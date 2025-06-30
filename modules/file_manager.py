"""
File Manager Module for Article Summarizer Agent
Handles file operations, output formatting, and metadata management
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path
import re
import hashlib

from config import config, SUPPORTED_FORMATS

class FileManager:
    """Manages file operations and output formatting"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.output_dir = Path(config.output.output_dir)
        self.cache_dir = Path(config.output.cache_dir)
        self._ensure_directories()
        
    def _ensure_directories(self):
        """Create necessary directories"""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        if config.output.cache_enabled:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger.info(f"Output directory: {self.output_dir.absolute()}")
    
    def save_results(self, summary_data: Dict, scraped_data: Dict, 
                    processed_data: Dict) -> Dict:
        """
        Save summarization results in multiple formats
        
        Args:
            summary_data: Results from summarization
            scraped_data: Original scraped data
            processed_data: Processed text data
            
        Returns:
            Dictionary with file paths and metadata
        """
        self.logger.info("Saving summarization results...")
        
        # Create comprehensive result data
        result_data = self._create_result_data(summary_data, scraped_data, processed_data)
        
        # Generate filename
        base_filename = self._generate_filename(scraped_data.get('title', 'article'))
        
        # Save in requested formats
        saved_files = {}
        for format_type in config.output.formats:
            if format_type in SUPPORTED_FORMATS:
                file_path = self._save_format(result_data, base_filename, format_type)
                saved_files[format_type] = str(file_path)
                self.logger.info(f"Saved {format_type.upper()} file: {file_path}")
        
        # Create summary report
        report_data = {
            'files_created': saved_files,
            'summary_stats': self._calculate_summary_stats(result_data),
            'timestamp': datetime.now().isoformat(),
            'success': True
        }
        
        self.logger.info(f"Results saved successfully. Created {len(saved_files)} files.")
        return report_data
    
    def _create_result_data(self, summary_data: Dict, scraped_data: Dict, 
                          processed_data: Dict) -> Dict:
        """Create comprehensive result data structure"""
        
        # Calculate processing statistics
        processing_stats = self._calculate_processing_stats(scraped_data, processed_data, summary_data)
        
        result_data = {
            'metadata': {
                'title': scraped_data.get('title', 'Unknown Title'),
                'url': scraped_data.get('url', ''),
                'author': scraped_data.get('author', 'Unknown Author'),
                'publish_date': scraped_data.get('publish_date', ''),
                'description': scraped_data.get('description', ''),
                'language': processed_data.get('language', 'unknown'),
                'scraped_at': datetime.fromtimestamp(scraped_data.get('scraped_at', 0)).isoformat() if scraped_data.get('scraped_at') else '',
                'processed_at': datetime.now().isoformat(),
                'encoding': scraped_data.get('encoding', 'utf-8'),
                'status_code': scraped_data.get('status_code', 0)
            },
            'summary': {
                'text': summary_data.get('summary', ''),
                'method': summary_data.get('method_used', 'unknown'),
                'length_setting': summary_data.get('summary_length_setting', 'medium'),
                'selected_sentences': summary_data.get('selected_sentences', []),
                'model_name': summary_data.get('model_name', 'N/A')
            },
            'statistics': processing_stats,
            'original_content': {
                'text': processed_data.get('clean_text', ''),
                'sentences': processed_data.get('sentences', []),
                'paragraphs': processed_data.get('paragraphs', [])
            } if config.output.include_metadata else {}
        }
        
        # Add additional data based on summarization method
        if summary_data.get('method_used') == 'extractive':
            result_data['extractive_data'] = {
                'sentence_scores': summary_data.get('sentence_scores', []),
                'selection_indices': summary_data.get('selection_indices', [])
            }
        elif summary_data.get('method_used') == 'hybrid':
            result_data['hybrid_data'] = {
                'extractive_summary': summary_data.get('extractive_summary', ''),
                'generative_summary': summary_data.get('generative_summary', ''),
                'sentence_scores': summary_data.get('sentence_scores', [])
            }
        
        return result_data
    
    def _calculate_processing_stats(self, scraped_data: Dict, processed_data: Dict, 
                                  summary_data: Dict) -> Dict:
        """Calculate comprehensive processing statistics"""
        
        original_text = scraped_data.get('content', '')
        clean_text = processed_data.get('clean_text', '')
        summary_text = summary_data.get('summary', '')
        
        # Text statistics
        original_stats = processed_data.get('statistics', {})
        
        stats = {
            'original': {
                'character_count': len(original_text),
                'word_count': len(original_text.split()) if original_text else 0,
                'sentence_count': len(processed_data.get('sentences', [])),
                'paragraph_count': len(processed_data.get('paragraphs', []))
            },
            'processed': original_stats,
            'summary': {
                'character_count': len(summary_text),
                'word_count': len(summary_text.split()) if summary_text else 0,
                'sentence_count': len(summary_data.get('selected_sentences', [])),
                'compression_ratio': 0.0
            },
            'extraction_method': scraped_data.get('extraction_method', 'unknown'),
            'summarization_method': summary_data.get('method_used', 'unknown')
        }
        
        # Calculate compression ratio
        if stats['original']['word_count'] > 0:
            stats['summary']['compression_ratio'] = (
                stats['summary']['word_count'] / stats['original']['word_count']
            )
        
        return stats
    
    def _calculate_summary_stats(self, result_data: Dict) -> Dict:
        """Calculate summary statistics for the report"""
        summary_stats = result_data.get('statistics', {}).get('summary', {})
        
        return {
            'words_original': result_data.get('statistics', {}).get('original', {}).get('word_count', 0),
            'words_summary': summary_stats.get('word_count', 0),
            'compression_ratio': summary_stats.get('compression_ratio', 0.0),
            'sentences_selected': summary_stats.get('sentence_count', 0),
            'method_used': result_data.get('summary', {}).get('method', 'unknown')
        }
    
    def _generate_filename(self, title: str) -> str:
        """Generate a safe filename from article title"""
        # Clean title for filename
        safe_title = re.sub(r'[^\w\s-]', '', title)
        safe_title = re.sub(r'[-\s]+', '-', safe_title)
        safe_title = safe_title.strip('-').lower()
        
        # Limit length
        if len(safe_title) > 50:
            safe_title = safe_title[:47] + '...'
        
        if not safe_title:
            safe_title = 'article'
        
        # Add timestamp to ensure uniqueness
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        return f"{safe_title}_{timestamp}"
    
    def _save_format(self, result_data: Dict, base_filename: str, format_type: str) -> Path:
        """Save data in specified format"""
        file_path = self.output_dir / f"{base_filename}.{format_type}"
        
        if format_type == 'txt':
            self._save_txt(result_data, file_path)
        elif format_type == 'md':
            self._save_markdown(result_data, file_path)
        elif format_type == 'json':
            self._save_json(result_data, file_path)
        
        return file_path
    
    def _save_txt(self, result_data: Dict, file_path: Path):
        """Save as plain text file"""
        with open(file_path, 'w', encoding='utf-8') as f:
            metadata = result_data['metadata']
            summary = result_data['summary']
            stats = result_data['statistics']
            
            # Header
            f.write("ARTICLE SUMMARY\n")
            f.write("=" * 50 + "\n\n")
            
            # Metadata
            f.write(f"Title: {metadata['title']}\n")
            f.write(f"Author: {metadata['author']}\n")
            f.write(f"URL: {metadata['url']}\n")
            f.write(f"Language: {metadata['language']}\n")
            f.write(f"Processed: {metadata['processed_at']}\n")
            f.write(f"Method: {summary['method']}\n")
            f.write("\n" + "-" * 50 + "\n\n")
            
            # Summary
            f.write("SUMMARY:\n")
            f.write(summary['text'])
            f.write("\n\n" + "-" * 50 + "\n\n")
            
            # Statistics
            if config.output.include_statistics:
                f.write("STATISTICS:\n")
                f.write(f"Original words: {stats['original']['word_count']}\n")
                f.write(f"Summary words: {stats['summary']['word_count']}\n")
                f.write(f"Compression ratio: {stats['summary']['compression_ratio']:.2%}\n")
                f.write(f"Sentences selected: {stats['summary']['sentence_count']}\n")
    
    def _save_markdown(self, result_data: Dict, file_path: Path):
        """Save as Markdown file"""
        with open(file_path, 'w', encoding='utf-8') as f:
            metadata = result_data['metadata']
            summary = result_data['summary']
            stats = result_data['statistics']
            
            # Header
            f.write(f"# {metadata['title']}\n\n")
            
            # Metadata table
            f.write("## Article Information\n\n")
            f.write("| Field | Value |\n")
            f.write("|-------|-------|\n")
            f.write(f"| **Author** | {metadata['author']} |\n")
            f.write(f"| **URL** | {metadata['url']} |\n")
            f.write(f"| **Language** | {metadata['language']} |\n")
            f.write(f"| **Processed** | {metadata['processed_at']} |\n")
            f.write(f"| **Method** | {summary['method']} |\n")
            
            if metadata['description']:
                f.write(f"| **Description** | {metadata['description']} |\n")
            
            f.write("\n")
            
            # Summary
            f.write("## Summary\n\n")
            f.write(summary['text'])
            f.write("\n\n")
            
            # Statistics
            if config.output.include_statistics:
                f.write("## Statistics\n\n")
                f.write("| Metric | Value |\n")
                f.write("|--------|-------|\n")
                f.write(f"| Original words | {stats['original']['word_count']} |\n")
                f.write(f"| Summary words | {stats['summary']['word_count']} |\n")
                f.write(f"| Compression ratio | {stats['summary']['compression_ratio']:.2%} |\n")
                f.write(f"| Sentences selected | {stats['summary']['sentence_count']} |\n")
                f.write("\n")
            
            # Selected sentences (for extractive)
            if summary.get('method') == 'extractive' and summary.get('selected_sentences'):
                f.write("## Selected Sentences\n\n")
                for i, sentence in enumerate(summary['selected_sentences'], 1):
                    f.write(f"{i}. {sentence}\n\n")
    
    def _save_json(self, result_data: Dict, file_path: Path):
        """Save as JSON file"""
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(result_data, f, indent=2, ensure_ascii=False)
    
    def load_cached_result(self, url: str) -> Optional[Dict]:
        """Load cached result if available"""
        if not config.output.cache_enabled:
            return None
        
        cache_key = self._get_cache_key(url)
        cache_file = self.cache_dir / f"{cache_key}.json"
        
        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cached_data = json.load(f)
                
                # Check if cache is still valid (24 hours)
                cached_time = datetime.fromisoformat(cached_data.get('cached_at', ''))
                if (datetime.now() - cached_time).total_seconds() < 86400:  # 24 hours
                    self.logger.info("Using cached result")
                    return cached_data
                
            except Exception as e:
                self.logger.warning(f"Failed to load cached result: {str(e)}")
        
        return None
    
    def save_to_cache(self, url: str, result_data: Dict):
        """Save result to cache"""
        if not config.output.cache_enabled:
            return
        
        cache_key = self._get_cache_key(url)
        cache_file = self.cache_dir / f"{cache_key}.json"
        
        try:
            cache_data = result_data.copy()
            cache_data['cached_at'] = datetime.now().isoformat()
            cache_data['url'] = url
            
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info("Result cached successfully")
            
        except Exception as e:
            self.logger.warning(f"Failed to cache result: {str(e)}")
    
    def _get_cache_key(self, url: str) -> str:
        """Generate cache key for URL"""
        return hashlib.md5(url.encode()).hexdigest()
    
    def clear_cache(self):
        """Clear all cached files"""
        if not config.output.cache_enabled or not self.cache_dir.exists():
            return
        
        try:
            for cache_file in self.cache_dir.glob("*.json"):
                cache_file.unlink()
            
            self.logger.info("Cache cleared successfully")
            
        except Exception as e:
            self.logger.warning(f"Failed to clear cache: {str(e)}")
    
    def get_output_files(self, pattern: str = "*") -> List[Path]:
        """Get list of output files matching pattern"""
        try:
            return list(self.output_dir.glob(pattern))
        except Exception:
            return []
    
    def cleanup_old_files(self, days: int = 30):
        """Clean up old output files"""
        try:
            cutoff_time = datetime.now().timestamp() - (days * 86400)
            
            for file_path in self.output_dir.iterdir():
                if file_path.is_file() and file_path.stat().st_mtime < cutoff_time:
                    file_path.unlink()
                    self.logger.info(f"Cleaned up old file: {file_path}")
            
        except Exception as e:
            self.logger.warning(f"Failed to cleanup old files: {str(e)}")
    
    def get_storage_info(self) -> Dict:
        """Get storage information"""
        try:
            total_size = 0
            file_count = 0
            
            for file_path in self.output_dir.rglob("*"):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
                    file_count += 1
            
            return {
                'output_directory': str(self.output_dir.absolute()),
                'total_files': file_count,
                'total_size_bytes': total_size,
                'total_size_mb': total_size / (1024 * 1024),
                'cache_enabled': config.output.cache_enabled,
                'cache_directory': str(self.cache_dir.absolute()) if config.output.cache_enabled else None
            }
            
        except Exception as e:
            self.logger.warning(f"Failed to get storage info: {str(e)}")
            return {'error': str(e)}