# Dossie Tecnico: Article Summarizer Agent

_Analise baseada no codigo, testes e artefatos reais do repositorio em 12 de marco de 2026._

## 1. Visao Geral do Projeto

O projeto e uma plataforma web para extracao e sumarizacao de artigos publicos da internet. O usuario informa uma URL, o sistema executa scraping com protecoes de seguranca, processa o texto, gera um resumo por metodo extrativo ou via Google Gemini e disponibiliza o resultado para consulta assincroma e download em `txt`, `md` e `json`.

O problema que ele resolve e reduzir tempo de leitura e transformar conteudo web extenso em uma saida estruturada e reutilizavel. O dominio continua sendo produtividade e NLP aplicado, mas o projeto foi evoluido para ficar mais proximo de um backend enterprise em organizacao interna, seguranca e operacao.

Hoje o sistema tambem cobre preocupacoes relevantes de engenharia:

- persistencia de tarefas e historico em banco relacional
- autenticacao administrativa com usuarios persistidos
- RBAC e auditoria
- fila assincroma com Celery quando Redis esta disponivel
- cache coerente entre pipeline e backend de cache
- metricas, health check e logs estruturados

## 2. Arquitetura do Sistema

Arquiteturalmente, o projeto agora e um **monolito modular com separacao por camadas**, mais proximo de uma Clean Architecture pragmatica do que da versao anterior concentrada em `app.py`.

Como o sistema esta organizado no codigo real:

- `presentation/`
  - `app_factory.py` monta Flask, JWT, CORS, Swagger, CSP, Prometheus e registra blueprints
  - `blueprints/api.py` expoe a API REST
  - `blueprints/auth.py` concentra login/logout/refresh/me
  - `blueprints/web.py` concentra as rotas HTML
- `application/`
  - `commands.py` e `queries.py` separam operacoes de escrita e leitura
  - `handlers/` implementa casos de uso como submit de tarefa, auth, settings e admin
  - `event_bus.py` publica eventos internos da aplicacao
- `domain/`
  - `entities.py` define `SummarizationTask`, `User`, `AuditLogEntry`, `SettingsEntry`
  - `events.py` define eventos como `TaskSubmitted`, `TaskCompleted`, `TaskFailed`, `UserAuthenticated`
  - `repositories.py` define contratos de persistencia
- `infrastructure/`
  - `repositories.py` implementa repositorios SQLAlchemy
  - `auth.py` faz hashing de senha e bootstrap do admin inicial
  - `runtime_settings.py` aplica settings persistidas no runtime
  - `container.py` faz o wiring do sistema
- `modules/`
  - concentra pipeline tecnico: scraper, NLP, sumarizador, cache, rate limiter, secrets rotation
- `tasks/`
  - integra o caso de uso de processamento com Celery

### Como os padroes aparecem de fato

- **Clean Architecture pragmatica**
  - `app.py` ficou fino e apenas chama `create_app()`
  - a borda HTTP nao conhece detalhes de scraping, NLP ou persistencia
  - os casos de uso passam por handlers da camada `application`
- **CQRS leve**
  - escrita: `SubmitSummarizationCommand`, `UpdateSettingsCommand`, `RotateJwtSecretCommand`
  - leitura: `GetTaskStatusQuery`, `GetTaskStatisticsQuery`, `GetSettingsQuery`
- **Event Driven interno**
  - submissao de tarefa publica `TaskSubmitted`
  - o dispatcher do container consome esse evento e envia o processamento para Celery ou thread fallback
  - conclusao, falha, autenticacao e rotacao de segredo viram eventos auditaveis
- **Modular Monolith**
  - nao e microservices
  - existe um unico deployable com modulos internos bem separados

Leitura honesta: o projeto hoje sustenta melhor a narrativa de arquitetura robusta e separacao de responsabilidades. Ainda nao e uma arquitetura enterprise completa com varios servicos, outbox e integracao externa orientada a eventos, mas passou a ter uma estrutura coerente e defensavel em entrevista.

## 3. Stack Tecnologica

### Backend

- **Python 3.10+**
  - linguagem principal do sistema
- **Flask**
  - exposicao de API REST, paginas server-side e rotas administrativas
- **Flask-JWT-Extended**
  - autenticacao via JWT por header e cookie
- **Flasgger**
  - documentacao Swagger em `/apidocs/`
- **Gunicorn**
  - execucao production-like

### Application / Domain

- **Commands / Queries / Handlers**
  - estrutura os casos de uso e separa leitura de escrita
