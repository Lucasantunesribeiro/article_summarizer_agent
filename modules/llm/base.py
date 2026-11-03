"""Contrato da porta de LLM usada pelo sumarizador generativo."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True)
class LLMRequest:
    """Requisição neutra de provedor.

    ``system_instruction`` carrega as regras (canal de sistema); o texto do
    artigo vai **somente** em ``user_content``, já delimitado como dado.
    """

    system_instruction: str
    user_content: str
    max_output_tokens: int
    temperature: float
    timeout_seconds: float
    json_schema: dict[str, Any] | None = None


@dataclass(frozen=True)
class LLMResponse:
    text: str
    model: str
    usage: dict[str, Any] = field(default_factory=dict)


class LLMError(Exception):
    """Erro base da porta de LLM."""


class LLMTransientError(LLMError):
    """Falha que pode passar com nova tentativa (timeout, 429, 5xx)."""

    def __init__(
        self, message: str, *, status: int | None = None, retry_after: float | None = None
    ) -> None:
        super().__init__(message)
        self.status = status
        self.retry_after = retry_after


class LLMPermanentError(LLMError):
    """Falha que não muda com nova tentativa (4xx de input, chave inválida...)."""

    def __init__(self, message: str, *, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status


class LLMOutputError(LLMError):
    """Resposta do modelo reprovada na validação de saída."""


@runtime_checkable
class LLMClient(Protocol):
    """Porta: qualquer provedor de LLM implementa ``generate``.

    Implementações devem traduzir erros do SDK para
    :class:`LLMTransientError` / :class:`LLMPermanentError` e **não** fazer
    retry próprio — a política de retry fica no chamador.
    """

    model_name: str

    def generate(self, request: LLMRequest) -> LLMResponse: ...
