"""
Article Summarizer Agent — modules package
"""

__version__ = "2.0.0"

from .file_manager import FileManager
from .summarizer import Summarizer
from .text_processor import TextProcessor
from .web_scraper import WebScraper

__all__ = ["WebScraper", "TextProcessor", "Summarizer", "FileManager"]
