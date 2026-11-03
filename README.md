# Article Summarizer Agent

Aplicação web (Flask) que recebe a URL de um artigo público, extrai o texto, processa e gera um resumo **extrativo** (TF-IDF, local) ou **generativo** (LLM via Google Gemini). O processamento é assíncrono (Celery, com fallback para thread local) e o resultado fica persistido em banco, com download em `txt`, `md` e `json`.

## Arquitetura

Monólito modular em camadas:

- `presentation/`: app factory Flask e blueprints (`api`, `auth`, `web`). O blueprint `web` serve o SPA React compilado em `static/dist/`.
- `application/`: commands, queries, handlers e event bus interno.
- `domain/`: entidades, eventos e contratos de repositório.
- `infrastructure/`: repositórios SQLAlchemy, container de dependências, `ArticlePipelineRunner`, settings de runtime.
- `modules/`: scraping, NLP, sumarização, porta de LLM, retry, defesa contra prompt injection, cache, rate limiting, circuit breaker.
- `tasks/`: tasks Celery (sumarização e relay do outbox).
- `frontend/`: SPA React + Vite + Tailwind (build vai para `static/dist/`).

```mermaid
flowchart LR
    U[Navegador / cliente HTTP] --> API[Flask<br/>presentation/]
    API --> H[Handlers<br/>application/]
    H --> DB[(PostgreSQL ou SQLite<br/>SQLAlchemy + Alembic)]
    H --> OB[(tabela outbox)]
    H --> D{Dispatcher}
    D -->|Celery disponível| MQ[[RabbitMQ]] --> W[Worker Celery]
    D -->|fallback| T[Thread local]
    W --> P[ArticlePipelineRunner]
    T --> P
    P --> S[WebScraper<br/>SSRF por salto + retry]
    S --> NET((Internet))
    P --> TP[TextProcessor<br/>NLTK]
    P --> SUM[Summarizer]
    SUM --> EX[Extrativo TF-IDF]
    SUM --> LLM[LLMSummarizer<br/>prompt_safety + retry]
    LLM --> PORT{{Porta LLMClient}}
    PORT --> GEM[GeminiLLMClient]
    PORT -.testes.-> FAKE[FakeLLMClient]
    P --> FM[FileManager<br/>outputs/ + cache Redis ou disco]
    BEAT[Celery beat] --> RELAY[outbox_relay] --> MQ
```

### Fluxo de uma sumarização

1. `POST /api/sumarizar` valida a URL (esquema, SSRF), aplica rate limiting e cria a tarefa no banco.
2. O handler publica `TaskSubmitted`; o dispatcher envia para o Celery quando o broker responde, senão roda numa thread.
3. `ArticlePipelineRunner` consulta o cache (chave = método + tamanho + URL), faz o scraping, processa o texto, sumariza e grava os arquivos.
4. O cliente consulta `GET /api/tarefa/<task_id>` até o status final.

### Confiabilidade e segurança do pipeline

- **Fetch do artigo** (`modules/web_scraper.py`): redirects seguidos manualmente com validação SSRF em cada salto; bloqueio de faixas privadas, loopback, link-local/metadata, CGNAT, multicast, reservadas, NAT64 e IPv4 embutido em IPv6; limite de tamanho do corpo; circuit breaker por host.
- **Retry** (`modules/retry.py`): uma única política para fetch e LLM. Backoff exponencial com *full jitter*, só para erros transitórios (timeout, conexão, HTTP 408/425/429/5xx), respeitando `Retry-After`, com limite de tentativas e orçamento total de tempo. 4xx de input e erros de TLS falham na primeira tentativa.
- **LLM atrás de uma porta** (`modules/llm/`): `LLMSummarizer` depende só de `LLMClient`. Em produção usa `GeminiLLMClient` (retry interno do SDK desligado); nos testes usa `FakeLLMClient`, determinístico e sem rede.
- **Prompt injection** (`modules/prompt_safety.py`): o artigo é tratado como dado não confiável. É higienizado (controle, zero-width, bidi, *tag characters*), truncado, delimitado por tag com nonce aleatório e enviado separado da instrução de sistema, que manda ignorar ordens contidas no texto. A saída precisa ser JSON `{"summary": str}` e é rejeitada se trouxer HTML, URLs que não estão no artigo, o delimitador ou trechos do prompt de sistema. Resposta rejeitada cai no resumo extrativo.
- **API**: JWT (header e cookie, com CSRF para cookie), RBAC com usuários persistidos, rate limiting por grupo de rota, rotação do segredo JWT, cabeçalhos de segurança.

