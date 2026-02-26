"""
Tests for the extractive summariser.
Gemini is NOT called — tests run fully offline.
"""

import pytest

from config import config
from modules.summarizer import ExtractiveSummarizer, Summarizer

SENTENCES = [
    "Artificial intelligence is transforming many industries worldwide.",
    "Machine learning algorithms can identify patterns in large datasets.",
    "Natural language processing allows computers to understand human text.",
    "Deep learning models have achieved superhuman performance on image tasks.",
    "Reinforcement learning enables agents to learn from trial and error.",
    "AI applications include healthcare, finance, and autonomous vehicles.",
    "Ethical considerations are increasingly important in AI development.",
    "Researchers are working on making AI systems more transparent and fair.",
]

PROCESSED_DATA = {
    "sentences": SENTENCES,
    "clean_text": " ".join(SENTENCES),
    "language": "en",
    "paragraphs": [" ".join(SENTENCES)],
    "statistics": {"word_count": 80, "sentence_count": 8},
}


class TestExtractiveSummarizer:
    @pytest.fixture
    def summarizer(self):
        return ExtractiveSummarizer()

    def test_returns_dict(self, summarizer):
        result = summarizer.summarize(SENTENCES, PROCESSED_DATA)
        assert isinstance(result, dict)

    def test_summary_key_present(self, summarizer):
        result = summarizer.summarize(SENTENCES, PROCESSED_DATA)
        assert "summary" in result
        assert isinstance(result["summary"], str)
        assert len(result["summary"]) > 0

    def test_summary_not_empty(self, summarizer):
        result = summarizer.summarize(SENTENCES, PROCESSED_DATA)
        assert result["summary"].strip()

    def test_selected_sentences_subset(self, summarizer):
        result = summarizer.summarize(SENTENCES, PROCESSED_DATA)
        for s in result.get("selected_sentences", []):
            assert s in SENTENCES

    def test_short_length(self, summarizer):
        config.summarization.summary_length = "short"
        result = summarizer.summarize(SENTENCES, PROCESSED_DATA)
        # short → 3 sentences max
        assert len(result.get("selected_sentences", [])) <= 3
        config.summarization.summary_length = "medium"  # restore

    def test_single_sentence_handled(self, summarizer):
        result = summarizer.summarize(
            ["Only one sentence here."], {"sentences": ["Only one sentence here."]}
        )
        assert result["summary"]


class TestSummarizerDispatcher:
    def test_extractive_mode_works_offline(self, monkeypatch):
        config.summarization.method = "extractive"
        s = Summarizer()
        result = s.summarize(PROCESSED_DATA)
        assert result["summary"]
        assert result["method_used"] == "extractive"

    def test_generative_falls_back_when_no_key(self, monkeypatch):
        # No API key → should fall back to extractive (use_fallback=True)
        config.summarization.method = "generative"
        config.gemini.api_key = ""
        config.summarization.use_fallback = True
        s = Summarizer()
        result = s.summarize(PROCESSED_DATA)
        assert result["summary"]
        # Restore
        config.summarization.method = "extractive"
