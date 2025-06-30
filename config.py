"""
Configuration settings for Article Summarizer Agent
"""

import os
from dataclasses import dataclass, field
from typing import Dict, List

@dataclass
class ScrapingConfig:
    """Web scraping configuration"""
    timeout: int = 30
    max_retries: int = 3
    retry_delay: float = 2.0
    backoff_factor: float = 2.0
    headers: Dict[str, str] = field(default_factory=dict)
    user_agents: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        if not self.headers:
            self.headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'Accept-Language': 'en-US,en;q=0.9,pt;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Cache-Control': 'max-age=0'
            }
        
        if not self.user_agents:
            self.user_agents = [
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
                'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            ]

@dataclass
class ProcessingConfig:
    """Text processing configuration"""
    min_paragraph_length: int = 20
    min_sentence_length: int = 10
    max_sentence_length: int = 500
    remove_short_paragraphs: bool = True
    preserve_structure: bool = True
    language_detection: bool = True

@dataclass
class SummarizationConfig:
    """Summarization configuration"""
    method: str = "extractive"  # "extractive" or "generative"
    summary_length: str = "medium"  # "short", "medium", "long"
    extractive_sentences: Dict[str, int] = field(default_factory=dict)
    max_tokens: int = 1024
    temperature: float = 0.7
    use_fallback: bool = True
    
    def __post_init__(self):
        if not self.extractive_sentences:
            self.extractive_sentences = {
                "short": 3,
                "medium": 5,
                "long": 8
            }

@dataclass
class OutputConfig:
    """Output configuration"""
    formats: List[str] = field(default_factory=list)
    include_metadata: bool = True
    include_statistics: bool = True
    output_dir: str = "outputs"
    cache_enabled: bool = True
    cache_dir: str = ".cache"
    
    def __post_init__(self):
        if not self.formats:
            self.formats = ["txt", "md", "json"]

@dataclass
class LoggingConfig:
    """Logging configuration"""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file_enabled: bool = True
    log_file: str = "summarizer.log"
    console_enabled: bool = True

@dataclass
class ModelConfig:
    """Model configuration for generative summarization"""
    model_name: str = "facebook/bart-large-cnn"
    device: str = "auto"  # "auto", "cpu", "cuda"
    cache_dir: str = ".model_cache"
    load_in_8bit: bool = False

class Config:
    """Main configuration class"""
    
    def __init__(self):
        self.scraping = ScrapingConfig()
        self.processing = ProcessingConfig()
        self.summarization = SummarizationConfig()
        self.output = OutputConfig()
        self.logging = LoggingConfig()
        self.model = ModelConfig()
        
        # Load environment variables if available
        self._load_from_env()
    
    def _load_from_env(self):
        """Load configuration from environment variables"""
        
        # Scraping config
        self.scraping.timeout = int(os.getenv('SCRAPING_TIMEOUT', self.scraping.timeout))
        self.scraping.max_retries = int(os.getenv('SCRAPING_MAX_RETRIES', self.scraping.max_retries))
        
        # Summarization config
        self.summarization.method = os.getenv('SUMMARIZATION_METHOD', self.summarization.method)
        self.summarization.summary_length = os.getenv('SUMMARY_LENGTH', self.summarization.summary_length)
        
        # Output config
        self.output.output_dir = os.getenv('OUTPUT_DIR', self.output.output_dir)
        self.output.cache_enabled = os.getenv('CACHE_ENABLED', 'true').lower() == 'true'
        
        # Model config
        self.model.model_name = os.getenv('MODEL_NAME', self.model.model_name)
        self.model.device = os.getenv('MODEL_DEVICE', self.model.device)
    
    def update_from_args(self, args):
        """Update configuration from command line arguments"""
        if hasattr(args, 'method') and args.method:
            self.summarization.method = args.method
        if hasattr(args, 'length') and args.length:
            self.summarization.summary_length = args.length
        if hasattr(args, 'output_dir') and args.output_dir:
            self.output.output_dir = args.output_dir

# Global configuration instance
config = Config()

# Content extraction selectors (in priority order)
CONTENT_SELECTORS = [
    'article',
    '[role="main"]',
    'main',
    '.post-content',
    '.article-content',
    '.entry-content',
    '.content',
    '.post-body',
    '.article-body',
    '.story-body',
    '.text',
    '#content',
    '#main-content',
    '.main-content'
]

# Elements to remove during scraping
UNWANTED_SELECTORS = [
    'nav', 'header', 'footer', 'aside',
    '.nav', '.header', '.footer', '.sidebar',
    '.advertisement', '.ads', '.ad',
    '.social-share', '.share-buttons',
    '.comments', '.comment',
    '.related-articles', '.related-posts',
    'script', 'style', 'noscript',
    '.cookie-notice', '.newsletter-signup'
]

# File extensions and MIME types
SUPPORTED_FORMATS = {
    'txt': 'text/plain',
    'md': 'text/markdown',
    'json': 'application/json'
}

# Language detection settings
SUPPORTED_LANGUAGES = ['en', 'es', 'fr', 'de', 'it', 'pt', 'ru', 'zh', 'ja', 'ko']
DEFAULT_LANGUAGE = 'en'