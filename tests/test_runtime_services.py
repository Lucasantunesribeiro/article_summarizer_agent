"""Tests for cache, secrets, and runtime configuration services."""
from __future__ import annotations

import time

from infrastructure.runtime_settings import RuntimeSettingsApplier
from modules.cache import FilesystemCacheBackend, create_cache_backend
from modules.rate_limiter import InMemoryRateLimiter
from modules.secrets_manager import SecretsManager


class TestFilesystemCacheBackend:
    def test_set_get_and_clear(self, tmp_path):
        backend = FilesystemCacheBackend(cache_dir=str(tmp_path), ttl=60)

        backend.set("abc", {"value": 1})
        assert backend.get("abc") == {"value": 1}

        backend.clear_all()
        assert backend.get("abc") is None

    def test_expired_entries_are_ignored(self, tmp_path, monkeypatch):
        backend = FilesystemCacheBackend(cache_dir=str(tmp_path), ttl=1)
        backend.set("abc", {"value": 1})
        monkeypatch.setattr(time, "time", lambda: backend._path("abc").stat().st_mtime + 2)

        assert backend.get("abc") is None

    def test_factory_falls_back_to_filesystem(self, monkeypatch):
        monkeypatch.delenv("REDIS_URL", raising=False)
        assert isinstance(create_cache_backend(ttl=60), FilesystemCacheBackend)


class TestSecretsManager:
    def test_rotate_keeps_previous_secret_during_grace_period(self, monkeypatch):
        monkeypatch.delenv("REDIS_URL", raising=False)
        monkeypatch.setenv("JWT_SECRET_KEY", "current-secret")
        manager = SecretsManager()
        previous_key_id = manager.get_current_key_id()

        result = manager.rotate(new_secret="next-secret", grace_period_seconds=60)

        assert result["rotated"] is True
        assert manager.get_current_secret() == "next-secret"
        assert manager.get_secret_for_kid(previous_key_id) == "current-secret"
        assert len(manager.get_all_valid_keys()) == 2

    def test_expired_secret_is_evicted_after_grace_period(self, monkeypatch):
        monkeypatch.delenv("REDIS_URL", raising=False)
        monkeypatch.setenv("JWT_SECRET_KEY", "current-secret")
        manager = SecretsManager()
        previous_key_id = manager.get_current_key_id()
        manager.rotate(new_secret="next-secret", grace_period_seconds=1)

        future = time.time() + 10
        monkeypatch.setattr(time, "time", lambda: future)

        assert manager.get_secret_for_kid(previous_key_id) is None
        assert len(manager.get_all_valid_keys()) == 1


class DummyPipelineRunner:
    def __init__(self) -> None:
        self.cache_backend = object()
        self.web_scraper = type("WebScraperStub", (), {"session": object(), "_build_session": lambda self: "session"})()
        self.summarizer = object()
        self.file_manager = type("FileManagerStub", (), {"cache_backend": object()})()


class TestRuntimeSettingsApplier:
    def test_apply_updates_runtime_components(self, monkeypatch):
        from config import config

        pipeline_runner = DummyPipelineRunner()
        rate_limiters = {
            "submit": InMemoryRateLimiter(10, 60),
            "auth": InMemoryRateLimiter(5, 300),
            "polling": InMemoryRateLimiter(60, 60),
            "admin": InMemoryRateLimiter(10, 300),
        }
        applier = RuntimeSettingsApplier(pipeline_runner, rate_limiters)
        monkeypatch.setattr("infrastructure.runtime_settings.create_cache_backend", lambda ttl: {"ttl": ttl})
        monkeypatch.setattr("infrastructure.runtime_settings.Summarizer", lambda: {"rebuilt": True})

        applier.apply(
            {
                "scraping.max_retries": 7,
                "summarization.default_method": "generative",
                "summarization.gemini_model_id": "gemini-test",
                "output.cache_ttl": 120,
                "rate_limit.admin.max_requests": 2,
            }
        )

        assert config.scraping.max_retries == 7
        assert config.summarization.method == "generative"
        assert config.gemini.model_id == "gemini-test"
        assert pipeline_runner.web_scraper.session == "session"
        assert pipeline_runner.summarizer == {"rebuilt": True}
        assert pipeline_runner.cache_backend == {"ttl": 120}
        assert pipeline_runner.file_manager.cache_backend == {"ttl": 120}
        assert isinstance(rate_limiters["admin"], InMemoryRateLimiter)
