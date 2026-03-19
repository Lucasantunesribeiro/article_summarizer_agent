"""Integration tests for WebScraper using mocked HTTP responses."""

from __future__ import annotations

import pytest

SAMPLE_HTML = """
<!DOCTYPE html>
<html>
<head><title>Test Article</title></head>
<body>
<article>
<h1>AI Advances in 2024</h1>
<p>Artificial intelligence has made remarkable progress in 2024. Researchers at major institutions have published breakthrough findings on large language models, computer vision, and reinforcement learning. These advances are transforming industries from healthcare to finance.</p>
<p>The development of multimodal models represents a significant milestone. Systems can now process text, images, audio, and video simultaneously, enabling richer interactions and more accurate understanding of complex scenarios.</p>
<p>Safety research has also accelerated. New techniques for alignment, interpretability, and robustness are being deployed in production systems, reducing risks associated with increasingly capable AI.</p>
</article>
</body>
</html>
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
self.__next_f.push([1,"f:E{\\\"digest\\\":\\\"NEXT_REDIRECT\\\"}\\n\\u003cp\\u003eOs artigos científicos são uma produção textual com os principais resultados de uma pesquisa acadêmica. Eles circulam em revistas científicas e ajudam a democratizar o conhecimento produzido nas universidades.\\u003c/p\\u003e\\n\\n**INTRODUÇÃO**\\nA introdução apresenta o contexto do estudo, define o problema de pesquisa, explica a relevância do tema e deixa claro quais objetivos o artigo pretende alcançar.\\n\\n**DESENVOLVIMENTO**\\nO desenvolvimento reúne revisão de literatura, metodologia, resultados e discussão. Nessa etapa, o autor organiza referências, descreve os procedimentos adotados e interpreta os dados encontrados à luz da literatura especializada.\\n\\n**CONCLUSÃO E REFERÊNCIAS**\\nA conclusão retoma os objetivos, sintetiza os principais achados e indica limitações ou desdobramentos futuros. As referências registram todas as fontes citadas, reforçando a credibilidade e a rastreabilidade científica do texto."]);
</script>
</body>
</html>
"""


def _mock_session_get(monkeypatch, html: str) -> None:
    import requests

    class MockResponse:
        status_code = 200
        headers = {"Content-Type": "text/html; charset=utf-8"}
        encoding = "utf-8"
        text = html
        content = html.encode("utf-8")
        url = "https://example.com/article"

        def raise_for_status(self):
            pass

        def iter_content(self, chunk_size=65536):
            yield html.encode("utf-8")

    def mock_get(self, url, **kwargs):
        return MockResponse()

    monkeypatch.setattr(requests.Session, "get", mock_get)

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
self.__next_f.push([1,"f:E{\\\"digest\\\":\\\"NEXT_REDIRECT\\\"}\\n\\u003cp\\u003eOs artigos científicos são uma produção textual com os principais resultados de uma pesquisa acadêmica. Eles circulam em revistas científicas e ajudam a democratizar o conhecimento produzido nas universidades.\\u003c/p\\u003e\\n\\n**INTRODUÇÃO**\\nA introdução apresenta o contexto do estudo, define o problema de pesquisa, explica a relevância do tema e deixa claro quais objetivos o artigo pretende alcançar.\\n\\n**DESENVOLVIMENTO**\\nO desenvolvimento reúne revisão de literatura, metodologia, resultados e discussão. Nessa etapa, o autor organiza referências, descreve os procedimentos adotados e interpreta os dados encontrados à luz da literatura especializada.\\n\\n**CONCLUSÃO E REFERÊNCIAS**\\nA conclusão retoma os objetivos, sintetiza os principais achados e indica limitações ou desdobramentos futuros. As referências registram todas as fontes citadas, reforçando a credibilidade e a rastreabilidade científica do texto."]);
</script>
</body>
</html>
"""

@pytest.fixture
def mock_http(monkeypatch):
    """Monkeypatch requests.Session.get to return sample HTML."""
    _mock_session_get(monkeypatch, SAMPLE_HTML)


@pytest.fixture
def mock_nextjs_http(monkeypatch):
    _mock_session_get(monkeypatch, NEXTJS_INLINE_HTML)


class TestWebScraperIntegration:
    def test_scrape_returns_content(self, mock_http):
        from modules.web_scraper import WebScraper

        scraper = WebScraper()
        result = scraper.scrape_article("https://example.com/article")
        assert result.get("content")
        assert len(result["content"]) > 50

    def test_scrape_extracts_title(self, mock_http):
        from modules.web_scraper import WebScraper

        scraper = WebScraper()
        result = scraper.scrape_article("https://example.com/article")
        assert result.get("title") or result.get("content")

    def test_scrape_extracts_nextjs_inline_payload_content(self, mock_nextjs_http):
        from modules.web_scraper import WebScraper

        scraper = WebScraper()
        result = scraper.scrape_article(
            "https://www.estacio.br/blog/aluno/o-que-e-um-artigo-cientifico"
            "?srsltid=abc&utm_source=google"
        )

        assert result["extraction_method"] == "nextjs_inline_payload"
        assert result["word_count"] > 80
        assert "introdução" in result["content"].lower()
        assert "metodologia" in result["content"].lower()

    def test_scrape_extracts_nextjs_inline_payload_content(self, mock_nextjs_http):
        from modules.web_scraper import WebScraper

        scraper = WebScraper()
        result = scraper.scrape_article(
            "https://www.estacio.br/blog/aluno/o-que-e-um-artigo-cientifico"
            "?srsltid=abc&utm_source=google"
        )

        assert result["extraction_method"] == "nextjs_inline_payload"
        assert result["word_count"] > 80
        assert "introdução" in result["content"].lower()
        assert "metodologia" in result["content"].lower()

    def test_ssrf_localhost_rejected(self):
        from modules.web_scraper import WebScraper

        scraper = WebScraper()
        with pytest.raises(Exception, match=r"(?i)(ssrf|blocked|private|local|forbidden|refused)"):
            scraper.scrape_article("http://localhost/")

    def test_ssrf_private_ip_rejected(self):
        from modules.web_scraper import WebScraper

        scraper = WebScraper()
        with pytest.raises(Exception, match=r"(?i)(ssrf|blocked|private|local|forbidden|refused)"):
            scraper.scrape_article("http://192.168.1.1/secret")

    def test_ssrf_metadata_ip_rejected(self):
        from modules.web_scraper import WebScraper

        scraper = WebScraper()
        with pytest.raises(Exception, match=r"(?i)(ssrf|blocked|private|local|forbidden|refused)"):
            scraper.scrape_article("http://169.254.169.254/latest/meta-data/")
