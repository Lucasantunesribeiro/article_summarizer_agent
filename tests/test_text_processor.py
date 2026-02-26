"""
Tests for TextProcessor — language detection, cleaning, sentence splitting.
"""

import pytest

from modules.text_processor import TextProcessor


@pytest.fixture(scope="module")
def processor():
    return TextProcessor()


SAMPLE_EN = """
Artificial intelligence (AI) is intelligence demonstrated by machines,
as opposed to the natural intelligence displayed by animals including humans.
AI research has been defined as the field of study of intelligent agents,
which refers to any system that perceives its environment and takes actions
that maximize its chance of achieving its goals.

The term "artificial intelligence" had previously been used to describe
machines that mimic and display "human" cognitive skills associated with
the human mind, such as "learning" and "problem-solving".
"""


class TestBasicProcessing:
    def test_returns_dict(self, processor):
        result = processor.process_text(SAMPLE_EN)
        assert isinstance(result, dict)

    def test_has_required_keys(self, processor):
        result = processor.process_text(SAMPLE_EN)
        for key in ("clean_text", "sentences", "paragraphs", "language", "statistics"):
            assert key in result, f"Missing key: {key}"

    def test_sentences_are_list_of_strings(self, processor):
        result = processor.process_text(SAMPLE_EN)
        sentences = result["sentences"]
        assert isinstance(sentences, list)
        assert len(sentences) >= 1
        assert all(isinstance(s, str) for s in sentences)

    def test_clean_text_is_string(self, processor):
        result = processor.process_text(SAMPLE_EN)
        assert isinstance(result["clean_text"], str)
        assert len(result["clean_text"]) > 0

    def test_language_detected(self, processor):
        result = processor.process_text(SAMPLE_EN)
        # Should detect English
        assert result["language"] in ("en", "pt")  # fallback is 'en'

    def test_statistics_word_count(self, processor):
        result = processor.process_text(SAMPLE_EN)
        stats = result["statistics"]
        assert stats["word_count"] > 0
        assert stats["sentence_count"] > 0


class TestEdgeCases:
    def test_empty_text_raises(self, processor):
        with pytest.raises((ValueError, Exception)):
            processor.process_text("")

    def test_whitespace_only_raises(self, processor):
        with pytest.raises((ValueError, Exception)):
            processor.process_text("   \n\t  ")

    def test_urls_removed_from_clean_text(self, processor):
        text = "Read more at https://example.com/page and http://other.org. Great article."
        result = processor.process_text(text)
        assert "https://" not in result["clean_text"]

    def test_short_text_processed(self, processor):
        text = "This is a complete sentence. And here is another one about AI."
        result = processor.process_text(text)
        assert len(result["sentences"]) >= 1


class TestSentenceFiltering:
    """Verify that noise patterns are correctly rejected by _is_valid_sentence."""

    def test_numbered_reference_fragment_filtered(self, processor):
        """Sentences like '3) de 2025 do periódico...' must be excluded."""
        text = (
            "This article presents new research on climate change. "
            "3) de 2025 do periódico Saúde e Sociedade, o dossiê reúne pesquisas. "
            "Scientists have identified key contributing factors to global warming. "
            "1. Another numbered item that should be excluded from the summary. "
            "The findings have significant implications for public policy worldwide."
        )
        result = processor.process_text(text)
        sentences = result["sentences"]
        for s in sentences:
            assert not s.strip().startswith(("3)", "1.")), (
                f"Numbered fragment leaked into sentences: {s!r}"
            )

    def test_copyright_line_filtered(self, processor):
        text = (
            "This is the main content of the article about technology. "
            "Copyright 2025 All rights reserved. "
            "The research was conducted over several years by the team."
        )
        result = processor.process_text(text)
        sentences = result["sentences"]
        for s in sentences:
            assert "copyright" not in s.lower(), f"Copyright line leaked: {s!r}"
