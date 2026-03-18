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

NEXTJS_INLINE_HTML = """
<!DOCTYPE html>
<html>
<head>
<title>Entenda tudo sobre um artigo científico | Blog Estácio</title>
</head>
<body>
<main><h1>Entenda tudo sobre um artigo científico | Blog Estácio</h1></main>
<script>
self.__next_f.push([1,"1:I[12846,[],\\\"\\\"]"]);
self.__next_f.push([1,"f:E{\\\"digest\\\":\\\"NEXT_REDIRECT\\\"}\\n\\u003cp\\u003eOs artigos científicos são uma produção textual com os principais resultados de uma pesquisa acadêmica. Em geral, eles são publicados em revistas científicas e ajudam a compartilhar descobertas com a comunidade acadêmica.\\u003c/p\\u003e\\n\\n**INTRODUÇÃO**\\nA introdução delimita o tema, apresenta o problema de pesquisa, contextualiza a relevância do estudo e informa os objetivos do trabalho.\\n\\n**DESENVOLVIMENTO**\\nO desenvolvimento reúne revisão de literatura, metodologia, resultados e discussão, mostrando como a pesquisa foi conduzida e quais evidências foram encontradas.\\n\\n**CONCLUSÃO E REFERÊNCIAS**\\nA conclusão sintetiza os achados, aponta limitações e sugere próximos passos. As referências listam as obras citadas e garantem respaldo científico ao artigo."]);
</script>
</body>
</html>
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

    def test_pipeline_handles_generative_fallback(self, mock_scraper):
        """When Gemini API key is missing, generative falls back to extractive."""
        import os

        os.environ.pop("GEMINI_API_KEY", None)

        from main import ArticleSummarizerAgent

        agent = ArticleSummarizerAgent()
        result = agent.run("https://example.com/ml-article", method="generative", length="short")
        # Should succeed via fallback
        assert result["success"] is True
        assert result["method_used"] in ("extractive", "generative")

    def test_pipeline_handles_nextjs_inline_payload_article(self, monkeypatch, tmp_path):
        import requests

        from config import config
        from main import ArticleSummarizerAgent

        class MockResponse:
            status_code = 200
            headers = {"Content-Type": "text/html; charset=utf-8"}
            encoding = "utf-8"
            text = NEXTJS_INLINE_HTML
            content = NEXTJS_INLINE_HTML.encode("utf-8")

            def raise_for_status(self):
                pass

            def iter_content(self, chunk_size=65536):
                yield NEXTJS_INLINE_HTML.encode("utf-8")

        def mock_get(self, url, **kwargs):
            return MockResponse()

        monkeypatch.setattr(requests.Session, "get", mock_get)
        monkeypatch.setattr(config.output, "output_dir", str(tmp_path / "outputs"))
        monkeypatch.setattr(config.output, "cache_dir", str(tmp_path / ".cache"))

        agent = ArticleSummarizerAgent()
        result = agent.run(
            "https://www.estacio.br/blog/aluno/o-que-e-um-artigo-cientifico"
            "?srsltid=abc&utm_source=google",
            method="extractive",
            length="short",
        )

        assert result["success"] is True
        assert len(result["summary"]) > 40
        assert result["method_used"] == "extractive"
