# Dossie Tecnico de Portfolio

**Projeto analisado:** `article_summarizer_agent`
**Candidato:** Lucas Antunes Ferreira
**Data da auditoria:** 17/03/2026

## 1. Visao Geral do Projeto

Este projeto implementa uma plataforma web para extracao, processamento e sumarizacao de artigos publicos a partir de URLs. O sistema recebe um link, executa scraping com protecoes de seguranca, processa o texto, gera um resumo por abordagem extractive (TF-IDF) ou generative (Google Gemini), persiste o historico da tarefa e disponibiliza o resultado para consulta e download.

O problema que ele resolve e o de transformar conteudo longo e disperso em saidas sintetizadas, com rastreabilidade operacional. Na pratica, nao e apenas um script de IA: o repositorio monta um fluxo completo com API, autenticacao administrativa, persistencia relacional, mensageria, cache, observabilidade e controles de seguranca.

O dominio do sistema e uma combinacao de ingestao de conteudo web, NLP, processamento assincrono e operacao de backend. Ele tambem inclui funcionalidades administrativas relevantes para ambiente produtivo, como audit trail, rotacao de segredo JWT, configuracoes persistidas em runtime e metricas Prometheus.

Ponto importante para portfolio: o backend principal e **Python/Flask**, nao .NET. Portanto, o projeto e tecnicamente forte como demonstracao de arquitetura e engenharia de software, mas tem aderencia indireta ao objetivo de carreira em **.NET**.

## 2. Arquitetura do Sistema

### Classificacao arquitetural

O sistema e, hoje, um **monolito modular** com separacao real de camadas. Nao ha microservices independentes. O que existe e um backend unico, com responsabilidades bem separadas por diretorios e contratos, e com processamento assincrono desacoplado via Celery/RabbitMQ.

### Como a arquitetura aparece no codigo real

- `presentation/`: camada de entrega HTTP. `presentation/app_factory.py` monta a aplicacao Flask e registra blueprints. `presentation/blueprints/api.py`, `auth.py` servem como API REST e autenticacao. `presentation/blueprints/web.py` e um catch-all que serve a SPA React para todas as rotas nao-API.
- `application/`: casos de uso. `application/commands.py` e `queries.py` modelam operacoes de escrita e leitura. `application/handlers/*.py` implementam fluxos como submissao de tarefa, autenticacao, atualizacao de settings e conclusao de processamento.
- `domain/`: regras centrais e contratos. `domain/entities.py` define `SummarizationTask`, `User`, `AuditLogEntry`, `OutboxEntry`, `TaskId` e a maquina de estados da tarefa. `domain/repositories.py` define interfaces para persistencia.
- `infrastructure/`: adaptadores concretos. `infrastructure/repositories.py` implementa os contratos com SQLAlchemy. `infrastructure/container.py` faz o wiring da aplicacao. `infrastructure/pipeline.py` encapsula o pipeline tecnico.
- `modules/`: componentes tecnicos reutilizaveis, como `web_scraper.py`, `text_processor.py`, `summarizer.py`, `cache.py`, `rate_limiter.py`, `secrets_manager.py`, `metrics.py`, `tracing.py` e `logging_config.py`.
- `tasks/`: integracao com Celery para execucao assincrona e relay de outbox com publicacao real via kombu.
- `frontend/`: SPA React 18/TypeScript/Vite, agora interface principal. Compilada para `static/dist/` e servida pelo Flask para todas as rotas nao-API.

### Padroes utilizados

**Clean Architecture pragmatica**
O projeto demonstra uma aplicacao coerente de Clean Architecture, mas sem dogmatismo. As dependencias principais seguem a direcao esperada: a camada HTTP chama handlers de aplicacao; a camada de aplicacao conversa com contratos do dominio; a infraestrutura implementa repositorios e adaptadores.

**DDD parcial**
Ha sinais claros de modelagem de dominio, mas nao um DDD completo. O repositorio tem:

- entidades de dominio com comportamento, nao apenas DTOs;
- eventos de dominio (`TaskSubmitted`, `TaskCompleted`, `TaskFailed`, `UserAuthenticated`, etc.);
- value object (`TaskId`);
- contratos de repositorio na camada de dominio;
- maquina de estados de tarefa com transicoes validas.

