# Descricao Portfolio

## 1. Visao Geral do Projeto

O `article_summarizer_agent` e uma plataforma web para extracao, processamento e sumarizacao de artigos publicos. O sistema recebe uma URL, executa scraping com protecoes de seguranca, processa o texto, gera um resumo por abordagem extractive ou via Gemini, persiste o historico e disponibiliza consulta assincrona por `task_id`, download de artefatos e um painel administrativo.

O problema que ele resolve e duplo:

- automatizar a leitura e condensacao de conteudo longo;
- transformar um processo potencialmente lento em um fluxo assincrono, observavel e administravel.

O dominio principal nao e financeiro nem core enterprise classico. Trata-se de um dominio de automacao de conteudo e NLP. O que aproxima o projeto do universo enterprise nao e o negocio em si, mas a forma como a engenharia foi estruturada: camadas, persistencia, auth, controles de seguranca, fila assincrona, cache, migrations e suite automatizada.

Estado validado (v3.1 — 2026-03-13):

- `pytest tests --cov --cov-report=term-missing`: testes passando (inclui 17 novos testes de entidades de dominio);
- `ruff check .`: verde.

## 2. Arquitetura do Sistema

### Classificacao arquitetural

O sistema e um **monolito modular**, nao uma arquitetura de microservices. A organizacao do repositorio segue uma **Clean Architecture pragmatica**, com influencias de **DDD tatico leve**, **CQRS leve** e um **event-driven interno**.

### Como isso aparece no codigo real

- `presentation/` concentra a borda HTTP e HTML com Flask Blueprints.
- `application/` contem comandos, queries e handlers que modelam casos de uso.
- `domain/` contem entidades, eventos e contratos de repositorio.
- `infrastructure/` implementa persistencia SQLAlchemy, auth, container de dependencias, runtime settings e o runner da pipeline.
- `modules/` concentra servicos tecnicos legados e transversais, como scraper, processador de texto, summarizer, cache, rate limiter, secrets manager e circuit breaker.
- `tasks/` integra a execucao assincrona com Celery.

### Por que a arquitetura faz sentido aqui

Essa escolha foi adequada porque o sistema mistura:

- interface web e API REST;
- processamento assincrono de tarefas;
- integracoes externas;
- persistencia de estado;
- operacoes administrativas.

Separar por camadas reduz acoplamento entre HTTP, casos de uso, dominio e detalhes tecnicos. Isso facilita trocar a borda, evoluir a pipeline e isolar testes.

### Onde a arquitetura e forte

- `presentation/app_factory.py` mostra bootstrap limpo da aplicacao, middlewares, JWT, CSP, Swagger e registro de blueprints.
- `infrastructure/container.py` faz a composicao das dependencias, handlers, repositorios, rate limiters e dispatcher assincrono.
- `application/handlers/task_handlers.py` separa submissao, processamento, consulta, estatisticas e download por caso de uso.
- `domain/entities.py`, `domain/events.py` e `domain/repositories.py` mostram uma tentativa real de separar modelo de dominio, contratos e eventos.

### Onde a arquitetura ainda e parcial

- O `domain/` e **anemico**: as entidades possuem pouca regra de negocio e a maior parte da orquestracao esta nas camadas `application` e `infrastructure`.
- O diretorio `modules/` concentra boa parte da logica tecnica central. Na pratica, ele funciona como uma camada de servicos compartilhados fora da disciplina estrita de portas/adapters.
- O `EventBus` em `application/event_bus.py` e **sincrono e in-process**. Isso caracteriza event-driven interno, nao integracao assincrona entre servicos.

### Diagnostico arquitetural

Arquiteturalmente, o repositorio esta acima da media de projetos de portfolio. Ele nao e um microservice enterprise completo, mas tambem nao e um CRUD simples. A melhor definicao e: **monolito modular com preocupacoes enterprise reais**.

## 3. Stack Tecnologica

### Backend

- **Python 3.10+ / 3.12 / 3.13**: base da aplicacao. O projeto roda localmente em Python 3.13, usa imagem Docker 3.12 e declara compatibilidade ampla no `pyproject.toml`.
- **Flask**: camada HTTP leve para API e paginas server-side.
- **Flask-JWT-Extended**: autenticacao JWT por header e cookies.
- **Flasgger**: Swagger UI em `/apidocs/`.