## Como rodar

### Local (Python 3.10+)

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
python -c "import nltk; [nltk.download(p, quiet=True) for p in ('punkt','punkt_tab','stopwords','wordnet')]"
cp .env.example .env               # ajuste os valores
FLASK_DEBUG=true python app.py
```

Sem `DATABASE_URL`, o app usa SQLite (`./dev.db`). As migrations Alembic rodam na inicialização (desligue com `SKIP_DB_MIGRATIONS_ON_STARTUP=true` e rode `python -m alembic upgrade head`). Sem `REDIS_URL`, cache e rate limiting usam memória/disco. Sem broker Celery acessível, as tarefas rodam em thread.

Frontend (opcional, para servir a interface em `/`):

```bash
cd frontend && npm install && npm run build   # gera static/dist/
```

Também há uma CLI: `python main.py --url <url> --method extractive --length short`.

### Docker Compose

```bash
cp .env.example .env    # opcional; sem .env o compose usa os valores internos
docker compose up --build
```

Sobe `api` (porta 5000), `worker` e `beat` (Celery), PostgreSQL, Redis, RabbitMQ (UI em 15672), Flower (5555), Prometheus (9090), Grafana (3001) e Jaeger (16686). As URLs de banco, Redis e RabbitMQ dos serviços da aplicação são definidas no próprio `docker-compose.yml` com os hostnames da rede do compose.

## Variáveis de ambiente

Lista completa com valores de exemplo em [`.env.example`](.env.example).

| Variável | Padrão | Descrição |
|---|---|---|
| `SECRET_KEY` | — | Obrigatória com `FLASK_DEBUG=false`. Assina sessão e JWT. |
| `FLASK_DEBUG` | `false` | `true` permite chave efêmera e cookies sem `Secure`. |
| `DATABASE_URL` | `sqlite:///./dev.db` | URL SQLAlchemy (PostgreSQL em produção). |
| `REDIS_URL` | vazio | Cache, rate limiting e segredos JWT compartilhados. Vazio = memória/disco. |
| `CELERY_BROKER_URL` / `RABBITMQ_URL` | `amqp://guest:guest@localhost:5672//` | Broker Celery e destino do outbox. |
| `CELERY_RESULT_BACKEND` | `redis://localhost:6379/2` | Backend de resultados Celery. |
| `ADMIN_USER` / `ADMIN_PASSWORD` | `admin` / — | Usuário admin semeado no banco. |
| `JWT_SECRET_KEY`, `JWT_EXPIRES_HOURS`, `JWT_COOKIE_CSRF_PROTECT` | — / `24` / `true` | Configuração do JWT. |
| `CORS_ORIGINS` | — | Origens permitidas (ex.: Vite em `http://localhost:5173`). |
| `SUMMARIZATION_METHOD` | `extractive` | `extractive` ou `generative`. |
| `SUMMARY_LENGTH` | `medium` | `short`, `medium` ou `long`. |
| `GEMINI_API_KEY` | vazio | Necessária só no modo generativo. Sem ela, cai no extrativo. |
| `GEMINI_MODEL_ID` | `gemini-2.5-flash-preview-05-20` | Modelo Gemini. |
| `GEMINI_TIMEOUT` | `30` | Timeout por requisição ao LLM (s). |
| `GEMINI_MAX_ATTEMPTS` | `3` | Tentativas para erros transitórios do LLM. |
| `GEMINI_RETRY_BASE_DELAY` / `GEMINI_RETRY_MAX_DELAY` | `1` / `20` | Base e teto do backoff (s). |
| `GEMINI_TOTAL_TIMEOUT` | `90` | Orçamento total de uma sumarização generativa (s). |
| `GEMINI_MAX_SUMMARY_CHARS` | `4000` | Resumo maior é rejeitado pela validação de saída. |
| `TIMEOUT_SCRAPING` | `30` | Timeout por requisição do fetch (s). |
| `MAX_RETRIES_SCRAPING` | `3` | Retentativas do fetch (total = 1 + retries). |
| `SCRAPING_RETRY_MAX_DELAY` | `16` | Teto do backoff do fetch (s). |
| `SCRAPING_TOTAL_TIMEOUT` | `90` | Orçamento total do fetch, incluindo esperas (s). |
| `SCRAPING_MAX_REDIRECTS` | `5` | Redirects seguidos (cada um revalidado contra SSRF). |
| `CIRCUIT_BREAKER_THRESHOLD` / `CIRCUIT_BREAKER_TIMEOUT` | `3` / `120` | Falhas para abrir o circuito por host e tempo aberto (s). |
| `CACHE_ENABLED` / `CACHE_TTL` / `OUTPUT_DIR` | `true` / `86400` / `outputs` | Cache de resultados e diretório de saída. |
| `RATE_LIMIT_*`, `AUTH_RATE_LIMIT_*`, `POLL_RATE_LIMIT_*`, `ADMIN_RATE_LIMIT_*` | ver `.env.example` | Limites por grupo de rota. |
| `TRUSTED_PROXY_HOPS` | `0` | Proxies confiáveis à frente do app. `0` ignora `X-Forwarded-For`; `1` usa o valor anexado pelo proxy (ex.: Render). |
| `METRICS_TOKEN` | vazio | Token exigido em `/metrics`, se definido. |
| `OTEL_ENABLED`, `OTEL_EXPORTER_OTLP_ENDPOINT`, `OTEL_SERVICE_NAME` | `false` | Tracing OpenTelemetry. |
| `LOG_LEVEL` | `INFO` | Nível de log. |