- **Event bus interno**
  - desacopla submit, processamento e auditoria

### Banco de dados

- **SQLAlchemy 2**
  - ORM principal
- **Alembic**
  - versionamento do schema
- **PostgreSQL**
  - banco alvo para ambiente mais serio
- **SQLite**
  - fallback de desenvolvimento e base dos testes locais

### Mensageria e processamento assincromo

- **Redis**
  - cache distribuido opcional, rate limiter distribuido e broker/backend de jobs
- **Celery**
  - processamento assincromo de tarefas
- **Flower**
  - inspecao de workers

### NLP e IA

- **requests + BeautifulSoup4 + chardet**
  - scraping e parsing HTML
- **NLTK + langdetect**
  - limpeza, tokenizacao e deteccao de idioma
- **scikit-learn**
  - sumarizacao extrativa por TF-IDF
- **google-genai**
  - sumarizacao generativa com Gemini
- **tenacity**
  - retry com backoff

### Frontend

- **Jinja2**
  - renderizacao server-side
- **Bootstrap 5**
  - UI
- **JavaScript vanilla**
  - polling, auth utilities, download e interacoes administrativas

### Observabilidade e seguranca

- **prometheus_client**
  - `/metrics`
- **python-json-logger**
  - logs estruturados
- **CSP com nonce + security headers**
  - hardening de resposta
- **rate limiting por perfil**
  - submit, auth, polling e admin
- **JWT secret rotation com `kid`**
  - reduz risco de downtime em rotacao de segredo

### DevOps

- **Docker**
  - empacotamento
- **docker-compose**
  - stack local
- **GitHub Actions**
  - lint, testes e build
- **Makefile + `scripts/dev.ps1`**
  - DX para Unix e Windows PowerShell

## 4. Fluxo do Sistema

Fluxo real de execucao:

1. O cliente envia `POST /api/sumarizar` com URL, metodo e tamanho.
2. A API valida payload, normaliza URL e aplica rate limiting de submit.
3. O `SubmitSummarizationHandler` cria a entidade da tarefa, persiste e publica `TaskSubmitted`.
4. O container consome esse evento e envia a execucao para Celery quando Redis esta disponivel; sem broker, usa thread fallback.
5. O pipeline executa:
   - SSRF guard
   - scraping HTTP com retry e circuit breaker
   - processamento de texto e tokenizacao
   - sumarizacao por TF-IDF ou Gemini
   - persistencia de arquivos e cache
6. O `ProcessTaskHandler` atualiza status da tarefa e publica `TaskCompleted` ou `TaskFailed`.
7. O cliente acompanha com `GET /api/tarefa/<task_id>`.
8. Quando concluido, pode baixar os arquivos gerados ou consultar o historico persistido.

Fluxo administrativo:

1. O admin faz login com usuario persistido.
2. Recebe JWT e cookies.
3. Rotas protegidas exigem JWT; fluxos com cookie usam CSRF habilitado.
4. Alteracoes de settings, limpeza de cache e rotacao de segredo geram auditoria.

## 5. Conceitos de Engenharia Aplicados

- **SOLID: sim, de forma razoavel**
  - a separacao por camadas e handlers reduziu acoplamento
  - responsabilidades estao mais coesas do que na versao anterior
- **DDD: parcial**
  - existem entidades e eventos de dominio
  - ainda nao ha um dominio rico com agregados complexos e linguagem ubiqua forte
- **Clean Architecture: sim, em versao pragmatica**
  - presentation -> application -> domain/contracts -> infrastructure
  - a regra de dependencia ficou mais clara
- **CQRS: sim, em versao leve**
  - commands e queries estao separados
  - nao ha buses externos nem storage segregado
- **Event Driven: sim, internamente**
  - existem eventos de aplicacao e despacho assincromo
  - ainda nao ha integracao entre servicos externos
- **Outbox pattern: nao**
  - nao existe consistencia transacional banco + fila nesse nivel
- **Idempotencia: parcial**
  - cache por URL reduz reprocessamento
  - ainda nao ha idempotency key ou deduplicacao transacional de comandos
- **Retry: sim**
  - scraping com retry/backoff e processamento assincromo com reexecucao controlada
- **DLQ: nao explicita**
  - nao ha fila morta ou tratamento formal de poison message

## 6. Relevancia Para o Mercado Brasileiro

### O projeto demonstra skills demandadas?

