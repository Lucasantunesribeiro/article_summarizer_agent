"""
Generative Summarizer — LLM via porta ``LLMClient`` (Gemini por padrão)
=======================================================================

``LLMSummarizer`` depende apenas da porta :class:`modules.llm.LLMClient`:
em produção recebe :class:`modules.llm.gemini.GeminiLLMClient`; nos testes,
:class:`modules.llm.FakeLLMClient` (determinístico, sem rede, sem chave).

Fluxo de uma sumarização:
1. Monta o prompt com o artigo higienizado, truncado e delimitado como dado
   (``modules.prompt_safety.build_summary_prompt``).
2. Chama o LLM com retry exponencial + jitter apenas para erros transitórios
   (``modules.retry``), respeitando Retry-After, limite de tentativas e
   orçamento total de tempo.
3. Valida a saída (JSON ``{"summary": str}``, tamanho, sem HTML/URLs novas).

Configuration (env vars):
    GEMINI_API_KEY    — required for the real Gemini client.
    GEMINI_MODEL_ID   — default: gemini-2.5-flash-preview-05-20
    GEMINI_TIMEOUT, GEMINI_MAX_ATTEMPTS, GEMINI_RETRY_BASE_DELAY,
    GEMINI_RETRY_MAX_DELAY, GEMINI_TOTAL_TIMEOUT, GEMINI_MAX_SUMMARY_CHARS.
"""

from __future__ import annotations

import logging
import random
import time
from collections.abc import Callable
from dataclasses import replace

from config import config
from modules.llm.base import LLMClient, LLMRequest, LLMTransientError
from modules.prompt_safety import SUMMARY_JSON_SCHEMA, build_summary_prompt, validate_summary_output
from modules.retry import RetryDecision, RetryPolicy, retry_call

logger = logging.getLogger(__name__)

_LENGTH_INSTRUCTIONS: dict[str, str] = {
    "short": "Write a concise summary in 2–3 sentences.",
    "medium": "Write a balanced summary in 4–6 sentences covering the main points.",
    "long": "Write a detailed summary in 8–10 sentences preserving key details.",
}


def classify_llm_error(exc: BaseException) -> RetryDecision:
    """Somente ``LLMTransientError`` é re-tentado."""
    if isinstance(exc, LLMTransientError):
        return RetryDecision(retryable=True, retry_after=exc.retry_after)
    return RetryDecision(retryable=False)


def default_llm_retry_policy() -> RetryPolicy:
    return RetryPolicy(
        max_attempts=max(1, config.gemini.max_attempts),
        base_delay=config.gemini.retry_base_delay,
        max_delay=config.gemini.retry_max_delay,
        total_timeout=config.gemini.total_timeout,
    )


class LLMSummarizer:
    """Sumarizador generativo independente de provedor."""

    def __init__(
        self,
        client: LLMClient,
        *,
        retry_policy: RetryPolicy | None = None,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
        rng: Callable[[], float] = random.random,
        nonce: str | None = None,
    ) -> None:
        self._client = client
        self._retry_policy = retry_policy
        self._sleep = sleep
        self._clock = clock
        self._rng = rng
        self._nonce = nonce  # fixo só em testes; em produção é aleatório por chamada

    @property
    def model_name(self) -> str:
        return getattr(self._client, "model_name", "unknown")

    def summarize(self, processed_data: dict, length: str | None = None) -> dict:
        """Generate a summary from processed text data.

        Args:
            processed_data: Output from TextProcessor.process_text().
            length: "short" | "medium" | "long" (overrides config if given).

        Returns:
            Dict with keys: summary, method_used, model_name, input_chars,
            output_chars, usage, input_truncated.

        Raises:
            ValueError: no text to summarise.
            LLMError subclasses: provider failure or output rejected by validation.
        """
        summary_length = length or config.summarization.summary_length
        length_instruction = _LENGTH_INSTRUCTIONS.get(
            summary_length, _LENGTH_INSTRUCTIONS["medium"]
        )

        # Prefer filtered sentences over raw clean_text so that navigation
        # noise and reference fragments are excluded from the prompt.
        sentences: list[str] = processed_data.get("sentences", [])
        clean_text = " ".join(sentences) if sentences else processed_data.get("clean_text", "")
        if not clean_text.strip():
            raise ValueError("No text available for summarisation.")

        prompt = build_summary_prompt(
            clean_text,
            length_instruction=length_instruction,
            max_chars=config.gemini.max_input_chars,
            nonce=self._nonce,
        )
        if not prompt.article_text:
            raise ValueError("No text available for summarisation.")
        if prompt.truncated:
            logger.info(
                "Input truncated to %d chars for LLM (limit %d)",
                len(prompt.article_text),
                config.gemini.max_input_chars,
            )

        base_request = LLMRequest(
            system_instruction=prompt.system_instruction,
            user_content=prompt.user_content,
            max_output_tokens=config.gemini.max_output_tokens,
            temperature=config.gemini.temperature,
            timeout_seconds=float(config.gemini.timeout),
            json_schema=SUMMARY_JSON_SCHEMA,
        )

        def _attempt(remaining: float):
            timeout = max(1.0, min(float(config.gemini.timeout), remaining))
            return self._client.generate(replace(base_request, timeout_seconds=timeout))

        logger.info(
            "Requesting LLM summary — model=%r length=%r chars=%d",
            self.model_name,
            summary_length,
            len(prompt.article_text),
        )
        response = retry_call(
            _attempt,
            policy=self._retry_policy or default_llm_retry_policy(),
            classify=classify_llm_error,
            sleep=self._sleep,
            clock=self._clock,
            rng=self._rng,
            description=f"LLM {self.model_name}",
        )

        summary_text = validate_summary_output(
            response.text,
            prompt=prompt,
            max_chars=config.gemini.max_summary_chars,
        )

        logger.info("LLM summary complete — %d output chars", len(summary_text))
        return {
            "summary": summary_text,
            "method_used": "generative",
            "model_name": response.model,
            "input_chars": len(prompt.article_text),
            "input_truncated": prompt.truncated,
            "output_chars": len(summary_text),
            "usage": response.usage,
        }


class GeminiSummarizer(LLMSummarizer):
    """``LLMSummarizer`` com o adaptador Gemini como cliente padrão."""

    def __init__(self, client: LLMClient | None = None, **kwargs) -> None:
        if client is None:
            from modules.llm.gemini import GeminiLLMClient  # noqa: PLC0415

            client = GeminiLLMClient(api_key=config.gemini.api_key, model_id=config.gemini.model_id)
            logger.info("GeminiSummarizer initialised with model %r", client.model_name)
        super().__init__(client, **kwargs)