### Processamento e IA

- **requests + BeautifulSoup4**: scraping HTTP e parsing HTML.
- **NLTK + langdetect**: limpeza, tokenizacao, stopwords e deteccao de idioma.
- **scikit-learn + numpy**: sumarizacao extractive via TF-IDF e cosine similarity.
- **google-genai**: integracao opcional com Gemini para resumo generativo.
- **tenacity + urllib3 Retry**: retries exponenciais no scraping.

### Banco de dados

- **SQLAlchemy 2**: ORM e repositorios.
- **Alembic**: versionamento de schema e migrations.
- **SQLite**: fallback e ambiente local simples.
- **PostgreSQL**: banco alvo para execucao mais seria, exposto no `docker-compose.yml`.

### Infraestrutura e assincronia

- **Celery**: execucao de tarefas assincronas.
- **RabbitMQ**: broker AMQP enterprise-grade (v3.1, substituiu Redis como broker).
- **Redis**: cache distribuido, rate limiting distribuido e backend de resultados Celery.
- **Gunicorn**: servico WSGI para runtime produtivo.
- **Docker / Docker Compose**: empacotamento e ambiente com API, worker, Postgres, Redis, RabbitMQ, Flower, Prometheus e Grafana.
- **Flower**: painel operacional do Celery.

### Frontend

- **Jinja2**: renderizacao server-side (templates Python).
- **React 18 + TypeScript** (v3.1): SPA com React Query, React Router e Tailwind CSS.
- **Bootstrap 5**: base visual para templates Jinja2.
- **JavaScript vanilla**: interacoes nos templates server-side.

### Observabilidade e operacao

- **prometheus_client**: endpoint `/metrics` (protegido por `METRICS_TOKEN`).
- **Grafana**: dashboard provisionado com 5 paineis (request rate, task rate, active tasks, p50/p95 duration, error rate).
- **Correlation ID**: `X-Request-ID` injetado em cada request e propagado em logs e response headers.
- **python-json-logger**: logs estruturados com `request_id` via `RequestIdFilter`.
- **Health check** em `/health`.
- **Locust** em `tests/load/locustfile.py` para carga basica.

### DevOps

- **GitHub Actions**: pipeline de lint, testes e build Docker.
- **Render**: manifesto simples de deploy cloud.
- **Makefile** e `scripts/dev.ps1`: ergonomia de desenvolvimento Linux/macOS/Windows.

### Por que cada grupo de tecnologia foi usado

- Flask, Jinja e JS vanilla simplificam a entrega do produto sem depender de SPA.
- SQLAlchemy e Alembic trazem persistencia versionada e padrao de mercado.
- Redis e Celery elevam o projeto de "request-response sincrono" para "pipeline assincrono de verdade".
- scikit-learn e NLTK permitem um modo offline, o que e uma decisao tecnica boa para fallback e custo.
- Docker, CI e health endpoints mostram preocupacao operacional alem do codigo.

## 4. Fluxo do Sistema

1. O usuario envia `POST /api/sumarizar` com URL, metodo e tamanho do resumo.
2. A API normaliza a URL, valida parametros, aplica rate limiting e registra uma tarefa em banco.
3. O caso de uso publica um evento `TaskSubmitted`.
4. O dispatcher em `infrastructure/container.py` tenta usar Celery; se nao houver worker disponivel, faz fallback para thread local.
5. A pipeline (`infrastructure/pipeline.py`) executa scraping, processamento de texto, sumarizacao e salvamento de artefatos.
6. O resultado e persistido na tabela `tasks`, com arquivos em `outputs/` e cache no backend configurado.
7. O cliente consulta `GET /api/tarefa/<task_id>` ate a conclusao.
8. O usuario pode baixar `txt`, `md` ou `json`, enquanto endpoints administrativos permitem login, leitura/alteracao de settings, limpeza de cache e rotacao de segredo JWT.

Fluxos secundarios relevantes:

