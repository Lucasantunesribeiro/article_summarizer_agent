# Onde Publicar o Projeto Gratuitamente (Guia de Portfolio)

Comparativo das melhores opções de hospedagem **gratuita ou quase gratuita** para este projeto Flask + Python, ordenadas por adequação para portfolio.

---

## Resumo Rápido

| Plataforma | Custo real | Cold start | Disco persistente | Domínio customizado | Nota portfolio |
|---|---|---|---|---|---|
| **Render** | $0 | ~50 s | Não (free) | Sim (free) | ⭐⭐⭐⭐ |
| **Railway** | ~$0–5/mês | Não | Sim | Sim | ⭐⭐⭐⭐⭐ |
| **Fly.io** | $0 (dentro do free) | Não | Sim (3 GB) | Sim | ⭐⭐⭐⭐ |
| **Koyeb** | $0 (free tier) | Não | Não | Sim | ⭐⭐⭐ |
| **Google Cloud Run** | $0 (2 M req/mês) | ~2–5 s | Não | Sim | ⭐⭐⭐⭐ |
| **Heroku** | $5/mês (Eco) | Não | Não | Sim | ⭐⭐⭐ |
| **PythonAnywhere** | $0 (limitado) | Não | Sim | Não (free) | ⭐⭐ |

---

## 1. Render — Melhor Opção Gratuita para Começar

