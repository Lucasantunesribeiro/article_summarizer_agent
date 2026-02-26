"""
Summarizer — Dispatcher for Extractive and Generative Summarisation
====================================================================

Two backends:
  - ExtractiveSummarizer: TF-IDF + position + cosine scoring.
    Works offline, no API key needed.
  - GeminiSummarizer: Google Gemini API.
    Requires GEMINI_API_KEY; falls back to extractive if unavailable.
"""

from __future__ import annotations

import logging
import re

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from config import config

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Top-level dispatcher
# ---------------------------------------------------------------------------


class Summarizer:
    """Dispatches to Gemini or extractive depending on config / availability."""

    def __init__(self) -> None:
        self._extractive = ExtractiveSummarizer()
        self._gemini: object | None = None  # lazy init

        if config.summarization.method == "generative":
            self._gemini = self._try_init_gemini()

    def _try_init_gemini(self) -> object | None:
        try:
            from .gemini_summarizer import GeminiSummarizer  # noqa: PLC0415

            gs = GeminiSummarizer()
            logger.info("Gemini summarizer ready.")
            return gs
        except Exception as exc:
            logger.warning("Gemini summarizer unavailable (%s); using extractive fallback.", exc)
            return None

    def summarize(
        self,
        processed_data: dict,
        method: str | None = None,
        length: str | None = None,
    ) -> dict:
        """Generate a summary from processed text data.

        Args:
            processed_data: Dict produced by TextProcessor.process_text().
            method: Per-call override for summarisation method
                ("extractive" / "generative"). Falls back to config default.
            length: Per-call override for summary length
                ("short" / "medium" / "long"). Falls back to config default.

        Returns:
            Dict with at least: summary (str), method_used (str).
        """
        sentences: list[str] = processed_data.get("sentences", [])
        if not sentences:
            raise ValueError("No sentences in processed_data.")

        # Resolve per-call overrides; never mutate the global singleton.
        effective_method = method or config.summarization.method
        effective_length = length or config.summarization.summary_length

        try:
            if effective_method == "generative" and self._gemini is not None:
                result = self._gemini.summarize(  # type: ignore[attr-defined]
                    processed_data
                )
            elif effective_method == "generative" and config.summarization.use_fallback:
                logger.info("Gemini unavailable — falling back to extractive.")
                result = self._extractive.summarize(
                    sentences, processed_data, length=effective_length
                )
            else:
                result = self._extractive.summarize(
                    sentences, processed_data, length=effective_length
                )

        except Exception as exc:
            logger.error("Primary summarisation failed: %s", exc)
            if config.summarization.use_fallback and effective_method != "extractive":
                logger.info("Falling back to extractive summarisation.")
                result = self._extractive.summarize(
                    sentences, processed_data, length=effective_length
                )
            else:
                raise

        # Attach common metadata
        result.setdefault("method_used", effective_method)
        result["original_sentence_count"] = len(sentences)
        result["summary_length_setting"] = effective_length
        result["language"] = processed_data.get("language", "unknown")
        return result


# ---------------------------------------------------------------------------
# Extractive summariser
# ---------------------------------------------------------------------------