- autenticacao administrativa via `POST /api/auth/login`;
- leitura de historico paginado em `/historico`;
- alteracao de configuracoes de runtime sem restart;
- rotacao de segredo JWT com grace period;
- observabilidade via `/health` e `/metrics`.

## 5. Conceitos de Engenharia Aplicados

### SOLID

**Parcialmente presente.**

- Ha boa separacao de responsabilidade entre blueprints, handlers, repositorios e servicos tecnicos.
- O container centraliza composicao e reduz acoplamento direto.
- Existem contratos (`domain/repositories.py`, `application/ports.py`) que ajudam a inverter dependencias.

Limite:

- a camada `modules/` ainda concentra muitas responsabilidades tecnicas;
- o dominio nao e rico o suficiente para demonstrar SOLID de forma profunda em regras de negocio.

### DDD

**Parcial e leve.**

- Existem entidades (`SummarizationTask`, `User`, `AuditLogEntry`, `SettingsEntry`), eventos de dominio e repositorios.
- O sistema sugere contextos claros: processamento de tarefa, identidade/admin e configuracao operacional.

Limite:

- nao ha aggregates mais sofisticados;
- nao ha bounded contexts formalizados;
- a modelagem de dominio e simples e utilitaria.

### Clean Architecture

**Sim, de forma pragmatica.**

- A separacao de `presentation`, `application`, `domain` e `infrastructure` e real.
- A API fala com handlers, os handlers usam contratos e a persistencia fica na infraestrutura.

Limite:

- `modules/` funciona como um bloco tecnico legado que contorna um isolamento mais estrito.

### CQRS

**Sim, em versao leve.**

- `application/commands.py` e `application/queries.py` separam escrita e leitura.
- `application/handlers/task_handlers.py` e `admin_handlers.py` refletem essa divisao.

Nao ha:

- bus dedicado de comandos;
- projections separadas;
- consistencia eventual sofisticada entre modelos.

### Event Driven

**Sim, internamente.**

- O sistema publica `TaskSubmitted`, `TaskCompleted`, `TaskFailed`, `UserAuthenticated`, `CacheCleared` e `JwtSecretRotated`.
- O dispatcher assincrono e acionado a partir do evento de submissao.

Limite:

- o bus e em memoria e sincrono;
- nao existe broker de eventos entre servicos;
- nao ha versionamento de eventos nem contratos externos.

### Outbox Pattern

**Implementado (v3.1).**

- `OutboxEntry` persistida atomicamente na submissao de tarefa.
- `tasks/outbox_relay.py` — task Celery beat que varre entradas pendentes a cada 30 segundos e as publica.
- `SqlAlchemyOutboxRepository` com `SELECT FOR UPDATE SKIP LOCKED` para processamento seguro em workers concorrentes.

### Idempotencia

**Implementado (v3.1).**

- Header `X-Idempotency-Key` aceito em `POST /api/sumarizar`.
- Chave e armazenada como SHA-256 (64 chars) na coluna `tasks.idempotency_key` (unique, indexed).
- Requisicoes duplicadas retornam a tarefa existente sem criar nova, exceto se a tarefa anterior falhou.

### Retry / DLQ

**Retry existe; DLQ implementado (v3.1).**

- O scraping usa retry com `tenacity` e `urllib3`.
- A task Celery tem `max_retries=3` com `task_reject_on_worker_lost=True`.
- `DeadLetterEntry` ORM model e migration 0003 para rastreamento de falhas persistentes.

## 6. Relevancia Para o Mercado Brasileiro

### O projeto demonstra skills demandadas?

**Sim, em engenharia backend e arquitetura.**

Ele demonstra varias competencias muito valorizadas em vagas reais:

- API REST;
- persistencia relacional;
- migrations;
- auth com JWT;
- rate limiting;
- cache;
- processamento assincrono;
- Docker;
- CI;
- testes automatizados;
- separacao em camadas;
- preocupacao com seguranca.

### Ele parece um projeto enterprise?

**Parcialmente.**

O projeto tem cara de backend com ambicao enterprise, principalmente por:

- arquitetura modular;
- configuracao por ambiente;
- audit log;
- task processing assincrono;
- runtime settings;
- hardening de API.

