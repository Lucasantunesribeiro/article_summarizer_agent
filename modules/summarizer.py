"""
Summarizer Module for Article Summarizer Agent
Implements both extractive and generative summarization approaches
"""

import logging
import numpy as np
from typing import List, Dict, Tuple, Optional
from collections import Counter
import re
import math

# Extractive summarization imports
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.cluster import KMeans

# Generative summarization imports (optional)
try:
    from transformers import pipeline, AutoTokenizer, AutoModelForSeq2SeqLM
    import torch
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    logging.warning("Transformers not available. Generative summarization will be disabled.")

from config import config

class Summarizer:
    """Hybrid summarizer with extractive and generative approaches"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.extractive_summarizer = ExtractiveSummarizer()
        
        # Initialize generative summarizer if available
        self.generative_summarizer = None
        if TRANSFORMERS_AVAILABLE and config.summarization.method in ['generative', 'hybrid']:
            try:
                self.generative_summarizer = GenerativeSummarizer()
                self.logger.info("Generative summarizer initialized successfully")
            except Exception as e:
                self.logger.warning(f"Failed to initialize generative summarizer: {str(e)}")
    
    def summarize(self, processed_text_data: Dict) -> Dict:
        """
        Main summarization method
        
        Args:
            processed_text_data: Dictionary containing processed text data
            
        Returns:
            Dictionary containing summary and metadata
        """
        self.logger.info(f"Starting summarization using {config.summarization.method} method")
        
        # Validate input data
        if not isinstance(processed_text_data, dict):
            raise TypeError(f"Expected dictionary for processed_text_data, got {type(processed_text_data)}")
        
        sentences = processed_text_data.get('sentences', [])
        if not sentences:
            raise ValueError("No sentences found in processed text data")
        
        if not isinstance(sentences, list):
            raise TypeError(f"Expected list for sentences, got {type(sentences)}")
        
        # Determine summarization method
        method = config.summarization.method
        summary_data = {}
        
        try:
            if method == 'extractive' or not self.generative_summarizer:
                summary_data = self._extractive_summarization(sentences, processed_text_data)
            elif method == 'generative':
                summary_data = self._generative_summarization(processed_text_data)
            elif method == 'hybrid':
                summary_data = self._hybrid_summarization(sentences, processed_text_data)
            else:
                raise ValueError(f"Unknown summarization method: {method}")
            
            # Add common metadata
            summary_data.update({
                'method_used': method,
                'original_sentence_count': len(sentences),
                'summary_length_setting': config.summarization.summary_length,
                'language': processed_text_data.get('language', 'unknown')
            })
            
            self.logger.info(f"Summarization completed successfully using {method} method")
            return summary_data
            
        except Exception as e:
            self.logger.error(f"Summarization failed: {str(e)}")
            # Fallback to extractive if configured
            if config.summarization.use_fallback and method != 'extractive':
                self.logger.info("Falling back to extractive summarization")
                try:
                    return self._extractive_summarization(sentences, processed_text_data)
                except Exception as fallback_e:
                    self.logger.error(f"Fallback summarization also failed: {str(fallback_e)}")
            raise
    
    def _extractive_summarization(self, sentences: List[str], processed_data: Dict) -> Dict:
        """Perform extractive summarization"""
        return self.extractive_summarizer.summarize(sentences, processed_data)
    
    def _generative_summarization(self, processed_data: Dict) -> Dict:
        """Perform generative summarization"""
        if not self.generative_summarizer:
            raise RuntimeError("Generative summarizer not available")
        return self.generative_summarizer.summarize(processed_data)
    
    def _hybrid_summarization(self, sentences: List[str], processed_data: Dict) -> Dict:
        """Perform hybrid summarization (extractive + generative)"""
        # First use extractive to get key sentences
        extractive_result = self.extractive_summarizer.summarize(sentences, processed_data)
        
        # Then use generative to refine the summary
        if self.generative_summarizer:
            # Create a new processed_data with extractive sentences
            refined_data = processed_data.copy()
            refined_data['clean_text'] = ' '.join(extractive_result['selected_sentences'])
            
            generative_result = self.generative_summarizer.summarize(refined_data)
            
            return {
                'summary': generative_result['summary'],
                'selected_sentences': extractive_result['selected_sentences'],
                'sentence_scores': extractive_result['sentence_scores'],
                'method_used': 'hybrid',
                'extractive_summary': extractive_result['summary'],
                'generative_summary': generative_result['summary']
            }
        else:
            # Fall back to extractive only
            return extractive_result

class ExtractiveSummarizer:
    """Extractive summarization using TF-IDF and sentence ranking"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def summarize(self, sentences: List[str], processed_data: Dict) -> Dict:
        """
        Perform extractive summarization
        
        Args:
            sentences: List of sentences to summarize
            processed_data: Additional processed text data
            
        Returns:
            Dictionary containing extractive summary results
        """
        if len(sentences) < 2:
            return {
                'summary': sentences[0] if sentences else "",
                'selected_sentences': sentences,
                'sentence_scores': [1.0] if sentences else [],
                'method_used': 'extractive'
            }
        
        # Calculate sentence scores using multiple methods
        tfidf_scores = self._calculate_tfidf_scores(sentences)
        position_scores = self._calculate_position_scores(sentences)
        length_scores = self._calculate_length_scores(sentences)
        similarity_scores = self._calculate_similarity_scores(sentences)
        
        # Combine scores with weights
        combined_scores = self._combine_scores(
            tfidf_scores, position_scores, length_scores, similarity_scores
        )
        
        # Select sentences based on scores and diversity
        selected_indices = self._select_diverse_sentences(
            sentences, combined_scores, processed_data.get('language', 'en')
        )
        
        # Create summary
        selected_sentences = [sentences[i] for i in selected_indices]
        summary = self._create_coherent_summary(selected_sentences, selected_indices)
        
        return {
            'summary': summary,
            'selected_sentences': selected_sentences,
            'sentence_scores': [combined_scores[i] for i in selected_indices],
            'all_scores': combined_scores,
            'method_used': 'extractive',
            'selection_indices': selected_indices
        }
    
    def _calculate_tfidf_scores(self, sentences: List[str]) -> List[float]:
        """Calculate TF-IDF based sentence scores"""
        try:
            # Create TF-IDF vectorizer
            vectorizer = TfidfVectorizer(
                stop_words='english',
                lowercase=True,
                max_features=1000,
                ngram_range=(1, 2)
            )
            
            # Calculate TF-IDF matrix
            tfidf_matrix = vectorizer.fit_transform(sentences)
            
            # Calculate sentence scores as sum of TF-IDF values
            scores = np.array(tfidf_matrix.sum(axis=1)).flatten()
            
            # Normalize scores
            if scores.max() > 0:
                scores = scores / scores.max()
            
            return scores.tolist()
            
        except Exception as e:
            self.logger.warning(f"TF-IDF calculation failed: {str(e)}")
            return [1.0] * len(sentences)
    
    def _calculate_position_scores(self, sentences: List[str]) -> List[float]:
        """Calculate position-based scores (beginning and end sentences are more important)"""
        n = len(sentences)
        scores = []
        
        for i in range(n):
            if i < n * 0.1:  # First 10%
                score = 1.0
            elif i > n * 0.9:  # Last 10%
                score = 0.8
            else:
                # Middle sentences get lower scores
                score = 0.5
            
            scores.append(score)
        
        return scores
    
    def _calculate_length_scores(self, sentences: List[str]) -> List[float]:
        """Calculate length-based scores (prefer medium-length sentences)"""
        scores = []
        word_counts = [len(sentence.split()) for sentence in sentences]
        
        # Find optimal length range
        avg_length = np.mean(word_counts)
        
        for word_count in word_counts:
            # Prefer sentences close to average length
            if 10 <= word_count <= 30:  # Reasonable range
                score = 1.0
            elif word_count < 5:  # Too short
                score = 0.3
            elif word_count > 50:  # Too long
                score = 0.5
            else:
                score = 0.7
            
            scores.append(score)
        
        return scores
    
    def _calculate_similarity_scores(self, sentences: List[str]) -> List[float]:
        """Calculate similarity-based scores (sentences similar to overall content)"""
        try:
            # Create document representation
            document = ' '.join(sentences)
            all_texts = sentences + [document]
            
            # Calculate TF-IDF
            vectorizer = TfidfVectorizer(stop_words='english', lowercase=True)
            tfidf_matrix = vectorizer.fit_transform(all_texts)
            
            # Calculate similarity to document
            doc_vector = tfidf_matrix[-1]  # Last vector is the document
            sentence_vectors = tfidf_matrix[:-1]  # All except last
            
            similarities = cosine_similarity(sentence_vectors, doc_vector).flatten()
            
            return similarities.tolist()
            
        except Exception as e:
            self.logger.warning(f"Similarity calculation failed: {str(e)}")
            return [1.0] * len(sentences)
    
    def _combine_scores(self, tfidf_scores: List[float], position_scores: List[float], 
                       length_scores: List[float], similarity_scores: List[float]) -> List[float]:
        """Combine different scoring methods with weights"""
        
        # Weights for different scoring methods
        weights = {
            'tfidf': 0.4,
            'position': 0.2,
            'length': 0.2,
            'similarity': 0.2
        }
        
        combined_scores = []
        for i in range(len(tfidf_scores)):
            score = (
                weights['tfidf'] * tfidf_scores[i] +
                weights['position'] * position_scores[i] +
                weights['length'] * length_scores[i] +
                weights['similarity'] * similarity_scores[i]
            )
            combined_scores.append(score)
        
        return combined_scores
    
    def _select_diverse_sentences(self, sentences: List[str], scores: List[float], 
                                 language: str) -> List[int]:
        """Select diverse sentences based on scores and content diversity"""
        
        # Determine number of sentences to select
        target_count = config.summarization.extractive_sentences.get(
            config.summarization.summary_length, 5
        )
        target_count = min(target_count, len(sentences))
        
        # Sort sentences by score
        scored_sentences = [(i, score) for i, score in enumerate(scores)]
        scored_sentences.sort(key=lambda x: x[1], reverse=True)
        
        # Select diverse sentences
        selected_indices = []
        selected_sentences_text = []
        
        for idx, score in scored_sentences:
            if len(selected_indices) >= target_count:
                break
            
            sentence = sentences[idx]
            
            # Check diversity with already selected sentences
            if self._is_diverse_sentence(sentence, selected_sentences_text):
                selected_indices.append(idx)
                selected_sentences_text.append(sentence)
        
        # Sort selected indices to maintain original order
        selected_indices.sort()
        
        return selected_indices
    
    def _is_diverse_sentence(self, candidate: str, selected: List[str]) -> bool:
        """Check if candidate sentence is diverse enough from selected sentences"""
        if not selected:
            return True
        
        # Calculate similarity with selected sentences
        candidate_words = set(candidate.lower().split())
        
        for selected_sentence in selected:
            selected_words = set(selected_sentence.lower().split())
            
            # Calculate Jaccard similarity
            intersection = len(candidate_words & selected_words)
            union = len(candidate_words | selected_words)
            
            if union > 0:
                similarity = intersection / union
                if similarity > 0.3:  # Too similar
                    return False
        
        return True
    
    def _create_coherent_summary(self, selected_sentences: List[str], 
                                selected_indices: List[int]) -> str:
        """Create a coherent summary from selected sentences"""
        if not selected_sentences:
            return ""
        
        # Join sentences with proper spacing
        summary = ' '.join(selected_sentences)
        
        # Basic coherence improvements
        summary = self._improve_coherence(summary)
        
        return summary
    
    def _improve_coherence(self, summary: str) -> str:
        """Improve summary coherence with basic text processing"""
        # Ensure proper sentence spacing
        summary = re.sub(r'\s+', ' ', summary)
        
        # Capitalize first letter
        if summary:
            summary = summary[0].upper() + summary[1:]
        
        # Ensure proper ending punctuation
        if summary and not summary[-1] in '.!?':
            summary += '.'
        
        return summary