Por outro lado, nao ha bounded contexts explicitos, aggregates mais sofisticados, domain services ricos ou um mapeamento de subdominios enterprise. Portanto, a leitura correta e: **DDD aplicado de forma parcial e pragmatica**.

**CQRS leve**
O projeto separa leituras e escritas com clareza:

- comandos em `application/commands.py`;
- queries em `application/queries.py`;
- handlers distintos para processar cada tipo de operacao.

Nao e um CQRS com modelos de leitura separados, event store ou projecoes; e um **CQRS organizacional**, util para manter casos de uso limpos.

**Event Driven interno**
Existe um `EventBus` in-process em `application/event_bus.py`. A submissao de tarefa publica `TaskSubmitted`, e o container registra um handler que dispara o `AsyncTaskDispatcher`, que por sua vez tenta usar Celery; se o broker nao estiver disponivel, cai para thread local.

Isso e importante para leitura de arquitetura: o projeto tem **event-driven interno** e **fila real para background jobs**, mas **nao** e uma arquitetura distribuida orientada a eventos entre servicos independentes.

### Decisao arquitetural mais importante

A escolha dominante foi separar o problema em dois eixos:

1. **Fluxo HTTP e administracao**: autenticacao, settings, historico, downloads e metricas.
2. **Pipeline tecnico assincrono**: scraping, processamento linguistico, sumarizacao, persistencia e cache.

Essa separacao e correta para um sistema desse tipo e melhora manutenibilidade, testabilidade e capacidade de evolucao.

## 3. Stack Tecnologica

| Categoria | Tecnologias | Por que foram usadas |
|---|---|---|
| Backend | Python 3.10+, Flask, Gunicorn, Flasgger | Flask entrega rapidez de iteracao; Gunicorn prepara deploy; Flasgger documenta a API. |
| Aplicacao e arquitetura | Handlers, commands, queries, EventBus, container proprio | Estruturam os casos de uso e reduzem acoplamento entre HTTP, dominio e infraestrutura. |
| Persistencia | SQLAlchemy 2, Alembic, SQLite, PostgreSQL | SQLAlchemy implementa repositorios; Alembic versiona schema; SQLite acelera dev local; PostgreSQL aparece como banco relacional mais robusto para Compose e CI. |
| Mensageria e async | Celery, RabbitMQ, kombu | Desacoplam o processamento da request web e permitem escalar workers separadamente. Outbox relay publica eventos reais via kombu para topic exchange RabbitMQ. |
| Cache e resiliencia | Redis, filesystem fallback, rate limiter, circuit breaker, Tenacity | Melhoram desempenho, limitam abuso e aumentam resiliencia do scraping. |
| IA e NLP | Google Gemini, NLTK, scikit-learn, langdetect | Gemini cobre resumo generativo; NLTK/scikit-learn garantem fallback extractive offline e pipeline de NLP sem dependencia exclusiva de LLM. |
| Seguranca | Flask-JWT-Extended, RBAC, CSRF para cookies, CSP, audit log, secret rotation | Elevam o nivel do backend para um padrao mais proximo de ambiente real. |
| Observabilidade | Prometheus, Grafana, OpenTelemetry, Jaeger, Flower, python-json-logger | Metricas, SLO dashboard, distributed tracing com spans Flask + SQLAlchemy, logs estruturados. |
| Frontend principal | React 18, TypeScript, Vite, TanStack Query, React Router, shadcn/ui | SPA principal compilada para `static/dist/`; autenticacao JWT, polling via TanStack Query e roteamento client-side. ESLint configurado. |
| DevOps | Docker, Docker Compose, GitHub Actions, Makefile, Render scripts | Facilita execucao local, CI e deploy basico. |
| Cloud | Render e Cloud Run aparecem em docs e manifests | Ha preocupacao com deploy em nuvem, mas nao existe orientacao nativa para AWS no repositorio. |

### Leitura tecnica da stack

Para vagas de backend geral, a stack mostra maturidade. Para vagas **.NET**, o problema nao e de qualidade; e de **alinhamento**. O projeto prova conhecimento de arquitetura, mensageria, seguranca, banco e operacao, mas nao prova experiencia direta com C#, ASP.NET Core, EF Core ou ecossistema Microsoft.