Mas ele ainda nao fecha o pacote de "enterprise-like completo" porque faltam:

- stack alvo do mercado .NET;
- broker de mensageria mais tipico de enterprise brasileiro;
- outbox, idempotencia e DLQ;
- observabilidade realmente instrumentada;
- cloud/IaC mais maduros;
- consistencia documental total.

### Ele e relevante para vagas Junior?

**Sim, como diferencial forte.**

Para Junior backend, o projeto e acima da media. Ele mostra repertorio de arquitetura e operacao que normalmente nao aparece em repositorios de iniciantes.

### Onde ele perde aderencia para o objetivo do candidato

O maior problema de mercado nao e tecnico, e de **alinhamento de stack**:

- o projeto nao usa **C#**;
- nao usa **.NET / ASP.NET Core**;
- nao usa **EF Core**;
- nao usa **React**;
- nao usa **AWS** como plataforma alvo;
- nao usa **RabbitMQ, Kafka ou SQS**.

Conclusao de mercado:

Este e um **bom projeto de engenharia de software**, mas **nao e o melhor projeto ancora para vender um perfil Fullstack .NET ou Backend .NET sozinho**. Ele funciona melhor como:

- prova de maturidade tecnica geral;
- prova de arquitetura e preocupacoes de producao;
- complemento forte a um projeto adicional em ASP.NET Core + React.

## 7. Como Explicar o Projeto em Entrevista

### Explicacao simples (30 segundos)

Criei uma plataforma que recebe links de artigos publicos, extrai o conteudo, gera resumos e processa isso de forma assincrona. O foco nao foi so fazer a funcionalidade, mas montar um backend mais proximo de producao, com persistencia, autenticacao JWT, rate limiting, cache, Docker, testes e uma arquitetura em camadas.

### Explicacao tecnica (2 minutos)

O projeto e um monolito modular em Flask organizado em `presentation`, `application`, `domain` e `infrastructure`, com uma camada tecnica em `modules/` para scraper, NLP, cache e seguranca. A submissao cria uma tarefa persistida em banco, publica um evento interno `TaskSubmitted` e um dispatcher envia o processamento para Celery com Redis, ou faz fallback para thread local. A pipeline executa scraping com protecao SSRF, retry e circuit breaker, processa o texto com NLTK/langdetect, resume por TF-IDF ou Gemini e persiste resultado, estatisticas e artefatos. A parte administrativa usa JWT, RBAC, audit log, runtime settings, limpeza de cache e rotacao de segredo com grace period. Em termos de maturidade, ele tem testes automatizados, migrations com Alembic, Docker Compose com API, worker, Postgres, Redis e Flower, alem de health check e endpoint de metricas. O ponto que eu mesmo destacaria como melhoria e que o event bus ainda e interno, nao ha outbox/idempotencia/DLQ, e para o meu alvo de carreira eu replicaria essa mesma arquitetura em ASP.NET Core + EF Core + React.

## 8. Pontos Fortes do Projeto

- Arquitetura em camadas real, nao apenas nominal.
- Monolito modular bem organizado para um projeto de portfolio.
- Pipeline assincrona com Celery e fallback controlado.
- Persistencia de tarefas, usuarios, audit log e settings com SQLAlchemy + Alembic.
- JWT com RBAC, cookies, CSRF e rotacao de segredo.
- Rate limiting por perfil de rota.
- Protecao SSRF, circuit breaker e retry na camada de scraping.
- Cache distribuivel com Redis e fallback em filesystem.
- Runtime settings sem restart.
- Suite automatizada forte para o tamanho do projeto.
- Docker Compose relativamente completo para ambiente local.
- CI com lint, testes e build da imagem.

## 9. Pontos a Melhorar

