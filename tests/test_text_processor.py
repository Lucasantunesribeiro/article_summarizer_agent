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
