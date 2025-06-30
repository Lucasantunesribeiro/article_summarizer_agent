#!/usr/bin/env python3
"""
Article Summarizer Agent - Main Script
Complete autonomous agent for web article summarization
"""

import sys
import argparse
import logging
import time
from pathlib import Path
from typing import Dict, Optional
import colorama
from colorama import Fore, Style
from tqdm import tqdm

# Initialize colorama for cross-platform colored output
colorama.init()

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Import our modules
from config import config
from modules import WebScraper, TextProcessor, Summarizer, FileManager

class ArticleSummarizerAgent:
    """
    Complete autonomous agent for article summarization
    Orchestrates the entire 5-step pipeline
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize the agent with all required modules"""
        self.logger = self._setup_logging()
        self.logger.info("Initializing Article Summarizer Agent...")
        
        # Initialize all modules
        try:
            self.web_scraper = WebScraper()
            self.text_processor = TextProcessor()
            self.summarizer = Summarizer()
            self.file_manager = FileManager()
            
            self.logger.info("All modules initialized successfully")
            print(f"{Fore.GREEN}✓ Article Summarizer Agent initialized successfully{Style.RESET_ALL}")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize agent: {str(e)}")
            print(f"{Fore.RED}✗ Failed to initialize agent: {str(e)}{Style.RESET_ALL}")
            raise
    
    def run(self, url: str) -> Dict:
        """
        Execute the complete summarization pipeline
        
        Args:
            url: URL of the article to summarize
            
        Returns:
            Dictionary containing results and metadata
        """
        start_time = time.time()
        
        print(f"\n{Fore.CYAN}🤖 Starting Article Summarization Agent{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}URL: {url}{Style.RESET_ALL}\n")
        
        try:
            # Check cache first
            cached_result = self.file_manager.load_cached_result(url)
            if cached_result:
                print(f"{Fore.GREEN}✓ Using cached result{Style.RESET_ALL}")
                return cached_result
            
            # Execute pipeline steps
            results = {}
            
            # Step 1: Validate input
            results['step1'] = self._step1_validate_input(url)
            
            # Step 2: Scrape content
            results['step2'] = self._step2_scrape_content(results['step1'])
            
            # Step 3: Process text
            results['step3'] = self._step3_process_text(results['step2'])
            
            # Step 4: Summarize
            results['step4'] = self._step4_summarize(results['step3'])
            
            # Step 5: Save results
            results['step5'] = self._step5_save_results(
                results['step4'], results['step2'], results['step3']
            )
            
            # Calculate total execution time
            execution_time = time.time() - start_time
            
            # Create final result
            final_result = {
                'success': True,
                'url': url,
                'execution_time': execution_time,
                'summary': results['step4']['summary'],
                'method_used': results['step4']['method_used'],
                'files_created': results['step5']['files_created'],
                'statistics': results['step5']['summary_stats'],
                'timestamp': time.time()
            }
            
            # Cache the result
            self.file_manager.save_to_cache(url, final_result)
            
            # Display success message
            self._display_success_message(final_result)
            
            return final_result
            
        except Exception as e:
            self.logger.error(f"Pipeline execution failed: {str(e)}")
            print(f"{Fore.RED}✗ Pipeline failed: {str(e)}{Style.RESET_ALL}")
            
            return {
                'success': False,
                'url': url,
                'error': str(e),
                'execution_time': time.time() - start_time,
                'timestamp': time.time()
            }
    
    def _step1_validate_input(self, url: str) -> Dict:
        """Step 1: Validate and prepare input"""
        with tqdm(total=1, desc="Step 1: Validating input", colour="blue") as pbar:
            self.logger.info("Step 1: Validating input URL")
            
            if not url or not url.strip():
                raise ValueError("Empty URL provided")
            
            url = url.strip()
            
            # Basic URL validation
            if not (url.startswith('http://') or url.startswith('https://')):
                if not url.startswith('www.'):
                    url = 'https://' + url
                else:
                    url = 'https://' + url
            
            pbar.update(1)
            
            result = {'validated_url': url, 'original_url': url}
            self.logger.info(f"Step 1 completed: URL validated")
            return result
    
    def _step2_scrape_content(self, step1_result: Dict) -> Dict:
        """Step 2: Scrape web content"""
        url = step1_result['validated_url']
        
        with tqdm(total=3, desc="Step 2: Scraping content", colour="green") as pbar:
            self.logger.info("Step 2: Starting web scraping")
            
            pbar.set_description("Fetching webpage...")
            pbar.update(1)
            
            scraped_data = self.web_scraper.scrape_article(url)
            pbar.update(1)
            
            # Validate scraped content
            if not isinstance(scraped_data, dict):
                raise ValueError(f"Web scraper returned invalid data type: {type(scraped_data)}")
            
            if not scraped_data.get('content') or len(scraped_data['content'].strip()) < 100:
                pbar.close()
                raise ValueError("Insufficient content extracted from webpage")
            
            pbar.set_description("Content validation complete")
            pbar.update(1)
            
            self.logger.info(f"Step 2 completed: Extracted {scraped_data.get('word_count', 0)} words")
            return scraped_data
    
    def _step3_process_text(self, scraped_data: Dict) -> Dict:
        """Step 3: Process and clean text"""
        with tqdm(total=4, desc="Step 3: Processing text", colour="yellow") as pbar:
            self.logger.info("Step 3: Starting text processing")
            
            # Validate input data
            if not isinstance(scraped_data, dict):
                raise ValueError(f"Expected dictionary for scraped_data, got {type(scraped_data)}")
            
            raw_text = scraped_data['content']
            
            pbar.set_description("Language detection...")
            pbar.update(1)
            
            pbar.set_description("Text cleaning...")
            pbar.update(1)
            
            processed_data = self.text_processor.process_text(raw_text)
            
            # Validate processed data
            if not isinstance(processed_data, dict):
                raise ValueError(f"Text processor returned invalid data type: {type(processed_data)}")
            
            pbar.update(1)
            
            # Validate processed content
            sentences = processed_data.get('sentences', [])
            if not sentences or len(sentences) < 2:
                pbar.close()
                raise ValueError("Insufficient sentences after text processing")
            
            pbar.set_description("Processing validation complete")
            pbar.update(1)
            
            self.logger.info(f"Step 3 completed: Processed {len(sentences)} sentences")
            return processed_data
    
    def _step4_summarize(self, processed_data: Dict) -> Dict:
        """Step 4: Generate summary"""
        method = config.summarization.method
        
        with tqdm(total=3, desc=f"Step 4: Summarizing ({method})", colour="magenta") as pbar:
            self.logger.info(f"Step 4: Starting summarization using {method} method")
            
            # Validate input data
            if not isinstance(processed_data, dict):
                raise ValueError(f"Expected dictionary for processed_data, got {type(processed_data)}")
            
            pbar.set_description(f"Initializing {method} summarizer...")
            pbar.update(1)
            
            pbar.set_description(f"Generating {method} summary...")
            summary_data = self.summarizer.summarize(processed_data)
            
            # Validate summary data
            if not isinstance(summary_data, dict):
                raise ValueError(f"Summarizer returned invalid data type: {type(summary_data)}")
            
            pbar.update(1)
            
            # Validate summary
            if not summary_data.get('summary') or len(summary_data['summary'].strip()) < 10:
                pbar.close()
                raise ValueError("Generated summary is too short or empty")
            
            pbar.set_description("Summary validation complete")
            pbar.update(1)
            
            summary_word_count = len(summary_data['summary'].split())
            self.logger.info(f"Step 4 completed: Generated {summary_word_count} word summary")
            return summary_data
    
    def _step5_save_results(self, summary_data: Dict, scraped_data: Dict, 
                           processed_data: Dict) -> Dict:
        """Step 5: Save results to files"""
        formats = config.output.formats
        
        with tqdm(total=len(formats) + 1, desc="Step 5: Saving results", colour="cyan") as pbar:
            self.logger.info("Step 5: Starting file operations")
            
            pbar.set_description("Preparing output data...")
            pbar.update(1)
            
            for format_type in formats:
                pbar.set_description(f"Saving {format_type.upper()} file...")
                pbar.update(1)
            
            save_result = self.file_manager.save_results(
                summary_data, scraped_data, processed_data
            )
            
            files_created = len(save_result.get('files_created', {}))
            self.logger.info(f"Step 5 completed: Created {files_created} output files")
            return save_result
    
    def _display_success_message(self, result: Dict):
        """Display success message with results summary"""
        print(f"\n{Fore.GREEN}✅ SUMMARIZATION COMPLETED SUCCESSFULLY{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
        
        # Summary preview
        summary_preview = result['summary'][:200] + "..." if len(result['summary']) > 200 else result['summary']
        print(f"\n{Fore.YELLOW}📋 Summary Preview:{Style.RESET_ALL}")
        print(f"{summary_preview}")
        
        # Statistics
        stats = result['statistics']
        print(f"\n{Fore.YELLOW}📊 Statistics:{Style.RESET_ALL}")
        print(f"  • Original words: {stats.get('words_original', 0)}")
        print(f"  • Summary words: {stats.get('words_summary', 0)}")
        print(f"  • Compression ratio: {stats.get('compression_ratio', 0):.1%}")
        print(f"  • Method used: {result['method_used']}")
        print(f"  • Execution time: {result['execution_time']:.2f} seconds")
        
        # Files created
        files = result['files_created']
        print(f"\n{Fore.YELLOW}📁 Files Created:{Style.RESET_ALL}")
        for format_type, file_path in files.items():
            print(f"  • {format_type.upper()}: {file_path}")
        
        print(f"\n{Fore.GREEN}🎉 Process completed successfully!{Style.RESET_ALL}")
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration"""
        logging.basicConfig(
            level=getattr(logging, config.logging.level.upper()),
            format=config.logging.format,
            handlers=[]
        )
        
        logger = logging.getLogger('ArticleSummarizerAgent')
        
        # Console handler
        if config.logging.console_enabled:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.WARNING)  # Only warnings and errors to console
            console_formatter = logging.Formatter('%(levelname)s: %(message)s')
            console_handler.setFormatter(console_formatter)
            logger.addHandler(console_handler)
        
        # File handler
        if config.logging.file_enabled:
            try:
                file_handler = logging.FileHandler(config.logging.log_file)
                file_handler.setLevel(getattr(logging, config.logging.level.upper()))
                file_formatter = logging.Formatter(config.logging.format)
                file_handler.setFormatter(file_formatter)
                logger.addHandler(file_handler)
            except Exception as e:
                print(f"Warning: Could not setup file logging: {e}")
        
        return logger
    
    def get_status(self) -> Dict:
        """Get agent status and configuration"""
        return {
            'version': '1.0.0',
            'config': {
                'summarization_method': config.summarization.method,
                'summary_length': config.summarization.summary_length,
                'output_formats': config.output.formats,
                'cache_enabled': config.output.cache_enabled
            },
            'storage_info': self.file_manager.get_storage_info(),
            'modules_loaded': {
                'web_scraper': self.web_scraper is not None,
                'text_processor': self.text_processor is not None,
                'summarizer': self.summarizer is not None,
                'file_manager': self.file_manager is not None
            }
        }

def create_argument_parser() -> argparse.ArgumentParser:
    """Create command line argument parser"""
    parser = argparse.ArgumentParser(
        description="Article Summarizer Agent - Autonomous web article summarization",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --url "https://example.com/article"
  python main.py --url "https://news.com/story" --method extractive --length short
  python main.py --interactive
  python main.py --status
        """
    )
    
    # Main arguments
    parser.add_argument(
        '--url', '-u',
        type=str,
        help='URL of the article to summarize'
    )
    
    parser.add_argument(
        '--method', '-m',
        choices=['extractive', 'generative', 'hybrid'],
        help='Summarization method to use'
    )
    
    parser.add_argument(
        '--length', '-l',
        choices=['short', 'medium', 'long'],
        help='Length of the summary'
    )
    
    parser.add_argument(
        '--output-dir', '-o',
        type=str,
        help='Output directory for summary files'
    )
    
    # Special modes
    parser.add_argument(
        '--interactive', '-i',
        action='store_true',
        help='Run in interactive mode'
    )
    
    parser.add_argument(
        '--status', '-s',
        action='store_true',
        help='Show agent status and configuration'
    )
    
    parser.add_argument(
        '--clear-cache',
        action='store_true',
        help='Clear cached results'
    )
    
    parser.add_argument(
        '--cleanup-files',
        type=int,
        metavar='DAYS',
        help='Clean up output files older than specified days'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )
    
    return parser