## 4. Fluxo do Sistema

O fluxo principal funciona assim:

1. O cliente envia `POST /api/sumarizar` com `url`, `method` e `length`.
2. A API normaliza e valida o payload basico em `presentation/blueprints/api.py`.
3. `SubmitSummarizationHandler` cria a tarefa, persiste em banco e aplica idempotencia se o header `X-Idempotency-Key` estiver presente.
4. O handler publica `TaskSubmitted` no `EventBus`.
5. O container registra um listener que usa `AsyncTaskDispatcher` para tentar despachar a tarefa ao Celery; se Celery/RabbitMQ nao estiver disponivel, o processamento cai para thread local.
6. `ProcessTaskHandler` marca a tarefa como `processing`, atualiza progresso e chama `ArticlePipelineRunner`.
7. `ArticlePipelineRunner` executa o pipeline:
   - `WebScraper` faz SSRF check, retries, circuit breaker e limite de tamanho de resposta;
   - `TextProcessor` limpa o texto, detecta idioma, quebra em sentencas/paragrafos e calcula estatisticas;
   - `Summarizer` escolhe entre Gemini e TF-IDF extractive com fallback;
   - `FileManager` salva arquivos `txt`, `md` e `json`, alem de cachear o resultado.
8. `CompleteTaskHandler` ou `FailTaskHandler` atualiza o estado final da tarefa, persiste o resultado e publica evento de conclusao/falha.
9. O cliente (via React + TanStack Query) consulta `GET /api/tarefa/<task_id>` ate o encerramento.
10. Quando a tarefa termina, o usuario pode baixar os artefatos em `GET /api/download/<task_id>/<fmt>`.

Fluxos administrativos adicionais:

- `POST /api/auth/login`: autentica administrador e gera JWT (endpoint da API REST, nao Jinja);
- `GET/PUT /api/settings`: leitura e alteracao de configuracoes persistidas em banco e aplicadas em runtime;
- `POST /api/limpar-cache`: limpeza administrativa de cache;
- `POST /api/admin/rotate-secret`: rotacao de segredo JWT com grace period;
- `GET /metrics` e `GET /health`: observabilidade e health check.

## 5. Conceitos de Engenharia Aplicados

| Conceito | Status | Evidencia no codigo | Leitura tecnica |
|---|---|---|---|
| SOLID | Sim | handlers pequenos, contratos em `domain/repositories.py`, adaptadores em `infrastructure/`, DI em `infrastructure/container.py` | Boa separacao de responsabilidade e inversao de dependencia para um projeto autoral. |
| DDD | Parcial | entidades de dominio, eventos, value object `TaskId`, state machine de `SummarizationTask` | Demonstra pensamento de dominio, mas nao chega a um DDD enterprise completo. |
| Clean Architecture | Sim | divisao real entre `presentation`, `application`, `domain`, `infrastructure` | Bem aplicada para um monolito modular. |
| CQRS | Sim, leve | `commands.py`, `queries.py`, handlers separados | Organiza o codigo, mas nao ha read models separados. |
| Event Driven | Parcial | `EventBus` + `TaskSubmitted` + despacho assincrono | Event-driven interno ao monolito, nao distribuido. |
| Outbox Pattern | Sim | `OutboxEntry`, `SqlAlchemyOutboxRepository`, `tasks/outbox_relay.py` com kombu | Relay publica eventos reais via kombu para topic exchange RabbitMQ com routing key por tipo de evento. Dead-letter para entradas com retry_count esgotado. |
| Idempotencia | Sim | hash do header `X-Idempotency-Key`, indice unico em `tasks.idempotency_key` | Boa pratica relevante para APIs reais. |
| Retry | Sim | `autoretry_for + retry_backoff=True` no Celery task, retries HTTP com Tenacity/urllib3 | Demonstra preocupacao com resiliencia e backoff exponencial. |
| DLQ | Sim | entradas com `retry_count >= OUTBOX_MAX_RETRIES` movidas para status `failed`; `MaxRetriesExceededError` persiste dead-letter record no banco | Dead-letter fechando o ciclo: relay nao tenta republicar entradas ja exauridas. |

### Observacoes importantes

