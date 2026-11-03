"""Porta de LLM (interface + erros) e implementações.

- :class:`LLMClient` — protocolo que qualquer provedor implementa.
- :class:`modules.llm.gemini.GeminiLLMClient` — adaptador para Google Gemini.
- :class:`modules.llm.fake.FakeLLMClient` — fake determinístico para testes.
"""

from .base import (
    LLMClient,
    LLMError,
    LLMOutputError,
    LLMPermanentError,
    LLMRequest,
    LLMResponse,
    LLMTransientError,
)
from .fake import FakeLLMClient

__all__ = [
    "FakeLLMClient",
    "LLMClient",
    "LLMError",
    "LLMOutputError",
    "LLMPermanentError",
    "LLMRequest",
    "LLMResponse",
    "LLMTransientError",
]