Sim. O projeto demonstra varias competencias que aparecem em vagas reais:

- API REST
- banco relacional com migrations
- autenticacao e autorizacao
- Redis
- processamento assincromo
- testes automatizados
- Docker
- CI/CD
- observabilidade
- preocupacao com seguranca e abuso de API

### Ele parece um projeto enterprise?

Ele parece **enterprise-inspired com boa maturidade tecnica**. Nao chega a enterprise pleno porque:

- nao e microservices
- nao tem outbox, DLQ e mensageria de integracao entre servicos
- o dominio de negocio e simples
- nao ha cloud AWS implementada

Mesmo assim, o projeto transmite bem a ideia de backend robusto e organizado.

### Ele e relevante para vagas Junior?

Sim, bastante. Para vagas backend generalistas ele esta acima da media de portfolios junior. Para o alvo especifico do Lucas, existe um ponto de atencao: a stack principal continua sendo Python/Flask, nao .NET/React/AWS.

Leitura mais honesta para o mercado-alvo:

- como projeto de engenharia backend: forte
- como projeto alinhado a vagas Fullstack .NET + React: parcial
- como prova de maturidade tecnica no portfolio: muito valida

## 7. Como Explicar o Projeto em Entrevista

### Explicacao simples (30 segundos)

Desenvolvi uma plataforma que recebe URLs de artigos, extrai o conteudo, processa o texto e gera resumos automaticamente. O projeto tem API, historico persistido, processamento assincromo, autenticacao administrativa, cache, testes, Docker e monitoramento basico.

### Explicacao tecnica (2 minutos)

O sistema foi estruturado como um monolito modular com camadas de presentation, application, domain e infrastructure. A API nao chama o pipeline diretamente; ela aciona handlers de caso de uso. Quando uma URL chega ao endpoint de submit, o handler cria a tarefa, persiste no banco e publica um evento interno `TaskSubmitted`. O container consome esse evento e despacha o processamento para Celery quando Redis esta disponivel, ou para thread local como fallback.

No pipeline, o scraper aplica SSRF guard, retry, circuit breaker e limite de tamanho de resposta. Depois o texto passa por limpeza, deteccao de idioma e tokenizacao. A sumarizacao pode ser extrativa com TF-IDF ou generativa com Gemini. O resultado e salvo em arquivo, armazenado em cache e refletido no historico da tarefa. Para a area administrativa, implementei usuarios persistidos com senha hasheada, RBAC, auditoria, CSRF para JWT em cookies, rotacao de segredo com `kid` e rate limiting separado por perfil de rota.

## 8. Pontos Fortes do Projeto

- arquitetura muito mais clara do que um monolito concentrado em um unico arquivo
- uso real de commands, queries e handlers
- eventos internos de aplicacao para desacoplar submit e processamento
- autenticacao administrativa persistida com hashing e RBAC
- auditoria de autenticacao, settings, cache clear e rotacao de segredo
- CSRF habilitado para fluxos baseados em cookies JWT
- rate limiting separado para submit, auth, polling e admin
- cache coerente entre pipeline e backend de cache
- migrations com Alembic sem `create_all()` no startup do app
- DX melhor para Windows nativo com `scripts/dev.ps1`
- lint verde com `ruff check .`
- suite automatizada forte para portfolio: `96 passed, 1 skipped`
- cobertura atual de `76.89%`

## 9. Pontos a Melhorar

- **Aderencia ao alvo .NET/React/AWS**
  - o projeto continua em Python/Flask
- **Mensageria de integracao**
  - Celery + Redis cobre jobs, mas nao mensageria enterprise tipo RabbitMQ/SQS/Kafka
- **Outbox, DLQ e idempotencia forte**
  - ainda nao existem
- **Cloud**
  - nao ha deploy AWS implementado com artefatos IaC
- **Frontend**
  - a UI e funcional, mas continua server-side com Jinja2, nao React
- **Observabilidade**
  - existe Prometheus, logs e health, mas faltam tracing, dashboards e alertas
- **Testes de integracao de infraestrutura**
  - ha fixture para PostgreSQL, mas o teste foi pulado no ambiente auditado por indisponibilidade do provider local

## 10. Melhorias Prioritarias Para Portfolio

1. **Criar uma versao equivalente em ASP.NET Core + EF Core + PostgreSQL**
   - maior impacto para vagas .NET
2. **Adicionar um frontend React consumindo a API**
   - melhora aderencia para vagas Fullstack .NET + React