def interactive_mode():
    """Run agent in interactive mode"""
    print(f"{Fore.CYAN}🤖 Article Summarizer Agent - Interactive Mode{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}Enter 'quit' or 'exit' to stop, 'help' for commands{Style.RESET_ALL}\n")
    
    try:
        agent = ArticleSummarizerAgent()
    except Exception as e:
        print(f"{Fore.RED}Failed to initialize agent: {e}{Style.RESET_ALL}")
        return
    
    while True:
        try:
            user_input = input(f"{Fore.GREEN}Enter article URL: {Style.RESET_ALL}").strip()
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                print(f"{Fore.YELLOW}Goodbye!{Style.RESET_ALL}")
                break
            elif user_input.lower() == 'help':
                print(f"{Fore.CYAN}Available commands:{Style.RESET_ALL}")
                print("  • Enter any URL to summarize")
                print("  • 'status' - Show agent status")
                print("  • 'clear-cache' - Clear cached results")
                print("  • 'quit' or 'exit' - Exit interactive mode")
                continue
            elif user_input.lower() == 'status':
                status = agent.get_status()
                print(f"{Fore.CYAN}Agent Status:{Style.RESET_ALL}")
                for key, value in status['config'].items():
                    print(f"  • {key}: {value}")
                continue
            elif user_input.lower() == 'clear-cache':
                agent.file_manager.clear_cache()
                print(f"{Fore.GREEN}Cache cleared{Style.RESET_ALL}")
                continue
            elif not user_input:
                continue
            
            # Process the URL
            result = agent.run(user_input)
            
            if not result['success']:
                print(f"{Fore.RED}Processing failed: {result.get('error', 'Unknown error')}{Style.RESET_ALL}")
            
            print()  # Add spacing between sessions
            
        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}Interrupted by user. Goodbye!{Style.RESET_ALL}")
            break
        except Exception as e:
            print(f"{Fore.RED}Error: {str(e)}{Style.RESET_ALL}")