- **Aderencia ao alvo de carreira**: o projeto e Python/Flask, nao .NET/React/AWS.
- **DDD ainda superficial**: dominio simples, mais tecnico do que orientado a negocio.
- **Mensageria enterprise ausente**: Celery + Redis resolvem fila, mas nao substituem RabbitMQ, Kafka ou SQS em sinal de mercado.
- **Outbox, idempotencia e DLQ inexistentes**: falta maturidade de integracao distribuida.
- **Observabilidade parcial**: existe `/metrics`, mas os objetos Prometheus sao declarados e nao aparecem efetivamente instrumentados no fluxo de request/task.
- **Cobertura inflada em relacao ao nucleo I/O**: `pyproject.toml` exclui `modules/web_scraper.py`, `modules/file_manager.py`, `modules/gemini_summarizer.py` e `modules/selenium_scraper.py` da meta de coverage.
- **Teste de PostgreSQL ainda opcional**: existe `tests/test_db_integration.py`, mas no ambiente auditado ele foi skipado por falta de `pytest-postgresql`.
- **Documentacao com drift**: `README.md` esta alinhado, mas `SECURITY.md`, `docs/ARCHITECTURE.md` e `docs/AUDIT_REPORT.md` ainda carregam estados antigos do projeto e reduzem credibilidade.
- **Infra cloud incompleta**: o `docker-compose.yml` representa uma topologia mais madura do que o `render.yaml`, que sobe apenas um web service.
- **Migrations no startup**: `database.upgrade_schema()` e o `render-start.sh` sugerem upgrade no boot; isso e conveniente, mas nao e o padrao mais seguro para ambientes multi-worker/multi-instancia.
- **Hardening adicional de seguranca**: `/api/status` e `/metrics` sao publicos; a validacao de caminho de download usa comparacao por prefixo de string e merece endurecimento.

## 10. Melhorias Prioritarias Para Portfolio

1. **Adicionar uma versao ASP.NET Core + EF Core do core transacional**
   Isso converte imediatamente a maturidade arquitetural atual em aderencia ao mercado .NET brasileiro.

2. **Criar um frontend React/TypeScript**
   O projeto hoje e server-side com Jinja2. Para vagas Fullstack .NET + React, falta a prova concreta da stack de UI mais pedida.

3. **Substituir o event bus interno por integracao com RabbitMQ ou AWS SQS**
   Isso aumenta muito a leitura de "projeto enterprise" e aproxima o portfolio das vagas que pedem mensageria real.

4. **Implementar outbox, idempotencia e DLQ**
   Esses itens tem alto valor em entrevistas tecnicas porque mostram maturidade em consistencia e resiliencia operacional.

5. **Instrumentar observabilidade de verdade**
   Adicionar metricas efetivamente incrementadas, correlation ID, tracing e dashboard Prometheus/Grafana tornaria o discurso de producao mais convincente.

6. **Levar o deploy para AWS**
   ECS/Fargate ou App Runner + RDS + ElastiCache + SQS dariam alinhamento direto com o foco de cloud do candidato.

7. **Fortalecer o pipeline de testes**
   Rodar integracao real com Postgres, Redis e Celery em CI aumenta muito a confiabilidade percebida pelo recrutador tecnico.

8. **Sanear a documentacao**
   Alinhar `SECURITY.md`, `docs/ARCHITECTURE.md` e `docs/AUDIT_REPORT.md` ao estado atual melhora a imagem profissional do repositorio.

## 11. Como Colocar no Curriculo

Plataforma backend para extracao e sumarizacao assincrona de artigos publicos, desenvolvida em Python/Flask com SQLAlchemy, Alembic, Redis/Celery, JWT e arquitetura em camadas inspirada em Clean Architecture, CQRS e event-driven interno. Inclui persistencia relacional, controles de seguranca, testes automatizados, Docker e pipeline de CI.

## 12. Nivel do Projeto

**Classificacao: Junior+**

Motivo:

- esta acima de um projeto Junior comum em arquitetura, seguranca, testes e operacao;
- demonstra repertorio tecnico que flerta com Pleno em backend;
- ainda nao chega a Pleno consolidado porque faltam stack alvo (.NET/React), mensageria enterprise, outbox/idempotencia/DLQ, observabilidade madura e cloud mais forte.

Se o criterio for apenas engenharia backend em Python, ele se aproxima de um inicio de nivel Pleno. Se o criterio for aderencia ao objetivo profissional do candidato, a classificacao correta continua sendo **Junior+**.