3. **Trocar ou complementar Celery/Redis com RabbitMQ ou AWS SQS**
   - aproxima o projeto do mercado enterprise brasileiro
4. **Levar a stack para AWS com artefatos reais**
   - ECS/Fargate ou App Runner, RDS, ElastiCache e observabilidade
5. **Adicionar outbox, DLQ e estrategia formal de idempotencia**
   - fortalece muito a narrativa de arquitetura distribuida
6. **Adicionar tracing e dashboards**
   - Prometheus + Grafana + OpenTelemetry elevariam o nivel operacional

## 11. Como Colocar no Curriculo

Plataforma backend para extracao e sumarizacao assincroma de artigos web, desenvolvida com Python, Flask, SQLAlchemy, Redis/Celery e JWT, estruturada em camadas de apresentacao, aplicacao, dominio e infraestrutura, com persistencia versionada, RBAC, auditoria, observabilidade e testes automatizados.

## 12. Nivel do Projeto

**Classificacao: Pleno**

Motivo:

- a estrutura interna, seguranca, persistencia, fila, cache, observabilidade e testes colocam o projeto acima de um portfolio junior comum
- a arquitetura ficou defensavel tecnicamente
- ele ainda nao chega a Enterprise-like porque faltam mensageria de integracao, outbox, DLQ, AWS e um dominio mais sofisticado

## 13. Checklist de Mercado

| Requisito Mercado | Presente no Projeto | Observacao |
|---|---|---|
| C# | Nao | Gap direto para vagas .NET |
| .NET / ASP.NET Core | Nao | Principal lacuna frente ao objetivo do candidato |
| React | Nao | Frontend atual e Jinja2 + Bootstrap |
| APIs REST | Sim | API Flask com submit, polling, auth, settings e admin |
| ORM | Sim | SQLAlchemy 2 |
| PostgreSQL | Parcial | Suportado e testado via fixture; teste PG ficou skip no ambiente auditado |
| SQL Server | Nao | Nao ha evidencia no repositorio |
| Docker | Sim | Dockerfile presente |
| Docker Compose | Sim | Stack local com servicos auxiliares |
| CI/CD | Sim | GitHub Actions |
| AWS | Nao | Ainda nao implementado |
| Azure | Nao | Ainda nao implementado |
| Redis | Sim | Cache, rate limiting distribuido e broker/backend de jobs |
| Mensageria real | Parcial | Celery + Redis para jobs; nao ha RabbitMQ, Kafka ou SQS |
| Microservices | Nao | E um monolito modular |
| Clean Architecture | Sim, pragmatica | Camadas explicitas e handlers de caso de uso |
| DDD | Parcial | Entidades e eventos existem; dominio ainda simples |
| CQRS | Sim, leve | Commands e queries separados |
| Event Driven | Sim, interno | Eventos de aplicacao e despacho assincromo interno |
| Outbox Pattern | Nao | Nao implementado |
| Retry | Sim | Scraping e processamento assincromo |
| DLQ | Nao | Nao implementado |
| Idempotencia | Parcial | Cache por URL; sem idempotency key/outbox |
| Testes automatizados | Sim | `96 passed, 1 skipped` |
| Observabilidade | Sim, parcial | Health, metrics e logs estruturados |
| Prometheus | Sim | `/metrics` |
| Grafana | Nao | Nao ha dashboards |
| ELK / stack de logs | Nao | Apenas logs estruturados |
| Kubernetes | Nao | Nao ha manifests |
| gRPC | Nao | REST apenas |
| Terraform | Nao | Ausente |
| Windows DX | Sim, parcial | `scripts/dev.ps1` complementa o Makefile |

## 14. Score Final do Projeto

**Nota final: 8.1 / 10**

O projeto melhorou bastante em engenharia e acabamento:

- arquitetura organizada em camadas
- auth persistida com RBAC
- CSRF habilitado
- rate limiting mais completo
- cache coerente
- migrations sem bootstrap enganoso
- lint verde
- testes e cobertura em bom nivel

A nota nao e mais alta por tres motivos:

- a stack principal ainda nao e .NET/React, que e o alvo do candidato
- nao ha AWS nem artefatos de cloud enterprise
- faltam outbox, DLQ, idempotencia forte e mensageria mais alinhada ao mercado enterprise brasileiro

Mesmo com esses gaps, o repositorio hoje se sustenta muito melhor como **projeto forte de portfolio backend**, com narrativa tecnica madura e facil de defender em entrevista.