def main():
    """Main entry point"""
    parser = create_argument_parser()
    args = parser.parse_args()
    
    # Update config from arguments
    config.update_from_args(args)
    
    # Set verbose logging if requested
    if args.verbose:
        config.logging.level = 'DEBUG'
        config.logging.console_enabled = True
    
    try:
        # Handle special modes first
        if args.interactive:
            interactive_mode()
            return
        
        # Initialize agent
        agent = ArticleSummarizerAgent()
        
        if args.status:
            status = agent.get_status()
            print(f"{Fore.CYAN}Article Summarizer Agent Status{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}Version: {status['version']}{Style.RESET_ALL}")
            print(f"\n{Fore.YELLOW}Configuration:{Style.RESET_ALL}")
            for key, value in status['config'].items():
                print(f"  • {key}: {value}")
            print(f"\n{Fore.YELLOW}Storage:{Style.RESET_ALL}")
            storage = status['storage_info']
            for key, value in storage.items():
                if key != 'error':
                    print(f"  • {key}: {value}")
            return
        
        if args.clear_cache:
            agent.file_manager.clear_cache()
            print(f"{Fore.GREEN}Cache cleared successfully{Style.RESET_ALL}")
            return
        
        if args.cleanup_files:
            agent.file_manager.cleanup_old_files(args.cleanup_files)
            print(f"{Fore.GREEN}Cleaned up files older than {args.cleanup_files} days{Style.RESET_ALL}")
            return
        
        # Main processing
        if args.url:
            result = agent.run(args.url)
            if not result['success']:
                print(f"{Fore.RED}Processing failed: {result.get('error', 'Unknown error')}{Style.RESET_ALL}")
                sys.exit(1)
        else:
            # No URL provided, show help and enter interactive mode
            parser.print_help()
            print(f"\n{Fore.YELLOW}No URL provided. Starting interactive mode...{Style.RESET_ALL}\n")
            interactive_mode()
    
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Operation cancelled by user{Style.RESET_ALL}")
        sys.exit(1)
    except Exception as e:
        print(f"{Fore.RED}Fatal error: {str(e)}{Style.RESET_ALL}")
        sys.exit(1)

if __name__ == "__main__":
    main()