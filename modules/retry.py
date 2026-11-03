"""
Retry com backoff exponencial + jitter para erros transitórios
==============================================================

Política única usada pelo fetch de artigos (``modules.web_scraper``) e pelas
chamadas ao LLM (``modules.gemini_summarizer``).

Regras:
- Só re-tenta o que o classificador marcar como transitório (timeout,
  falha de conexão, HTTP 408/425/429/5xx). Erros de input (4xx) falham na hora.
- Backoff exponencial com *full jitter*: ``uniform(0, min(max_delay, base * 2**n))``.
- ``Retry-After`` do servidor é respeitado (em vez do backoff calculado).
- Limites: número máximo de tentativas **e** orçamento total de tempo. Se a
  próxima espera estourar o orçamento, desiste imediatamente.

Relógio, ``sleep`` e gerador aleatório são injetáveis para testes
determinísticos (sem dormir de verdade).
"""

from __future__ import annotations

import email.utils
import logging
import random
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")

# Status HTTP considerados transitórios. 501/505 etc. não entram: não mudam
# com nova tentativa.
TRANSIENT_HTTP_STATUSES = frozenset({408, 425, 429, 500, 502, 503, 504})


@dataclass(frozen=True)
class RetryPolicy:
    """Parâmetros da política de retry."""

    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 30.0
    total_timeout: float = 60.0

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts deve ser >= 1")
        if self.base_delay < 0 or self.max_delay < 0 or self.total_timeout <= 0:
            raise ValueError("delays devem ser >= 0 e total_timeout > 0")


@dataclass(frozen=True)
class RetryDecision:
    """Resultado da classificação de uma exceção."""

    retryable: bool
    retry_after: float | None = None


class RetryBudgetExceeded(TimeoutError):
    """Orçamento total de tempo esgotado antes de uma resposta válida."""


def parse_retry_after(value: str | None, *, now: float | None = None) -> float | None:
    """Converte o header ``Retry-After`` (segundos ou HTTP-date) em segundos.

    Retorna ``None`` se ausente ou inválido. Valores negativos viram 0.
    """
    if value is None:
        return None
    value = str(value).strip()
    if not value:
        return None
    try:
        return max(0.0, float(value))
    except ValueError:
        pass
    try:
        parsed = email.utils.parsedate_to_datetime(value)
    except (TypeError, ValueError, IndexError):
        return None
    if parsed is None:
        return None
    current = time.time() if now is None else now
    return max(0.0, parsed.timestamp() - current)


def backoff_delay(attempt: int, policy: RetryPolicy, rng: Callable[[], float]) -> float:
    """Espera antes da tentativa ``attempt + 1`` (``attempt`` começa em 1)."""
    cap = min(policy.max_delay, policy.base_delay * (2 ** (attempt - 1)))
    return rng() * cap


def retry_call(
    fn: Callable[[float], T],
    *,
    policy: RetryPolicy,
    classify: Callable[[BaseException], RetryDecision],
    sleep: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.monotonic,
    rng: Callable[[], float] = random.random,
    description: str = "operação",
) -> T:
    """Executa ``fn`` com retry.

    ``fn`` recebe o tempo restante do orçamento (segundos) para que possa
    limitar o timeout da própria requisição.

    Levanta a última exceção original quando ela não é transitória ou quando
    as tentativas acabam. Levanta :class:`RetryBudgetExceeded` (encadeada à
    última exceção) quando o orçamento total não comporta a próxima espera.
    """
    start = clock()
    attempt = 0
    while True:
        attempt += 1
        remaining = policy.total_timeout - (clock() - start)
        if remaining <= 0:
            raise RetryBudgetExceeded(
                f"{description}: orçamento de {policy.total_timeout:.1f}s esgotado"
            )
        try:
            return fn(remaining)
        except Exception as exc:
            decision = classify(exc)
            if not decision.retryable:
                raise
            if attempt >= policy.max_attempts:
                logger.warning(
                    "%s: falha transitória após %d tentativa(s): %s", description, attempt, exc
                )
                raise

            if decision.retry_after is not None:
                delay = decision.retry_after
            else:
                delay = backoff_delay(attempt, policy, rng)

            remaining = policy.total_timeout - (clock() - start)
            if delay >= remaining:
                raise RetryBudgetExceeded(
                    f"{description}: próxima espera ({delay:.1f}s) excede o orçamento "
                    f"restante ({max(remaining, 0):.1f}s)"
                ) from exc

            logger.info(
                "%s: tentativa %d/%d falhou (%s); nova tentativa em %.2fs",
                description,
                attempt,
                policy.max_attempts,
                exc,
                delay,
            )
            sleep(delay)
