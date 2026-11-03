"""Integration tests for the full ArticleSummarizerAgent pipeline."""

from __future__ import annotations

import pytest

SAMPLE_HTML = """
<article>
<h1>Machine Learning Fundamentals</h1>
<p>Machine learning is a branch of artificial intelligence that enables systems to learn and improve from experience without being explicitly programmed. It focuses on developing computer programs that can access data and use it to learn for themselves.</p>
<p>Supervised learning is the most common type of machine learning. In supervised learning, the algorithm learns from labeled training data, helping it predict outcomes for unforeseen data. Common algorithms include linear regression, decision trees, and neural networks.</p>
<p>Unsupervised learning finds hidden patterns in data without pre-existing labels. Clustering and dimensionality reduction are typical unsupervised tasks. K-means clustering groups similar data points together without knowing the categories in advance.</p>
<p>Reinforcement learning trains agents to make decisions by rewarding desirable behaviors and punishing undesirable ones. This approach has achieved superhuman performance in games like Go and Chess, and is being applied to robotics and autonomous driving.</p>
<p>Deep learning, a subset of machine learning, uses neural networks with many layers to learn representations of data. Convolutional neural networks excel at image recognition, while recurrent networks handle sequential data like text and speech.</p>
</article>
"""


@pytest.fixture
def mock_scraper(monkeypatch):
    """Replace WebScraper.scrape_article with a function returning sample data."""

    def fake_scrape(self, url):
        import time

        return {
            "content": "Machine learning is a branch of artificial intelligence that enables systems to learn and improve from experience without being explicitly programmed. It focuses on developing computer programs that can access data and use it to learn for themselves. Supervised learning is the most common type of machine learning. In supervised learning the algorithm learns from labeled training data helping it predict outcomes for unforeseen data. Common algorithms include linear regression decision trees and neural networks. Unsupervised learning finds hidden patterns in data without pre-existing labels. Clustering and dimensionality reduction are typical unsupervised tasks. Reinforcement learning trains agents to make decisions by rewarding desirable behaviors and punishing undesirable ones. Deep learning a subset of machine learning uses neural networks with many layers to learn representations of data.",
            "title": "Machine Learning Fundamentals",
            "url": url,
            "word_count": 120,
            "author": "",
            "publish_date": "",
            "description": "",
            "scraped_at": time.time(),
            "encoding": "utf-8",
            "status_code": 200,
            "extraction_method": "article",
        }

    from modules import web_scraper

    monkeypatch.setattr(web_scraper.WebScraper, "scrape_article", fake_scrape)


class TestPipelineIntegration:
    def test_extractive_pipeline_end_to_end(self, mock_scraper):
        from main import ArticleSummarizerAgent

        agent = ArticleSummarizerAgent()
        result = agent.run("https://example.com/ml-article", method="extractive", length="short")
        assert result["success"] is True
        assert len(result["summary"]) > 20
        assert result["method_used"] == "extractive"
        assert "execution_time" in result

    def test_pipeline_returns_statistics(self, mock_scraper):
        from main import ArticleSummarizerAgent

        agent = ArticleSummarizerAgent()
        result = agent.run("https://example.com/ml-article", method="extractive", length="medium")
        assert result["success"] is True
        stats = result.get("statistics", {})
        assert isinstance(stats, dict)

    def test_pipeline_creates_output_files(self, mock_scraper, tmp_path, monkeypatch):
        monkeypatch.setenv("OUTPUT_DIR", str(tmp_path))
        # Re-init config to pick up new OUTPUT_DIR
        import config as cfg_module

        cfg_module.config.output.output_dir = str(tmp_path)

        from main import ArticleSummarizerAgent

        agent = ArticleSummarizerAgent()
        result = agent.run("https://example.com/ml-article", method="extractive", length="short")
        assert result["success"] is True
        assert len(result.get("files_created", {})) > 0

    def test_pipeline_handles_generative_fallback(self, mock_scraper, monkeypatch):
        """When Gemini API key is missing, generative falls back to extractive."""
        from config import config

        # O antigo os.environ.pop não afetava config.gemini.api_key (já lido),
        # então o teste construía o cliente Gemini real com "test-key".
        monkeypatch.setattr(config.gemini, "api_key", "")

        from main import ArticleSummarizerAgent

        agent = ArticleSummarizerAgent()
        result = agent.run("https://example.com/ml-article", method="generative", length="short")
        # Should succeed via fallback
        assert result["success"] is True
        assert result["method_used"] == "extractive"

    def test_pipeline_generative_with_fake_llm(self, mock_scraper, monkeypatch, tmp_path):
        """Modo generativo ponta a ponta com o fake determinístico da porta de LLM."""
        from config import config
        from infrastructure.pipeline import ArticlePipelineRunner
        from modules.llm import FakeLLMClient
        from modules.llm.fake import DEFAULT_FAKE_SUMMARY
        from modules.summarizer import Summarizer

        monkeypatch.setattr(config.output, "output_dir", str(tmp_path))
        monkeypatch.setattr(config.output, "cache_enabled", False)
        fake = FakeLLMClient()
        runner = ArticlePipelineRunner(summarizer=Summarizer(llm_client=fake))

        result = runner.run("https://example.com/fake-llm", method="generative", length="long")

        assert result["success"] is True, result
        assert result["method_used"] == "generative"
        assert result["summary"] == DEFAULT_FAKE_SUMMARY
        assert fake.call_count == 1
        assert "8–10 sentences" in fake.calls[0].user_content  # length repassado ao LLM

    def test_cache_is_keyed_by_method_and_length(self, mock_scraper, monkeypatch, tmp_path):
        """Resultado extrativo em cache não pode ser devolvido a um pedido generativo."""
        from config import config
        from infrastructure.pipeline import ArticlePipelineRunner
        from modules.cache import FilesystemCacheBackend
        from modules.llm import FakeLLMClient
        from modules.summarizer import Summarizer

        monkeypatch.setattr(config.output, "output_dir", str(tmp_path))
        monkeypatch.setattr(config.output, "cache_enabled", True)
        fake = FakeLLMClient()
        runner = ArticlePipelineRunner(
            cache_backend=FilesystemCacheBackend(cache_dir=str(tmp_path / "cache"), ttl=60),
            summarizer=Summarizer(llm_client=fake),
        )
        url = "https://example.com/cache-key"

        first = runner.run(url, method="extractive", length="short")
        second = runner.run(url, method="generative", length="short")
        third = runner.run(url, method="generative", length="short")

        assert first["method_used"] == "extractive"
        assert second["method_used"] == "generative"
        assert third["method_used"] == "generative"
        assert fake.call_count == 1  # terceiro veio do cache da chave generativa
