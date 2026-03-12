# Article Summarizer Agent

Plataforma web para extracao, processamento e sumarizacao de artigos publicos com pipeline assincromo, persistencia relacional, JWT, rate limiting, cache e observabilidade.

## O que o projeto faz

O sistema recebe uma URL publica, extrai o conteudo do artigo, processa o texto, gera um resumo por TF-IDF ou Google Gemini e disponibiliza:

- status assincromo por `task_id`
- historico persistido em banco
- download do resultado em `txt`, `md` e `json`
- painel web server-side
- API REST documentada em `/apidocs/`

## Arquitetura

O repositorio foi reorganizado como um monolito modular com separacao explicita de camadas:

- `presentation/`: Flask app factory e blueprints HTTP/HTML
- `application/`: commands, queries, handlers e event bus de aplicacao
- `domain/`: entidades, eventos e contratos de repositorio
- `infrastructure/`: repositorios SQLAlchemy, auth, container e runtime settings
- `modules/`: pipeline tecnico de scraping, NLP, cache, rate limiting e secrets rotation
- `tasks/`: integracao com Celery para processamento assincromo

### Padroes aplicados

- Clean Architecture pragmatica
  - `app.py` agora e apenas bootstrap do WSGI.
  - os casos de uso ficam em handlers da camada `application`.
- CQRS leve
  - operacoes de escrita usam commands (`SubmitSummarizationCommand`, `UpdateSettingsCommand`)
  - operacoes de leitura usam queries (`GetTaskStatusQuery`, `GetSettingsQuery`)
- Event-driven interno
  - `TaskSubmitted`, `TaskCompleted`, `TaskFailed`, `UserAuthenticated`, `CacheCleared`, `JwtSecretRotated`
  - submissao publica evento e o dispatcher envia a execucao para Celery ou thread fallback
- Persistencia versionada
  - SQLAlchemy 2 + Alembic
- Runtime settings
  - configuracoes salvas na tabela `settings` sao aplicadas ao runtime sem reiniciar a aplicacao

## Stack

### Backend

- Python 3.10+
- Flask
- Flask-JWT-Extended
- SQLAlchemy 2
- Alembic
- Redis
- Celery
- Prometheus client
- Flasgger / Swagger

### Pipeline

- requests
- BeautifulSoup4
- NLTK
- scikit-learn
- google-genai
- tenacity

### Frontend

- Jinja2
- Bootstrap 5
- JavaScript vanilla

## Seguranca e confiabilidade

- protecao SSRF antes do scraping
- JWT por header e cookies
- CSRF habilitado para fluxos baseados em cookie JWT
- RBAC real com usuarios persistidos e senha hasheada
- audit trail para autenticacao, alteracao de settings, limpeza de cache e rotacao de segredo
- rate limiting separado para submit, auth, polling e rotas administrativas
- rotacao de segredo JWT com `kid` e grace period
- headers de seguranca e CSP com nonce
- circuit breaker e retry para scraping

## Fluxo principal

1. Cliente envia `POST /api/sumarizar`.
2. A API valida URL, metodo, tamanho e aplica rate limiting.
3. O handler cria a tarefa, persiste no banco e publica `TaskSubmitted`.
4. O dispatcher envia para Celery quando disponivel; caso contrario usa thread local.
5. O pipeline executa scraping, processamento, sumarizacao e persistencia dos artefatos.
6. O handler atualiza a tarefa e publica `TaskCompleted` ou `TaskFailed`.
7. O cliente consulta `GET /api/tarefa/<task_id>` ate a conclusao.

## Estrutura do repositorio

```text
article_summarizer_agent/
├── app.py
├── main.py
├── application/
├── domain/
├── infrastructure/
├── modules/
├── presentation/
├── tasks/
├── templates/
├── static/
├── alembic/
├── tests/
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── requirements-dev.txt
```

## Execucao local

### 1. Instalar dependencias

Linux/macOS:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
```

### 2. Configurar ambiente

```bash
cp .env.example .env
```

Variaveis mais importantes:

- `SECRET_KEY`
- `DATABASE_URL`
- `REDIS_URL`
- `ADMIN_USER`
- `ADMIN_PASSWORD`
- `GEMINI_API_KEY` (somente modo generative)

### 3. Aplicar migrations

```bash
./.venv/Scripts/python -m alembic upgrade head
```

### 4. Rodar a aplicacao

Linux/macOS:

```bash
FLASK_DEBUG=true python app.py
```

Windows PowerShell:

```powershell
./scripts/dev.ps1 -Task run
```

### 5. Rodar com Docker Compose

```bash
docker compose up --build
```

## Comandos uteis

```bash
ruff check .
ruff format .
pytest tests -q
pytest tests --cov --cov-report=term-missing -q
```

Atalhos:

- `make setup`
- `make test`
- `make test-cov`
- `make db-upgrade`
- `./scripts/dev.ps1 -Task test`

## API principal

| Metodo | Endpoint | Descricao |
|---|---|---|
| `POST` | `/api/sumarizar` | Cria uma tarefa de sumarizacao |
| `GET` | `/api/tarefa/<task_id>` | Consulta status e resultado |
| `GET` | `/api/download/<task_id>/<fmt>` | Baixa `txt`, `md` ou `json` |
| `GET` | `/api/status` | Status tecnico do pipeline |
| `GET` | `/api/estatisticas` | Estatisticas agregadas de tarefas |
| `POST` | `/api/auth/login` | Login administrativo |
| `GET` | `/api/auth/me` | Identidade do usuario autenticado |
| `GET` | `/api/settings` | Le configuracoes persistidas |
| `PUT` | `/api/settings` | Atualiza configuracoes persistidas |
| `POST` | `/api/limpar-cache` | Limpa cache com JWT admin |
| `POST` | `/api/admin/rotate-secret` | Rotaciona segredo JWT |
| `GET` | `/health` | Health check |
| `GET` | `/metrics` | Metricas Prometheus |

## Testes

Estado atual da suite:

- `96 passed, 1 skipped`
- cobertura total: `76.89%`
- lint: `ruff check .` verde

Os testes cobrem:

- API e autorizacao
- settings e RBAC
- cache e secrets rotation
- sumarizador e processador de texto
- guardas SSRF
- integracao do pipeline

## Observacoes de produto

- o frontend e server-side com Jinja2, nao React
- o broker padrao da stack assincroma e Redis/Celery
- o event bus atual e interno ao monolito; nao ha outbox nem integracao entre servicos externos

## Portfolio

O dossie tecnico detalhado do projeto esta em `Descricao_Portfolio.md`.
