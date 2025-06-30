"""
Text Processor Module for Article Summarizer Agent
Handles advanced text cleaning and preprocessing
"""

import re
import logging
import string
from typing import List, Dict, Tuple, Optional
from langdetect import detect, DetectorFactory
import nltk
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
import unicodedata

from config import config, SUPPORTED_LANGUAGES, DEFAULT_LANGUAGE

# Set seed for langdetect for consistent results
DetectorFactory.seed = 0

class TextProcessor:
    """Advanced text processor with multilingual support"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.lemmatizer = WordNetLemmatizer()
        self._download_nltk_data()
        self._load_stopwords()
        
    def _download_nltk_data(self):
        """Download required NLTK data"""
        try:
            nltk.data.find('tokenizers/punkt')
        except LookupError:
            self.logger.info("Downloading NLTK punkt tokenizer...")
            nltk.download('punkt', quiet=True)
        
        try:
            nltk.data.find('corpora/stopwords')
        except LookupError:
            self.logger.info("Downloading NLTK stopwords...")
            nltk.download('stopwords', quiet=True)
        
        try:
            nltk.data.find('corpora/wordnet')
        except LookupError:
            self.logger.info("Downloading NLTK wordnet...")
            nltk.download('wordnet', quiet=True)
    
    def _load_stopwords(self):
        """Load stopwords for supported languages"""
        self.stopwords_dict = {}
        nltk_languages = {
            'en': 'english', 'es': 'spanish', 'fr': 'french',
            'de': 'german', 'it': 'italian', 'pt': 'portuguese',
            'ru': 'russian'
        }
        
        for lang_code, nltk_lang in nltk_languages.items():
            try:
                self.stopwords_dict[lang_code] = set(stopwords.words(nltk_lang))
            except Exception:
                self.logger.warning(f"Could not load stopwords for {lang_code}")
                self.stopwords_dict[lang_code] = set()
    
    def process_text(self, raw_text: str) -> Dict:
        """
        Main text processing method
        
        Args:
            raw_text: Raw text extracted from web page
            
        Returns:
            Dictionary containing processed text and metadata
        """
        self.logger.info("Starting text processing...")
        
        if not raw_text or not raw_text.strip():
            raise ValueError("Empty or invalid text provided")
        
        # Detect language
        language = self._detect_language(raw_text)
        self.logger.info(f"Detected language: {language}")
        
        # Basic cleaning
        clean_text = self._basic_cleaning(raw_text)
        
        # Advanced cleaning
        clean_text = self._advanced_cleaning(clean_text)
        
        # Normalize text
        clean_text = self._normalize_text(clean_text)
        
        # Split into sentences and paragraphs
        sentences = self._extract_sentences(clean_text, language)
        paragraphs = self._extract_paragraphs(clean_text)
        
        # Filter content
        filtered_sentences = self._filter_sentences(sentences)
        filtered_paragraphs = self._filter_paragraphs(paragraphs)
        
        # Extract structure if enabled
        structure = None
        if config.processing.preserve_structure:
            structure = self._extract_structure(raw_text)
        
        # Calculate statistics
        stats = self._calculate_statistics(clean_text, sentences, language)
        
        processed_data = {
            'original_text': raw_text,
            'clean_text': clean_text,
            'sentences': filtered_sentences,
            'paragraphs': filtered_paragraphs,
            'language': language,
            'structure': structure,
            'statistics': stats
        }
        
        self.logger.info(f"Text processing completed. {len(filtered_sentences)} sentences extracted.")
        return processed_data
    
    def _detect_language(self, text: str) -> str:
        """Detect text language"""
        if not config.processing.language_detection:
            return DEFAULT_LANGUAGE
        
        try:
            # Take a sample of the text for detection (first 1000 chars)
            sample = text[:1000].strip()
            if len(sample) < 50:
                return DEFAULT_LANGUAGE
            
            detected_lang = detect(sample)
            
            # Check if detected language is supported
            if detected_lang in SUPPORTED_LANGUAGES:
                return detected_lang
            else:
                self.logger.warning(f"Unsupported language detected: {detected_lang}, using default")
                return DEFAULT_LANGUAGE
                
        except Exception as e:
            self.logger.warning(f"Language detection failed: {str(e)}, using default")
            return DEFAULT_LANGUAGE
    
    def _basic_cleaning(self, text: str) -> str:
        """Basic text cleaning operations"""
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove control characters
        text = ''.join(char for char in text if ord(char) >= 32 or char in '\n\t')
        
        # Fix common encoding issues
        text = text.replace(''', "'").replace(''', "'")
        text = text.replace('"', '"').replace('"', '"')
        text = text.replace('–', '-').replace('—', '-')
        text = text.replace('…', '...')
        
        # Remove excessive punctuation
        text = re.sub(r'([.!?]){2,}', r'\1', text)
        
        return text.strip()
    
    def _advanced_cleaning(self, text: str) -> str:
        """Advanced text cleaning operations"""
        # Remove URLs
        text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)
        
        # Remove email addresses
        text = re.sub(r'\S+@\S+\.\S+', '', text)
        
        # Remove phone numbers (basic pattern)
        text = re.sub(r'[\+]?[1-9]?[0-9]{7,15}', '', text)
        
        # Remove excessive newlines
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Remove lines that are mostly punctuation or numbers
        lines = text.split('\n')
        clean_lines = []
        for line in lines:
            line = line.strip()
            if line and self._is_content_line(line):
                clean_lines.append(line)
        
        return '\n'.join(clean_lines)
    
    def _is_content_line(self, line: str) -> bool:
        """Check if a line contains meaningful content"""
        if len(line) < 10:
            return False
        
        # Calculate ratio of letters to total characters
        letter_count = sum(1 for char in line if char.isalpha())
        if letter_count / len(line) < 0.5:
            return False
        
        # Skip lines that are mostly numbers or dates
        if re.match(r'^\s*[\d\s\-/.,]+\s*$', line):
            return False
        
        # Skip lines that are mostly punctuation
        punct_count = sum(1 for char in line if char in string.punctuation)
        if punct_count / len(line) > 0.5:
            return False
        
        return True
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text using Unicode normalization"""
        # Normalize Unicode characters
        text = unicodedata.normalize('NFKC', text)
        
        # Fix spacing around punctuation
        text = re.sub(r'\s*([.!?])\s*', r'\1 ', text)
        text = re.sub(r'\s*,\s*', ', ', text)
        text = re.sub(r'\s*;\s*', '; ', text)
        text = re.sub(r'\s*:\s*', ': ', text)
        
        # Ensure sentences end with proper spacing
        text = re.sub(r'([.!?])([A-Z])', r'\1 \2', text)
        
        return text.strip()
    
    def _extract_sentences(self, text: str, language: str) -> List[str]:
        """Extract sentences using NLTK tokenizer"""
        try:
            # Use appropriate NLTK language model if available
            lang_models = {
                'en': 'english',
                'de': 'german',
                'fr': 'french',
                'it': 'italian',
                'pt': 'portuguese',
                'es': 'spanish'
            }
            
            if language in lang_models:
                sentences = sent_tokenize(text, language=lang_models[language])
            else:
                sentences = sent_tokenize(text)
            
            return [sent.strip() for sent in sentences if sent.strip()]
            
        except Exception as e:
            self.logger.warning(f"NLTK sentence tokenization failed: {str(e)}, using regex fallback")
            return self._regex_sentence_split(text)
    
    def _regex_sentence_split(self, text: str) -> List[str]:
        """Fallback sentence splitting using regex"""
        # Split on sentence endings followed by whitespace and capital letter
        pattern = r'(?<=[.!?])\s+(?=[A-Z])'
        sentences = re.split(pattern, text)
        return [sent.strip() for sent in sentences if sent.strip()]
    
    def _extract_paragraphs(self, text: str) -> List[str]:
        """Extract paragraphs from text"""
        paragraphs = re.split(r'\n\s*\n', text)
        return [para.strip() for para in paragraphs if para.strip()]
    
    def _filter_sentences(self, sentences: List[str]) -> List[str]:
        """Filter sentences based on quality criteria"""
        filtered = []
        
        for sentence in sentences:
            if self._is_valid_sentence(sentence):
                filtered.append(sentence)
        
        return filtered
    
    def _is_valid_sentence(self, sentence: str) -> bool:
        """Check if sentence meets quality criteria"""
        # Length check
        if len(sentence) < config.processing.min_sentence_length:
            return False
        
        if len(sentence) > config.processing.max_sentence_length:
            return False
        
        # Must contain at least one letter
        if not re.search(r'[a-zA-Z]', sentence):
            return False
        
        # Skip sentences that are mostly numbers or symbols
        alpha_count = sum(1 for char in sentence if char.isalpha())
        if alpha_count / len(sentence) < 0.3:
            return False
        
        # Skip sentences that look like navigation or UI elements
        ui_patterns = [
            r'^(click|select|choose|enter|submit|login|register|home|about|contact|menu)',
            r'(copyright|©|\(c\))',
            r'^(next|previous|back|forward|up|down)$',
            r'^[0-9\s\-/]+$'
        ]
        
        for pattern in ui_patterns:
            if re.search(pattern, sentence.lower()):
                return False
        
        return True
    
    def _filter_paragraphs(self, paragraphs: List[str]) -> List[str]:
        """Filter paragraphs based on configuration"""
        if not config.processing.remove_short_paragraphs:
            return paragraphs
        
        filtered = []
        for para in paragraphs:
            if len(para) >= config.processing.min_paragraph_length:
                filtered.append(para)
        
        return filtered
    
    def _extract_structure(self, text: str) -> Dict:
        """Extract document structure (headings, sections)"""
        structure = {
            'headings': [],
            'sections': [],
            'lists': []
        }
        
        # Extract potential headings (lines that might be titles)
        lines = text.split('\n')
        for i, line in enumerate(lines):
            line = line.strip()
            if self._looks_like_heading(line):
                structure['headings'].append({
                    'text': line,
                    'position': i,
                    'level': self._estimate_heading_level(line)
                })
        
        return structure
    
    def _looks_like_heading(self, line: str) -> bool:
        """Check if line looks like a heading"""
        if not line or len(line) > 100:
            return False
        
        # Check if line is short and doesn't end with sentence punctuation
        if len(line) < 60 and not line.endswith(('.', '!', '?')):
            # Check if it has title case or all caps
            if line.istitle() or line.isupper():
                return True
        
        return False
    
    def _estimate_heading_level(self, heading: str) -> int:
        """Estimate heading level based on formatting"""
        if heading.isupper():
            return 1
        elif heading.istitle():
            return 2
        else:
            return 3
    
    def _calculate_statistics(self, text: str, sentences: List[str], language: str) -> Dict:
        """Calculate text statistics"""
        words = word_tokenize(text.lower())
        
        # Filter out punctuation
        words = [word for word in words if word.isalnum()]
        
        # Calculate readability metrics
        stats = {
            'character_count': len(text),
            'word_count': len(words),
            'sentence_count': len(sentences),
            'paragraph_count': len(text.split('\n\n')),
            'avg_words_per_sentence': len(words) / len(sentences) if sentences else 0,
            'avg_chars_per_word': sum(len(word) for word in words) / len(words) if words else 0,
            'language': language
        }
        
        # Add vocabulary richness
        unique_words = set(words)
        stats['vocabulary_richness'] = len(unique_words) / len(words) if words else 0
        
        # Add stopword ratio if we have stopwords for the language
        if language in self.stopwords_dict:
            stopword_count = sum(1 for word in words if word in self.stopwords_dict[language])
            stats['stopword_ratio'] = stopword_count / len(words) if words else 0
        
        return stats
    
    def preprocess_for_summarization(self, sentences: List[str], language: str) -> List[str]:
        """Preprocess sentences specifically for summarization"""
        processed_sentences = []
        
        for sentence in sentences:
            # Clean and normalize each sentence
            clean_sentence = self._normalize_text(sentence)
            
            # Skip very short or very long sentences for summarization
            word_count = len(clean_sentence.split())
            if 5 <= word_count <= 50:  # Reasonable sentence length for summarization
                processed_sentences.append(clean_sentence)
        
        return processed_sentences