**Site:** [render.com](https://render.com)

### O que é gratuito
- 1 Web Service sempre ativo (com limitações)
- 750 horas/mês de execução (suficiente para 1 serviço rodando 24/7)
- HTTPS automático
- Domínio `seuapp.onrender.com`
- Deploy automático a cada `git push`

### Limitação principal
O serviço **dorme após 15 minutos sem tráfego** e leva ~50 segundos para acordar na primeira requisição. Para um recrutador abrindo o link, isso pode parecer que o site está fora do ar.

**Solução:** Use um serviço de ping gratuito (ex: [cron-job.org](https://cron-job.org)) para fazer um `GET /health` a cada 10 minutos e manter o app acordado.

### Como publicar

```bash
# 1. Suba o código para o GitHub (já feito)

# 2. Acesse render.com → New → Web Service
# 3. Conecte o repositório GitHub
# 4. Configure:
#    Runtime: Python 3
#    Build Command: pip install -r requirements.txt
#    Start Command: gunicorn --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 120 app:app

# 5. Adicione as variáveis de ambiente:
SECRET_KEY=<gere com: python -c "import secrets; print(secrets.token_urlsafe(32))">
GEMINI_API_KEY=<sua chave do Google AI Studio>
FLASK_DEBUG=false
```

### RAM disponível
512 MB — suficiente para o modo extractive. Para Gemini (generativo), também funciona pois as chamadas são via API, sem modelo local.

---

## 2. Railway — Melhor Experiência Geral (Quase Gratuito)

**Site:** [railway.app](https://railway.app)

### O que é gratuito
- **$5 de crédito grátis por mês** (Hobby plan)
- Este projeto consome ~$1–2/mês com uso moderado → **praticamente gratuito**
- Sem cold starts
- Disco persistente
- HTTPS automático
- Deploy por `git push` ou GitHub Actions

### Por que é melhor para portfolio
- App fica **sempre online**, sem atraso inicial
- Interface moderna e fácil de mostrar em entrevistas
- Métricas de uso visíveis no dashboard
- Suporta variáveis de ambiente via dashboard ou `.env`

### Como publicar

```bash
# 1. Instale o CLI
npm install -g @railway/cli

# 2. Autentique
railway login

# 3. Na pasta do projeto:
railway init
railway up

# 4. Adicione as variáveis no dashboard ou via CLI:
railway variables set SECRET_KEY="..." GEMINI_API_KEY="..." FLASK_DEBUG=false
```

O `Procfile` já está configurado — Railway detecta automaticamente.

### Custo estimado

Com uso de portfolio (< 1000 requisições/dia):
- CPU: ~$0.20/mês
- RAM (512 MB): ~$0.60/mês
- **Total: ~$0.80/mês → coberto pelo crédito gratuito**

---

## 3. Fly.io — Melhor Controle Técnico

**Site:** [fly.io](https://fly.io)

### O que é gratuito (sempre)
- 3 VMs compartilhadas (`shared-cpu-1x`, 256 MB RAM) — **sem expirar**
- 3 GB de volume persistente
- 160 GB de saída de rede/mês
- HTTPS e certificado SSL automático
- Domínio customizado gratuito

### Limitação
RAM de 256 MB pode ser apertada durante scraping pesado. Use `--vm-size shared-cpu-1x` com `--vm-memory 512` (cobra ~$1/mês extra pelo upgrade de RAM).

### Como publicar

```bash
# 1. Instale o CLI
curl -L https://fly.io/install.sh | sh

# 2. Autentique
fly auth login

# 3. Na pasta do projeto:
fly launch
# Responda as perguntas: nome do app, região (GRU = São Paulo), sem banco de dados

# 4. Configure os secrets
fly secrets set SECRET_KEY="..." GEMINI_API_KEY="..."

# 5. Deploy
fly deploy
```

O `Dockerfile` existente no projeto já é compatível com Fly.io.

### Por que é bom para portfolio
Fly.io tem boa reputação entre desenvolvedores — aparecer em entrevistas "deployei no Fly.io" passa uma imagem técnica mais sofisticada que "usei o Heroku".

---

## 4. Google Cloud Run — Melhor para Escala e Currículo

**Site:** [cloud.google.com/run](https://cloud.google.com/run)

### O que é gratuito (sempre, mesmo com conta gratuita encerrada)
- **2 milhões de requisições/mês**
- 360.000 GB-segundos de memória/mês
- 180.000 vCPU-segundos/mês
- Egress de rede: 1 GB/mês

Para um projeto de portfolio com poucos acessos, **o custo é $0,00**.

### Limitação
Cold start de 2–5 segundos quando o container não está em execução. Diferente do Render, o Cloud Run acorda muito mais rápido.

### Como publicar

```bash
# Pré-requisito: gcloud CLI instalado e projeto GCP criado

PROJECT_ID=meu-projeto-gcp
REGION=southamerica-east1   # São Paulo

# Build e deploy direto do source (sem precisar do Docker localmente)
gcloud run deploy article-summarizer \
  --source . \
  --region $REGION \
  --allow-unauthenticated \
  --memory 512Mi \
  --cpu 1 \
  --timeout 120 \
  --set-env-vars FLASK_DEBUG=false \
  --set-env-vars SUMMARIZATION_METHOD=extractive \
  --update-secrets SECRET_KEY=article-summarizer-secret:latest \
  --update-secrets GEMINI_API_KEY=gemini-api-key:latest

# Criar os secrets antes:
echo -n "sua-secret-key" | gcloud secrets create article-summarizer-secret --data-file=-
echo -n "sua-gemini-key" | gcloud secrets create gemini-api-key --data-file=-
```

### Por que é ótimo para currículo
**"Deployei na GCP com Cloud Run"** é exatamente o que equipes de produto e engenharia querem ver. Mostra conhecimento de containers, infraestrutura serverless e boas práticas de secrets management.

---

## 5. Koyeb — Alternativa Simples sem Cold Start

**Site:** [koyeb.com](https://koyeb.com)

### O que é gratuito
- 1 Web Service sempre ativo (sem cold start)
- 512 MB RAM, 0.1 vCPU
- HTTPS automático
- Domínio `seuapp.koyeb.app`

### Como publicar
1. Crie conta em koyeb.com
2. New App → GitHub → selecione o repositório
3. Buildpack detecta Python automaticamente
4. Adicione as variáveis de ambiente no dashboard
5. Deploy

Não requer configuração de `Dockerfile` — o Koyeb lê o `Procfile` diretamente.

---

## Recomendação para Portfolio

### Cenário 1: Quer publicar agora, de graça, sem complicação
→ **Render** + cron-job.org para manter acordado

### Cenário 2: Quer a melhor experiência para mostrar em entrevistas
→ **Railway** (usa o crédito de $5 — praticamente $0)

### Cenário 3: Quer impressionar com infraestrutura
→ **Google Cloud Run** (menciona GCP no currículo)

### Cenário 4: Quer total controle e sem cold start de graça
→ **Fly.io**

---

## Domínio Customizado Gratuito

Para todas as opções acima (exceto PythonAnywhere free), você pode apontar um domínio próprio.

**Opção gratuita:** [Freenom](https://freenom.com) oferece domínios `.tk`, `.ml`, `.ga` gratuitos por 1 ano. Não é ideal para currículo profissional.

**Opção recomendada (~$10/ano):** Registre um `.com.br` na [Registro.br](https://registro.br) (~R$40/ano) ou um `.com` na [Namecheap](https://namecheap.com) (~$10/ano). Domínio próprio eleva muito a percepção de profissionalismo.

Use [Cloudflare](https://cloudflare.com) (gratuito) como DNS e CDN na frente de qualquer plataforma — dá HTTPS, cache de assets estáticos e protege contra DDoS.

---

## Gemini API Key — Custo Real

O Gemini **gemini-2.5-flash** tem uma camada gratuita generosa:
- **15 requisições/minuto**
- **1 milhão de tokens/dia** (gratuito)
- **1 500 requisições/dia** (gratuito)

Para um portfolio com tráfego baixo, o custo da API Gemini é **$0,00**. Apenas se viralizar (improvável para um portfolio) você precisaria pagar.

Obtenha sua chave em: [aistudio.google.com](https://aistudio.google.com/app/apikey)

---

## Checklist Antes de Publicar

- [ ] `SECRET_KEY` definido como variável de ambiente (nunca no código)
- [ ] `GEMINI_API_KEY` definido como variável de ambiente / secret
- [ ] `FLASK_DEBUG=false`
- [ ] `outputs/` e `.cache/` no `.gitignore` (já configurado)
- [ ] Testou localmente com `make run` antes de fazer deploy
- [ ] Tem o link do repositório GitHub no README para recrutadores verem o código
- [ ] Link do app publicado no LinkedIn e no GitHub profile README