- **Nao considero este projeto um exemplo de microservices.** A classificacao correta e monolito modular com worker assincrono.
- **Outbox e DLQ agora estao plenamente implementados.** O relay publica eventos reais via kombu, com dead-letter operacional para entradas com retries esgotados.
- **A seguranca esta acima da media de projetos junior**, com JWT, RBAC, CSRF para cookies, SSRF protection, audit log, path traversal guard e rotacao de segredo.

## 6. Relevancia Para o Mercado Brasileiro

### O projeto demonstra skills demandadas?

**Sim, em boa parte.** O repositorio mostra varias capacidades que vagas backend e fullstack pedem no Brasil em 2025-2026:

- API REST estruturada;
- persistencia relacional com migrations;
- mensageria real com RabbitMQ + outbox pattern;
- Redis para cache/rate limiting;
- autenticacao e autorizacao;
- Docker e CI com GitHub Actions;
- observabilidade com Prometheus/Grafana/OpenTelemetry/Jaeger;
- testes automatizados;
- organizacao arquitetural acima do nivel CRUD simples;
- React/TypeScript como SPA primaria consistente.

### Ele parece um projeto enterprise?

**Ele passa uma imagem enterprise-like em suas principais implementacoes.** O repositorio demonstra:

- camadas explicitas;
- mensageria assincrona com outbox pattern real;
- RBAC e audit trail;
- configuracao em runtime;
- metricas, SLO dashboard e distributed tracing;
- persistencia versionada;
- preocupacao com idempotencia e resiliencia.

Os gaps restantes estao principalmente na ausencia de stack .NET e AWS, e em documentacao que ainda pode ser melhorada.

### Ele e relevante para vagas Junior?

**Sim, como diferencial tecnico.** Para vaga Junior/Estagio, ele esta acima da media de portfolio porque mostra mais do que CRUD. Porem, para **Junior .NET**, ele perde forca por nao demonstrar C#, ASP.NET Core, EF Core e ecossistema Microsoft.

Minha leitura de mercado e a seguinte:

- como projeto de engenharia backend, ele e forte;
- como projeto para provar stack **.NET**, ele e insuficiente sozinho;
- como projeto para mostrar maturidade arquitetural, ele ajuda bastante;
- como projeto flagship para vaga **Fullstack .NET + React**, ele ainda precisa de uma versao em ASP.NET Core ou de um projeto complementar nessa stack.

## 7. Como Explicar o Projeto em Entrevista

### Explicacao simples (30 segundos)

"Desenvolvi uma plataforma que recebe URLs de artigos, extrai o conteudo, gera resumos de forma assincrona e armazena o historico das tarefas. O projeto tem autenticacao JWT, banco relacional, mensageria com RabbitMQ e outbox pattern real, cache com Redis, observabilidade com Prometheus e OpenTelemetry, frontend React como SPA principal e testes automatizados."

### Explicacao tecnica (2 minutos)

"Esse projeto e um monolito modular em Flask organizado em `presentation`, `application`, `domain` e `infrastructure`, com um pipeline tecnico separado em `modules/`. A API recebe a URL, cria uma `SummarizationTask`, persiste no banco via SQLAlchemy e publica um evento interno `TaskSubmitted`. O dispatcher tenta usar Celery com RabbitMQ como broker e, se o broker nao estiver disponivel, faz fallback para thread local. O worker executa scraping com protecao SSRF, retries, circuit breaker e limite de tamanho, depois processa o texto com NLTK/langdetect, resume com TF-IDF ou Gemini e salva artefatos em `txt`, `md` e `json`. O sistema tem Outbox Pattern com relay real via kombu publicando para topic exchange RabbitMQ — entradas com retry esgotado vao para dead-letter. O frontend e uma SPA React/TypeScript com TanStack Query para polling. A observabilidade inclui Prometheus, Grafana com SLO dashboard e tracing distribuido via OpenTelemetry com Jaeger. Ha JWT com RBAC, audit log, rate limiting, CSP, rotacao de segredo e migrations com Alembic."

## 8. Pontos Fortes do Projeto

