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

    def test_short_length(self, summarizer, monkeypatch):
        monkeypatch.setattr(config.summarization, "summary_length", "short")
        result = summarizer.summarize(SENTENCES, PROCESSED_DATA)
        # short → 3 sentences max
        assert len(result.get("selected_sentences", [])) <= 3
        # No manual restore needed — monkeypatch auto-restores after test

    def test_single_sentence_handled(self, summarizer):
        result = summarizer.summarize(
            ["Only one sentence here."], {"sentences": ["Only one sentence here."]}
        )
        assert result["summary"]


class TestSummarizerDispatcher:
    def test_extractive_mode_works_offline(self, monkeypatch):
        monkeypatch.setattr(config.summarization, "method", "extractive")
        s = Summarizer()
        result = s.summarize(PROCESSED_DATA)
        assert result["summary"]
        assert result["method_used"] == "extractive"
        # No manual restore needed — monkeypatch auto-restores after test

    def test_generative_falls_back_when_no_key(self, monkeypatch):
        # No API key → should fall back to extractive (use_fallback=True)
        monkeypatch.setattr(config.summarization, "method", "generative")
        monkeypatch.setattr(config.gemini, "api_key", "")
        monkeypatch.setattr(config.summarization, "use_fallback", True)
        s = Summarizer()
        result = s.summarize(PROCESSED_DATA)
        assert result["summary"]
        # No manual restore needed — monkeypatch auto-restores after test


PT_SENTENCES = [
    "A inteligência artificial está transformando muitas indústrias ao redor do mundo.",
    "Algoritmos de aprendizado de máquina podem identificar padrões em grandes conjuntos de dados.",
    "O processamento de linguagem natural permite que computadores entendam textos humanos.",
    "Modelos de aprendizado profundo alcançaram desempenho super-humano em tarefas de imagem.",
    "O aprendizado por reforço permite que agentes aprendam por tentativa e erro.",
    "Aplicações de IA incluem saúde, finanças e veículos autônomos.",
    "Considerações éticas são cada vez mais importantes no desenvolvimento de IA.",
    "Pesquisadores trabalham para tornar os sistemas de IA mais transparentes e justos.",
]

PT_PROCESSED = {
    "sentences": PT_SENTENCES,
    "clean_text": " ".join(PT_SENTENCES),
    "language": "pt",
    "paragraphs": [" ".join(PT_SENTENCES)],
    "statistics": {"word_count": 80, "sentence_count": 8},
}


class TestLanguageAwareStopWords:
    @pytest.fixture
    def summarizer(self):
        return ExtractiveSummarizer()

    def test_portuguese_stop_words_loaded(self, summarizer):
        sw = summarizer._get_stop_words("pt")
        assert isinstance(sw, list)
        # Common Portuguese stopwords must be present
        assert "de" in sw or "que" in sw

    def test_english_returns_string(self, summarizer):
        assert summarizer._get_stop_words("en") == "english"

    def test_unknown_lang_falls_back_to_english(self, summarizer):
        assert summarizer._get_stop_words("xx") == "english"

    def test_portuguese_summary_produced(self, summarizer):
        result = summarizer.summarize(PT_SENTENCES, PT_PROCESSED)
        assert result["summary"]
        assert len(result["selected_sentences"]) >= 1