## API

| Método | Endpoint | Descrição |
|---|---|---|
| `POST` | `/api/sumarizar` | Cria uma tarefa de sumarização |
| `GET` | `/api/tarefa/<task_id>` | Status e resultado |
| `GET` | `/api/download/<task_id>/<fmt>` | Baixa `txt`, `md` ou `json` |
| `GET` | `/api/historico` | Histórico de tarefas |
| `GET` | `/api/status` | Status técnico do pipeline |
| `GET` | `/api/estatisticas` | Estatísticas agregadas |
| `POST` | `/api/auth/login`, `/api/auth/refresh`, `/api/auth/logout`, `/api/auth/register` | Autenticação |
| `GET` | `/api/auth/me` | Usuário autenticado |
| `GET`/`PUT` | `/api/settings` | Lê/atualiza settings persistidas (admin) |
| `POST` | `/api/limpar-cache` | Limpa cache (admin) |
| `POST` | `/api/admin/rotate-secret` | Rotaciona o segredo JWT (admin) |
| `GET` | `/health`, `/metrics` | Health check e métricas Prometheus |

Documentação Swagger (Flasgger) em `/apidocs/`.

## Testes

```bash
pip install -r requirements-dev.txt
pytest -q
ruff check . && ruff format --check .
```

- Nenhum teste chama um LLM real nem precisa de `GEMINI_API_KEY`: `tests/conftest.py` zera a chave, faz o adaptador Gemini falhar se for usado e bloqueia conexões de rede que não sejam loopback. O modo generativo é testado com `FakeLLMClient`, inclusive falhas transitórias simuladas e um artigo malicioso (`tests/test_llm_summarizer.py`, `tests/test_prompt_safety.py`).
- Retry e SSRF do fetch são testados com sessão HTTP roteirizada e DNS falso (`tests/test_retry.py`, `tests/test_fetch_retry.py`, `tests/test_ssrf.py`).
- `tests/test_db_integration.py` usa `pytest-postgresql`, que sobe um PostgreSQL temporário com o `pg_ctl` da máquina. Sem PostgreSQL instalado (ou rodando como root), esses testes dão erro no setup.