- Estrutura de pastas madura e coerente para um projeto autoral, com separacao clara de camadas.
- Backend com qualidade acima da media de portfolio junior, incluindo autenticacao JWT, RBAC, audit trail, idempotencia e rotacao de segredo.
- Uso real de mensageria e processamento assincrono com Celery + RabbitMQ, em vez de apenas jobs sincronos.
- Persistencia relacional com SQLAlchemy 2, Alembic e schema versionado.
- Preocupacao real com seguranca: SSRF protection, rate limiting, CSP, CSRF em cookies e validacao de path de download.
- Observabilidade acima do normal para portfolio: metricas Prometheus, SLO dashboard Grafana, Flower e logs estruturados.
- Boa base de testes. Suite executou com **113+ testes aprovados, cobertura > 76%**, com `ruff check .` em verde.
- Suporte a fallback tecnico: Redis opcional, Celery opcional, Gemini com fallback extractive e SQLite para desenvolvimento rapido.
- **Frontend React/TypeScript como SPA primaria** com autenticacao JWT, polling via TanStack Query e roteamento client-side via React Router. ESLint configurado.
- **Outbox relay publicando eventos reais** via kombu para exchange RabbitMQ (topic exchange com routing key por tipo de evento). Dead-letter para entradas com retry_count esgotado.
- **Distributed tracing via OpenTelemetry** com Jaeger, cobrindo Flask + SQLAlchemy. OTEL_ENABLED flag para ligar/desligar sem rebuild.

## 9. Pontos a Melhorar

- O principal desalinhamento para o objetivo de carreira e o stack: o backend e Python/Flask, nao C#/.NET.
- A estrategia de cloud do repositorio esta mais proxima de Render/Cloud Run do que de AWS, o que reduz aderencia ao foco de carreira definido.
- A documentacao ainda tem algum drift entre o que esta descrito e o estado real do codigo — melhoria continua necessaria.
- Os testes sao fortes no backend, mas ainda faltam testes fim a fim com PostgreSQL/RabbitMQ em ambiente local padronizado.

## 10. Melhorias Prioritarias Para Portfolio

1. **Portar o backend para ASP.NET Core + EF Core, preservando a mesma arquitetura.**
   Essa e a melhoria de maior impacto para empregabilidade. O projeto ja tem historia tecnica boa; falta provar C#, ASP.NET Core, EF Core e convencoes do mercado .NET. *(pendente)*

2. ~~**Consolidar a camada frontend em React.**~~ **Concluido.** React e agora a SPA principal com ESLint configurado e integracao completa com a API.

3. ~~**Completar a mensageria enterprise.**~~ **Concluido.** Relay publica eventos reais, Celery Beat nos manifests de deploy, retry com backoff exponencial e dead-letter operacional.

4. **Adicionar infraestrutura AWS-first e IaC.**
   Para o foco de carreira informado, a evolucao natural seria ECS/Fargate, RDS, ElastiCache, Amazon MQ ou SQS e Terraform/CDK. *(pendente)*

5. ~~**Fortalecer testes de integracao.**~~ **Parcialmente concluido.** Testes de alinhamento React-API e testes de outbox/messaging adicionados; E2E com browser ainda faltam.

6. ~~**Adicionar observabilidade proxima de producao.**~~ **Concluido.** OpenTelemetry, Jaeger, SLO dashboard Grafana.

## 11. Como Colocar no Curriculo

Sistema web de sumarizacao de artigos publicos com arquitetura em camadas (Clean Architecture + CQRS), processamento assincrono via Celery/RabbitMQ com Outbox Pattern real, persistencia relacional com SQLAlchemy/PostgreSQL, autenticacao JWT com RBAC, cache Redis, observabilidade com Prometheus/Grafana/OpenTelemetry e frontend React/TypeScript como SPA principal.

## 12. Nivel do Projeto

**Classificacao: Pleno.**

Motivo:

- esta acima de um projeto Junior tipico porque inclui mensageria, seguranca, persistencia versionada, CI, observabilidade e testes automatizados;
- demonstra pensamento arquitetural e preocupacao com resiliencia, nao apenas CRUD;
- o outbox pattern e DLQ agora fecham um ciclo enterprise real;
- a SPA React e a UI primaria consistente;
- para vagas especificamente **.NET**, o impacto percebido cai porque o stack principal nao e o stack alvo.

## 13. Checklist de Mercado

