"""Adaptador da porta de LLM para Google Gemini (SDK ``google-genai``).

Responsabilidades:
- Enviar ``system_instruction`` pelo canal de sistema do Gemini (separado do
  conteúdo do usuário) e pedir saída JSON quando houver ``json_schema``.
- Aplicar timeout por requisição.
- Desligar o retry interno do SDK (a política de retry é do chamador, em
  ``modules.retry``) para não multiplicar tentativas.
- Traduzir erros do SDK/HTTP em ``LLMTransientError`` / ``LLMPermanentError``.
"""

from __future__ import annotations

import logging
from typing import Any

from modules.retry import TRANSIENT_HTTP_STATUSES, parse_retry_after

from .base import LLMPermanentError, LLMRequest, LLMResponse, LLMTransientError

logger = logging.getLogger(__name__)

try:
    import google.genai as genai  # type: ignore[import]
    from google.genai import errors as genai_errors  # type: ignore[import]
    from google.genai import types as genai_types  # type: ignore[import]

    _GENAI_AVAILABLE = True
except ImportError:  # pragma: no cover - depende do ambiente
    _GENAI_AVAILABLE = False

try:
    import httpx

    _HTTPX_TRANSIENT: tuple[type[BaseException], ...] = (
        httpx.TimeoutException,
        httpx.TransportError,
    )
except ImportError:  # pragma: no cover
    _HTTPX_TRANSIENT = ()


def _retry_after_from(exc: Any) -> float | None:
    response = getattr(exc, "response", None)
    headers = getattr(response, "headers", None)
    if not headers:
        return None
    try:
        return parse_retry_after(headers.get("Retry-After"))
    except Exception:
        return None


def _http_options(timeout_ms: int | None = None) -> Any:
    """``HttpOptions`` com retry do SDK desligado (quando o SDK suporta)."""
    kwargs: dict[str, Any] = {}
    if timeout_ms is not None:
        kwargs["timeout"] = timeout_ms
    if "retry_options" in getattr(genai_types.HttpOptions, "model_fields", {}):
        kwargs["retry_options"] = genai_types.HttpRetryOptions(attempts=1)
    return genai_types.HttpOptions(**kwargs)


def translate_error(exc: BaseException) -> Exception:
    """Mapeia exceções do SDK/transporte para a hierarquia da porta."""
    if _GENAI_AVAILABLE and isinstance(exc, genai_errors.APIError):
        code = getattr(exc, "code", None)
        if isinstance(code, int) and code in TRANSIENT_HTTP_STATUSES:
            return LLMTransientError(
                f"Gemini HTTP {code}: {exc}", status=code, retry_after=_retry_after_from(exc)
            )
        return LLMPermanentError(f"Gemini HTTP {code}: {exc}", status=code)
    if _HTTPX_TRANSIENT and isinstance(exc, _HTTPX_TRANSIENT):
        return LLMTransientError(f"Gemini transporte: {exc}")
    if isinstance(exc, (TimeoutError, ConnectionError)):
        return LLMTransientError(f"Gemini transporte: {exc}")
    return LLMPermanentError(f"Gemini erro inesperado: {exc}")


class GeminiLLMClient:
    """Implementação de :class:`modules.llm.base.LLMClient` para Gemini."""

    def __init__(self, api_key: str, model_id: str) -> None:
        if not _GENAI_AVAILABLE:
            raise ImportError(
                "google-genai is required for Gemini summarisation. "
                "Install with: pip install 'google-genai>=1.0.0'"
            )
        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY environment variable is not set. "
                "Obtain a key at https://aistudio.google.com/app/apikey"
            )
        # attempts=1 → SDK não re-tenta; quem decide é modules.retry.
        self._client = genai.Client(api_key=api_key, http_options=_http_options())
        self.model_name = model_id

    def generate(self, request: LLMRequest) -> LLMResponse:
        cfg: dict[str, Any] = {
            "system_instruction": request.system_instruction,
            "max_output_tokens": request.max_output_tokens,
            "temperature": request.temperature,
            "http_options": _http_options(max(1, int(request.timeout_seconds * 1000))),
        }
        if request.json_schema is not None:
            cfg["response_mime_type"] = "application/json"
            cfg["response_json_schema"] = request.json_schema
        # Versões antigas do SDK não têm todos os campos; descarta os ausentes
        # (a validação de saída do chamador continua valendo).
        supported = getattr(genai_types.GenerateContentConfig, "model_fields", None)
        if supported:
            cfg = {k: v for k, v in cfg.items() if k in supported}

        try:
            response = self._client.models.generate_content(
                model=self.model_name,
                contents=request.user_content,
                config=genai_types.GenerateContentConfig(**cfg),
            )
        except Exception as exc:
            translated = translate_error(exc)
            logger.warning("Gemini API call failed: %s", translated)
            raise translated from exc

        usage: dict[str, Any] = {}
        meta = getattr(response, "usage_metadata", None)
        if meta is not None:
            usage = {
                "prompt_tokens": getattr(meta, "prompt_token_count", None),
                "candidates_tokens": getattr(meta, "candidates_token_count", None),
                "total_tokens": getattr(meta, "total_token_count", None),
            }
        return LLMResponse(text=response.text or "", model=self.model_name, usage=usage)