## 13. Checklist de Mercado

| Requisito Mercado | Presente no Projeto | Observacao |
|---|---|---|
| C# | Nao | Stack principal e Python |
| .NET / ASP.NET Core | Nao | Maior gap para o objetivo do candidato |
| EF Core | Nao | ORM usado e SQLAlchemy |
| API REST | Sim | Blueprints Flask com rotas HTTP claras |
| PostgreSQL | Sim | Banco alvo no `docker-compose.yml` e `.env.example` |
| SQL Server | Nao | Nao ha suporte no repositorio |
| React / Angular | Sim (v3.1) | Frontend React 18 + TypeScript + Tailwind em `frontend/` |
| Docker | Sim | `Dockerfile` e `docker-compose.yml` presentes |
| CI/CD | Parcial | Ha CI em GitHub Actions; nao ha CD real |
| Redis | Sim | Cache, rate limiting, secrets e broker Celery |
| Celery / fila assincrona | Sim | Processamento assincrono real |
| RabbitMQ / Kafka / SQS | Sim (v3.1) | RabbitMQ AMQP como broker Celery em `celery_app.py` e `docker-compose.yml` |
| Clean Architecture | Parcial | Estrutura boa, mas com `modules/` concentrando servicos tecnicos |
| DDD | Parcial | Entidades, eventos e repositorios, porem dominio simples |
| CQRS | Sim | Commands, queries e handlers separados |
| Event Driven | Parcial | Eventos internos; nao ha integracao externa via eventos |
| Outbox Pattern | Sim (v3.1) | `OutboxEntry`, `SqlAlchemyOutboxRepository`, `tasks/outbox_relay.py` |
| Idempotencia | Sim (v3.1) | `X-Idempotency-Key` header + SHA-256 em `tasks.idempotency_key` |
| Retry | Sim | Tenacity no scraper e retry no Celery |
| DLQ | Sim (v3.1) | `DeadLetterEntry` ORM model + migration 0003 |
| Seguranca de API | Sim | JWT, RBAC, CSRF, SSRF, CSP, rate limiting |
| Testes automatizados | Sim | Suite forte com unitarios e integracoes selecionadas |
| TDD | Nao identificado | O repositorio nao prova workflow TDD |
| Observabilidade | Sim (v3.1) | Prometheus instrumentado, Grafana provisionado, correlation ID, logs estruturados |
| Prometheus / Grafana | Sim (v3.1) | Stack completo em `docker-compose.yml` + dashboard JSON provisionado |
| ELK / Application Insights | Nao | Nao ha stack dedicada |
| AWS | Nao | Nenhum provisionamento AWS no codigo |
| Terraform | Nao | Nao ha IaC |
| Kubernetes | Nao | Nao ha manifests ou helm |
| gRPC | Nao | Nao utilizado |
| NoSQL | Nao | Somente relacional + Redis como infraestrutura |

## 14. Score Final do Projeto

**Nota final: 7.8 / 10** (v3.1 — atualizado 2026-03-13)

### Justificativa da nota

**O que puxa a nota para cima:**

- arquitetura mais madura do que a media de projetos de portfolio;
- preocupacao real com seguranca, operacao e testes;
- assincronia, persistencia, cache, auth, migrations, CI e Docker;
- boa leitura de engenharia backend.

**O que puxa a nota para baixo:**

- forte desalinhamento com o objetivo principal de vagas `.NET + React + AWS`;
- event-driven apenas interno, sem broker de integracao enterprise;
- ausencia de outbox, idempotencia, DLQ e observabilidade completa;
- inconsistencias de documentacao e cobertura parcialmente otimista;
- dominio funcional pouco enterprise, apesar da engenharia boa.

### Veredito final

Como projeto de engenharia, o repositorio e forte e diferenciador para um candidato Junior. Como projeto ancora para vender um perfil **Software Engineer / Fullstack .NET / Backend .NET**, ele ainda precisa de uma ponte clara para o ecossistema Microsoft e para AWS. Em outras palavras: **e um excelente argumento de maturidade tecnica geral, mas ainda nao e a melhor prova de aderencia de stack para o objetivo profissional declarado**.
