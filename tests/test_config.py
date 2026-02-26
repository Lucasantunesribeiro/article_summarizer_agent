"""
Tests for config.py — attribute names, defaults, and env-var overrides.
"""


def test_config_has_english_attributes():
    from config import config
    # All modules expect these — test they all exist
    assert hasattr(config, "scraping")
    assert hasattr(config, "processing")
    assert hasattr(config, "summarization")
    assert hasattr(config, "gemini")
    assert hasattr(config, "output")
    assert hasattr(config, "logging")
    assert hasattr(config, "model")
    assert hasattr(config, "rate_limit")


def test_scraping_config_defaults():
    from config import config
    assert config.scraping.timeout > 0
    assert config.scraping.max_retries > 0
    assert config.scraping.max_content_bytes > 0
    assert isinstance(config.scraping.blocked_cidrs, list)
    assert "127.0.0.0/8" in config.scraping.blocked_cidrs
    assert "169.254.0.0/16" in config.scraping.blocked_cidrs


def test_constants_are_exported():
    from config import (
        CONTENT_SELECTORS,
        DEFAULT_LANGUAGE,
        SUPPORTED_FORMATS,
        SUPPORTED_LANGUAGES,
        UNWANTED_SELECTORS,
    )
    assert isinstance(CONTENT_SELECTORS, list)
    assert len(CONTENT_SELECTORS) > 0
    assert "article" in CONTENT_SELECTORS
    assert isinstance(UNWANTED_SELECTORS, list)
    assert "en" in SUPPORTED_LANGUAGES
    assert DEFAULT_LANGUAGE in SUPPORTED_LANGUAGES
    assert "txt" in SUPPORTED_FORMATS
    assert "md" in SUPPORTED_FORMATS
    assert "json" in SUPPORTED_FORMATS


def test_gemini_config_has_model_id():
    from config import config
    assert config.gemini.model_id  # not empty
    assert config.gemini.max_output_tokens > 0
    assert config.gemini.max_input_chars > 0


def test_output_config_defaults():
    from config import config
    assert "txt" in config.output.formats
    assert "md" in config.output.formats
    assert "json" in config.output.formats
    assert config.output.output_dir == "outputs"


def test_rate_limit_config():
    from config import config
    assert config.rate_limit.max_requests > 0
    assert config.rate_limit.window_seconds > 0


def test_update_from_args():
    import argparse

    from config import Config

    cfg = Config()
    args = argparse.Namespace(
        method="generative",
        length="short",
        output_dir="/tmp/out",
    )
    cfg.update_from_args(args)
    assert cfg.summarization.method == "generative"
    assert cfg.summarization.summary_length == "short"
    assert cfg.output.output_dir == "/tmp/out"