A CI (`.github/workflows/ci.yml`) roda lint, testes e `docker build` em pull requests e em push para `main`.

## Deploy gratuito (Render)

Demo pública: <https://article-summarizer-agent.onrender.com> (plano free do Render; após inatividade o serviço dorme e a primeira requisição pode levar cerca de 1 minuto).

O [`render.yaml`](render.yaml) descreve um único web service no plano `free`:

- **Build** (`render-build.sh`): instala dependências Python, aplica as migrations e compila o SPA React (`frontend/` para `static/dist/`).
- **Start** (`render-start.sh`): Gunicorn com 1 worker e 4 threads.
- **Sem Celery**: o Render não tem plano gratuito para background workers. Sem broker, cada sumarização roda numa thread do processo web.
- **Banco**: sem `DATABASE_URL`, usa SQLite no disco efêmero do serviço. O histórico some a cada deploy ou reinício. Para persistir de graça, crie um Postgres no [Neon](https://neon.tech) ou no [Supabase](https://supabase.com) e defina `DATABASE_URL`.
- **Redis** (opcional): sem `REDIS_URL`, cache e rate limiting ficam em memória/disco do processo. O [Upstash](https://upstash.com) tem Redis gratuito.

Passo a passo:

1. No Render, **New > Blueprint** e selecione este repositório (branch `main`).
2. Preencha as variáveis pedidas pelo painel (as marcadas com `sync: false`):
   - `SECRET_KEY`: string aleatória longa (ex.: `python -c "import secrets; print(secrets.token_urlsafe(48))"`).
   - `ADMIN_PASSWORD`: senha do usuário `admin`.
   - `GEMINI_API_KEY`: opcional. Deixe vazio para a demo só extrativa. Se usar, gere a chave no plano gratuito do Google AI Studio, sem faturamento ativado.
3. O Render faz deploy automático a cada push na `main`. Pull requests não disparam deploy.

Proteções contra custo e abuso na demo:

- Rate limit de submissão por IP (`RATE_LIMIT_MAX=5` por `RATE_LIMIT_WINDOW=60` s no `render.yaml`), além dos limites de login, polling e admin. O IP vem do valor que o proxy do Render anexa ao `X-Forwarded-For` (`TRUSTED_PROXY_HOPS=1`), não do que o cliente envia.
- Corpo da página limitado a 10 MB; entrada do LLM truncada em 30.000 caracteres; saída limitada a 1.024 tokens.
- Retry do LLM limitado (`GEMINI_MAX_ATTEMPTS=2`, `GEMINI_TOTAL_TIMEOUT=60`).
- A chave do LLM só existe como variável de ambiente no painel do Render, nunca no repositório.

## Decisões de arquitetura

ADRs em [`docs/adr/`](docs/adr/).

## Limitações conhecidas

- A defesa contra prompt injection reduz o risco, mas não o elimina: um modelo ainda pode ser influenciado pelo texto do artigo de formas que a validação de saída não detecta (ex.: resumo enviesado sem URL, HTML ou vazamento de prompt).
- A validação SSRF resolve o DNS antes da requisição, mas o `requests` resolve de novo ao conectar. Um DNS com TTL zero (*DNS rebinding*) ainda pode trocar o IP entre a checagem e a conexão.
- A imagem Docker não compila o frontend: sem `static/dist/`, `/` responde 503 com uma mensagem, e só a API funciona.
- O cache em disco usa MD5 da chave apenas como nome de arquivo (não é uso criptográfico).
- O event bus é interno ao processo; o outbox publica eventos no RabbitMQ, mas não há consumidores no repositório.
- O modo generativo só tem adaptador para Gemini.
