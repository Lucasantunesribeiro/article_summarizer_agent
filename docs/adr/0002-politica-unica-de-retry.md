# 0002 — Política única de retry com backoff exponencial e jitter

- Status: aceita
- Data: 2026-11-03

## Contexto

O fetch de artigos tinha dois retries empilhados: `urllib3.Retry` no `HTTPAdapter` da sessão (status 429/5xx) e `tenacity` em volta da chamada (timeout/conexão). Com `MAX_RETRIES_SCRAPING=3`, uma falha de conexão persistente podia gerar até 4 × 4 = 16 tentativas (o urllib3 também re-tenta erros de conexão), sem jitter e sem teto de tempo total. Qualquer erro, inclusive 404 ou URL bloqueada, contava como falha do host no circuit breaker. A chamada ao Gemini não tinha retry nem usava `GEMINI_TIMEOUT`.

## Decisão

Criar `modules/retry.py` e usá-lo no fetch e no LLM:

- Só re-tenta o que o classificador marca como transitório: timeout, falha de conexão e HTTP 408/425/429/500/502/503/504. Erros de input (4xx), TLS, SSRF e limite de tamanho falham na primeira tentativa.
- Backoff exponencial com *full jitter*: `uniform(0, min(max_delay, base * 2**(n-1)))`.
- `Retry-After` (segundos ou data HTTP) substitui o backoff calculado.
- Dois limites: número máximo de tentativas e orçamento total de tempo. Se a próxima espera não cabe no orçamento, desiste na hora (`RetryBudgetExceeded`). A função recebe o tempo restante e limita o timeout da própria requisição.
- O retry do urllib3 e do SDK do Gemini fica desligado. `tenacity` sai das dependências.
- Só falhas transitórias contam para o circuit breaker.
- Relógio, `sleep` e gerador aleatório são injetáveis, e os testes não dormem.

## Consequências

- Número de tentativas e tempo máximo de uma tarefa ficam previsíveis e configuráveis (`SCRAPING_*`, `GEMINI_*`).
- Um `Retry-After` maior que o orçamento faz a tarefa falhar rápido em vez de bloquear o worker.
- Política escrita à mão: mais código próprio para manter, em troca de controle sobre classificação e orçamento.
