"""Fake determinístico da porta de LLM (sem rede, sem chave de API)."""

from __future__ import annotations

import json
from collections.abc import Callable, Iterable

from .base import LLMRequest, LLMResponse

DEFAULT_FAKE_SUMMARY = "Resumo determinístico gerado pelo FakeLLMClient."


class FakeLLMClient:
    """Implementação em memória de :class:`modules.llm.base.LLMClient`.

    - ``failures``: exceções levantadas, em ordem, nas primeiras chamadas
      (ex.: ``[LLMTransientError("503")] * 2`` falha 2 vezes e depois responde).
    - ``responses``: textos devolvidos em ordem após as falhas; o último se
      repete. Sem ``responses``, devolve JSON ``{"summary": DEFAULT_FAKE_SUMMARY}``.
    - ``responder``: alternativa a ``responses`` — função ``LLMRequest -> str``.

    Todas as requisições recebidas ficam em ``calls`` para inspeção.
    """

    def __init__(
        self,
        *,
        responses: Iterable[str] | None = None,
        failures: Iterable[BaseException] | None = None,
        responder: Callable[[LLMRequest], str] | None = None,
        model_name: str = "fake-llm",
    ) -> None:
        self.model_name = model_name
        self._responses = list(responses or [])
        self._failures = list(failures or [])
        self._responder = responder
        self.calls: list[LLMRequest] = []

    @property
    def call_count(self) -> int:
        return len(self.calls)

    def generate(self, request: LLMRequest) -> LLMResponse:
        self.calls.append(request)
        if self._failures:
            raise self._failures.pop(0)
        if self._responder is not None:
            text = self._responder(request)
        elif self._responses:
            text = self._responses.pop(0) if len(self._responses) > 1 else self._responses[0]
        else:
            text = json.dumps({"summary": DEFAULT_FAKE_SUMMARY}, ensure_ascii=False)
        return LLMResponse(
            text=text,
            model=self.model_name,
            usage={"prompt_chars": len(request.system_instruction) + len(request.user_content)},
        )