| Requisito de mercado | Presente no projeto | Observacao |
|---|---|---|
| C# | Nao | Principal gap para vagas .NET. |
| .NET / ASP.NET Core | Nao | Arquitetura e transferivel, stack nao. |
| EF Core | Nao | Persistencia atual usa SQLAlchemy. |
| APIs REST | Sim | API organizada com autenticacao, admin e downloads. |
| PostgreSQL | Sim | Presente em Compose, CI e `.env.example`; local default continua SQLite. |
| SQL Server | Nao | Nao ha suporte explicito no repositorio. |
| React | Sim | SPA primaria com React 18/TypeScript/Vite, ESLint configurado, integracao API completa. |
| Angular | Nao | Nao utilizado. |
| Docker | Sim | `Dockerfile` e `docker-compose.yml` completos. |
| CI | Sim | GitHub Actions com lint, testes e build de imagem. |
| CD | Parcial | Ha manifests/scripts de deploy, mas nao pipeline automatizada de release enterprise. |
| RabbitMQ | Sim | Broker real configurado para Celery + outbox relay com kombu. |
| Kafka | Nao | Nao utilizado. |
| Redis | Sim | Cache, rate limiting e apoio a segredos. |
| JWT / Auth | Sim | Login, refresh, RBAC e cookies JWT. |
| Clean Architecture | Sim | Aplicacao bem separada em camadas. |
| DDD | Parcial | Ha elementos de dominio, nao um DDD completo. |
| CQRS | Sim | Leve, via commands/queries/handlers. |
| Event Driven | Parcial | Interno ao monolito; nao distribuido entre servicos. |
| Outbox Pattern | Sim | Relay publica eventos reais via kombu para topic exchange RabbitMQ. |
| Idempotencia | Sim | Header dedicado + indice unico em banco. |
| Retry / DLQ | Sim | Retry com backoff exponencial; DLQ para entradas com retry_count esgotado. |
| Observabilidade | Sim | Prometheus + Grafana (SLO dashboard) + OpenTelemetry + Jaeger + logs estruturados. |
| Testes automatizados | Sim | Backend bem coberto; E2E com browser ainda faltam. |
| NoSQL / MongoDB | Nao | Nao ha uso de banco NoSQL. |
| AWS | Nao | Nao ha deploy nem servicos AWS no repositorio. |
| Azure | Nao | Nao ha integracao com Azure. |
| Kubernetes | Nao | Nao ha manifests Helm/K8s. |
| Terraform / CDK | Nao | Sem IaC. |
| gRPC | Nao | Apenas HTTP/REST. |
| TDD | Parcial | Ha testes fortes, mas o repositorio nao prova processo TDD. |

## 14. Score Final do Projeto

**Nota final: 7.8 / 10**

### Leitura da nota

- **Engenharia:** 8.5/10
  O projeto e forte em modularizacao, seguranca, persistencia, async, observabilidade e testes. Outbox real, distributed tracing e React como SPA primaria elevam a nota.

- **Arquitetura:** 8.0/10
  A base e boa e passa maturidade. Outbox Pattern e DLQ agora fecham ciclos enterprise completos. Mensageria com Celery Beat nos manifests de deploy.

- **Relevancia para vagas .NET no Brasil:** 5.5/10
  O maior desconto da nota vem do desalinhamento de stack. React agora e consistente, mas o stack principal ainda e Python/Flask. Para backend geral o projeto vale mais; para **.NET**, ele nao e prova direta de experiencia no stack que mais aparece nas vagas.

### Conclusao objetiva

Como projeto de engenharia, este repositorio e forte e acima da media. Como projeto de portfolio para um candidato Junior/Estagio, ele e um diferencial tecnico real. O frontend React e agora a UI primaria, o outbox pattern fecha o ciclo com publicacao real, e a observabilidade cobre metricas, SLOs e tracing distribuido. Como **projeto principal para vagas .NET**, entretanto, ele ainda nao e suficiente sozinho. A melhor estrategia e usar este repositorio como vitrine de arquitetura e engenharia, e em seguida replicar ou portar a mesma solucao para **ASP.NET Core + EF Core + React + AWS**, transformando um bom projeto em um portfolio altamente aderente ao mercado alvo.