class GenerativeSummarizer:
    """Generative summarization using transformer models"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.model_name = config.model.model_name
        self.device = self._determine_device()
        self.summarizer = None
        self._initialize_model()
    
    def _determine_device(self) -> str:
        """Determine the best device to use"""
        if config.model.device == "auto":
            if torch.cuda.is_available():
                return "cuda"
            elif torch.backends.mps.is_available():
                return "mps"
            else:
                return "cpu"
        return config.model.device
    
    def _initialize_model(self):
        """Initialize the generative model"""
        try:
            self.logger.info(f"Loading model: {self.model_name}")
            
            # Initialize summarization pipeline
            self.summarizer = pipeline(
                "summarization",
                model=self.model_name,
                device=0 if self.device == "cuda" else -1,
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32
            )
            
            self.logger.info("Generative model loaded successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to load generative model: {str(e)}")
            raise
    
    def summarize(self, processed_data: Dict) -> Dict:
        """
        Perform generative summarization
        
        Args:
            processed_data: Dictionary containing processed text data
            
        Returns:
            Dictionary containing generative summary results
        """
        if not self.summarizer:
            raise RuntimeError("Generative model not initialized")
        
        text = processed_data.get('clean_text', '')
        if not text:
            raise ValueError("No clean text found in processed data")
        
        try:
            # Prepare text for summarization
            input_text = self._prepare_input_text(text)
            
            # Determine summary parameters based on configuration
            max_length, min_length = self._get_summary_lengths(input_text)
            
            # Generate summary
            self.logger.info("Generating summary with transformer model...")
            
            summary_result = self.summarizer(
                input_text,
                max_length=max_length,
                min_length=min_length,
                do_sample=True,
                temperature=config.summarization.temperature,
                truncation=True
            )
            
            summary = summary_result[0]['summary_text']
            
            # Post-process summary
            summary = self._post_process_summary(summary)
            
            return {
                'summary': summary,
                'method_used': 'generative',
                'model_name': self.model_name,
                'input_length': len(input_text.split()),
                'summary_length': len(summary.split())
            }
            
        except Exception as e:
            self.logger.error(f"Generative summarization failed: {str(e)}")
            raise
    
    def _prepare_input_text(self, text: str) -> str:
        """Prepare text for the generative model"""
        # Truncate text if too long for the model
        words = text.split()
        max_input_words = 800  # Conservative limit for most models
        
        if len(words) > max_input_words:
            text = ' '.join(words[:max_input_words])
            self.logger.info(f"Truncated input text to {max_input_words} words")
        
        return text
    
    def _get_summary_lengths(self, input_text: str) -> Tuple[int, int]:
        """Determine appropriate summary lengths"""
        input_length = len(input_text.split())
        
        length_settings = {
            'short': (0.1, 0.2),
            'medium': (0.2, 0.3),
            'long': (0.3, 0.4)
        }
        
        min_ratio, max_ratio = length_settings.get(config.summarization.summary_length, (0.2, 0.3))
        
        min_length = max(20, int(input_length * min_ratio))
        max_length = max(min_length + 10, int(input_length * max_ratio))
        
        # Ensure reasonable bounds
        min_length = min(min_length, 50)
        max_length = min(max_length, 150)
        
        return max_length, min_length
    
    def _post_process_summary(self, summary: str) -> str:
        """Post-process generated summary"""
        # Remove any model artifacts
        summary = summary.strip()
        
        # Ensure proper capitalization
        if summary:
            summary = summary[0].upper() + summary[1:]
        
        # Ensure proper ending punctuation
        if summary and not summary[-1] in '.!?':
            summary += '.'
        
        return summary