class ExtractiveSummarizer:
    """TF-IDF + position + cosine-similarity sentence ranking."""

    def summarize(
        self,
        sentences: list[str],
        processed_data: dict,
        length: str | None = None,
    ) -> dict:
        if len(sentences) < 2:
            return {
                "summary": sentences[0] if sentences else "",
                "selected_sentences": sentences,
                "sentence_scores": [1.0] if sentences else [],
                "method_used": "extractive",
            }

        language = processed_data.get("language", "en")
        stop_words = self._get_stop_words(language)

        tfidf_scores = self._tfidf_scores(sentences, stop_words)
        position_scores = self._position_scores(sentences)
        length_scores = self._length_scores(sentences)
        similarity_scores = self._similarity_scores(sentences, stop_words)

        combined = self._combine_scores(
            tfidf_scores, position_scores, length_scores, similarity_scores
        )

        selected_idx = self._select_diverse(sentences, combined, length=length)
        selected = [sentences[i] for i in selected_idx]
        summary = self._join_sentences(selected)

        return {
            "summary": summary,
            "selected_sentences": selected,
            "sentence_scores": [combined[i] for i in selected_idx],
            "all_scores": combined,
            "selection_indices": selected_idx,
            "method_used": "extractive",
        }

    # --- Scoring ---

    def _get_stop_words(self, language: str) -> str | list[str]:
        """Return stop words appropriate for *language*.

        sklearn's TfidfVectorizer only understands "english" as a string;
        for other languages we pass a list from NLTK.
        """
        if language == "en":
            return "english"
        nltk_map = {
            "pt": "portuguese",
            "es": "spanish",
            "fr": "french",
            "de": "german",
            "it": "italian",
            "ru": "russian",
        }
        if language in nltk_map:
            try:
                from nltk.corpus import stopwords as _sw  # noqa: PLC0415

                return list(_sw.words(nltk_map[language]))
            except Exception as exc:
                logger.debug("Could not load %s stopwords: %s", language, exc)
        return "english"

    def _tfidf_scores(self, sentences: list[str], stop_words: str | list[str] = "english") -> list[float]:
        try:
            vec = TfidfVectorizer(
                stop_words=stop_words,
                lowercase=True,
                max_features=1000,
                ngram_range=(1, 2),
            )
            matrix = vec.fit_transform(sentences)
            scores = np.array(matrix.sum(axis=1)).flatten()
            if scores.max() > 0:
                scores /= scores.max()
            return scores.tolist()
        except Exception as exc:
            logger.warning("TF-IDF scoring failed: %s", exc)
            return [1.0] * len(sentences)

    def _position_scores(self, sentences: list[str]) -> list[float]:
        n = len(sentences)
        scores = []
        for i in range(n):
            if i < n * 0.1:
                scores.append(1.0)
            elif i > n * 0.9:
                scores.append(0.8)
            else:
                scores.append(0.5)
        return scores

    def _length_scores(self, sentences: list[str]) -> list[float]:
        scores = []
        for s in sentences:
            wc = len(s.split())
            if 10 <= wc <= 30:
                scores.append(1.0)
            elif wc < 5:
                scores.append(0.3)
            elif wc > 50:
                scores.append(0.5)
            else:
                scores.append(0.7)
        return scores

    def _similarity_scores(self, sentences: list[str], stop_words: str | list[str] = "english") -> list[float]:
        try:
            doc = " ".join(sentences)
            vec = TfidfVectorizer(stop_words=stop_words, lowercase=True)
            matrix = vec.fit_transform(sentences + [doc])
            sims = cosine_similarity(matrix[:-1], matrix[-1:]).flatten()
            return sims.tolist()
        except Exception as exc:
            logger.warning("Similarity scoring failed: %s", exc)
            return [1.0] * len(sentences)

    def _combine_scores(
        self,
        tfidf: list[float],
        position: list[float],
        length: list[float],
        similarity: list[float],
    ) -> list[float]:
        w = {"tfidf": 0.4, "position": 0.2, "length": 0.2, "similarity": 0.2}
        return [
            w["tfidf"] * tfidf[i]
            + w["position"] * position[i]
            + w["length"] * length[i]
            + w["similarity"] * similarity[i]
            for i in range(len(tfidf))
        ]

    # --- Selection ---

    def _select_diverse(
        self,
        sentences: list[str],
        scores: list[float],
        length: str | None = None,
    ) -> list[int]:
        effective_length = length or config.summarization.summary_length
        target = config.summarization.extractive_sentences.get(effective_length, 5)
        target = min(target, len(sentences))

        ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
        selected_idx: list[int] = []
        selected_texts: list[str] = []

        for idx, _score in ranked:
            if len(selected_idx) >= target:
                break
            if self._is_diverse(sentences[idx], selected_texts):
                selected_idx.append(idx)
                selected_texts.append(sentences[idx])

        selected_idx.sort()
        return selected_idx

    def _is_diverse(self, candidate: str, selected: list[str]) -> bool:
        if not selected:
            return True
        cand_words = set(candidate.lower().split())
        for s in selected:
            sel_words = set(s.lower().split())
            union = cand_words | sel_words
            if union:
                jaccard = len(cand_words & sel_words) / len(union)
                if jaccard > 0.3:
                    return False
        return True

    def _join_sentences(self, sentences: list[str]) -> str:
        text = " ".join(sentences)
        text = re.sub(r"\s+", " ", text).strip()
        if text and text[0].islower():
            text = text[0].upper() + text[1:]
        if text and text[-1] not in ".!?":
            text += "."
        return text
