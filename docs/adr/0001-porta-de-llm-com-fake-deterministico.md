# 0001 — Porta de LLM com fake determinístico nos testes

- Status: aceita
- Data: 2026-11-03

## Contexto

O modo generativo chamava o SDK `google-genai` direto de `GeminiSummarizer`. Para testar, era preciso uma `GEMINI_API_KEY` (a CI usava `"test-key"`) ou monkeypatch do SDK. Um teste de fallback removia a variável de ambiente depois de a config já ter sido lida e acabava construindo o cliente real. Não havia como simular falhas transitórias (429, 503, timeout) de forma reproduzível, nem verificar o que de fato era enviado ao modelo.

## Decisão

- Criar a porta `modules.llm.base.LLMClient` (`generate(LLMRequest) -> LLMResponse`). `LLMRequest` separa `system_instruction` de `user_content` e carrega timeout e schema de saída.
- Erros da porta: `LLMTransientError` (com `status` e `retry_after`), `LLMPermanentError` e `LLMOutputError`. Cada adaptador traduz os erros do seu SDK para essa hierarquia e **não** faz retry próprio.
- `GeminiLLMClient` é o adaptador de produção. Ele desliga o retry interno do SDK (`HttpRetryOptions(attempts=1)`) e aplica o timeout por requisição.
- `FakeLLMClient` é o adaptador de teste: sem rede, respostas roteirizadas, falhas injetáveis (`failures=[...]`) e registro das requisições (`calls`).
- `LLMSummarizer` depende só da porta. `Summarizer(llm_client=...)` e `ArticlePipelineRunner(summarizer=...)` aceitam injeção.
- `tests/conftest.py` zera `GEMINI_API_KEY`, faz `GeminiLLMClient.generate` falhar se for chamado e bloqueia conexões que não sejam loopback.

## Consequências

- A CI roda sem chave e sem rede externa. Um teste que tente o provedor real falha alto.
- Retry, validação de saída e defesa contra prompt injection são testados de ponta a ponta com o fake.
- Trocar ou adicionar um provedor exige só um novo adaptador.
- O adaptador Gemini em si só é coberto por testes com o SDK mockado. Mudanças de contrato da API real só aparecem em uso real.
