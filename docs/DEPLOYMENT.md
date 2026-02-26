# Deployment Guide: Article Summarizer Agent

This guide covers three deployment targets: Google Cloud Run (recommended for production), Render free tier (zero-cost with cold start), and local Docker Compose (development).

**Before deploying**, resolve all CRITICAL findings from `docs/AUDIT_REPORT.md`. The application cannot handle web requests correctly in its current state due to the config naming mismatch (C1) and the `run()` signature bug (C3).

---

## Option A: Google Cloud Run + Cloudflare Pages or Vercel (Recommended)

Cloud Run is a managed container platform that auto-scales, charges only for request time, and handles HTTPS automatically. Because this application serves HTML templates from Flask (it is not a decoupled SPA), there is no separate frontend to deploy — Cloud Run serves both the API and the rendered HTML. Cloudflare or Vercel can be placed in front as a CDN and DDoS shield by proxying all traffic to the Cloud Run URL.

### Prerequisites

- [gcloud CLI](https://cloud.google.com/sdk/docs/install) installed and authenticated (`gcloud auth login`)
- A Google Cloud project with billing enabled
- Docker installed locally
- A [Cloudflare](https://cloudflare.com) or [Vercel](https://vercel.com) account (optional, for CDN)

### Step 1: Write the Dockerfile

Create `Dockerfile` in the project root:

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies for lxml, chardet, and headless Chrome (if Selenium is used)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libxml2-dev \
    libxslt-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Ensure output and cache directories exist
RUN mkdir -p outputs .cache

EXPOSE 8080

CMD ["gunicorn", \
     "--bind", "0.0.0.0:8080", \
     "--workers", "2", \
     "--threads", "4", \
     "--timeout", "120", \
     "app:app"]
```

**Workers and threads:** 2 workers x 4 threads = 8 concurrent requests. Summarization is CPU-bound; more than 2 workers per vCPU provides diminishing returns and risks OOM if BART is loaded. With Gemini (post-refactor), you can safely increase to 4 workers.

**Timeout:** 120 seconds covers extractive summarization of long articles. Generative summarization via Gemini is typically under 10 seconds. Do not lower the timeout below 60 seconds.

### Step 2: Build and Test Locally

```bash
docker build -t article-summarizer .
docker run --rm -p 8080:8080 \
  -e SECRET_KEY=dev-secret-key-change-me \
  -e GEMINI_API_KEY=your-key-here \
  -e FLASK_DEBUG=false \
  article-summarizer
```

Visit `http://localhost:8080` and submit a test URL.

### Step 3: Push to Artifact Registry

```bash
# Set your project and region
PROJECT_ID=your-gcp-project-id
REGION=southamerica-east1   # São Paulo — lowest latency for BR users
IMAGE=gcr.io/$PROJECT_ID/article-summarizer

# Configure Docker to push to GCR
gcloud auth configure-docker

# Build and push
docker build -t $IMAGE .
docker push $IMAGE
```

### Step 4: Deploy to Cloud Run

```bash
gcloud run deploy article-summarizer \
  --image $IMAGE \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --memory 1Gi \
  --cpu 1 \
  --timeout 120 \
  --set-env-vars "FLASK_DEBUG=false" \
  --set-env-vars "CORS_ORIGINS=https://your-domain.com" \
  --set-secrets "SECRET_KEY=article-summarizer-secret:latest" \
  --set-secrets "GEMINI_API_KEY=gemini-api-key:latest"
```

Use `--set-secrets` (Google Secret Manager) rather than `--set-env-vars` for sensitive values. Create the secrets first:

```bash
echo -n "your-secret-key" | gcloud secrets create article-summarizer-secret --data-file=-
echo -n "your-gemini-key" | gcloud secrets create gemini-api-key --data-file=-
```

After deployment, Cloud Run outputs a service URL (`https://article-summarizer-xxxx-rj.a.run.app`).

### Step 5: (Optional) Front with Cloudflare or Vercel

Since Flask renders HTML server-side, there is no static frontend to deploy separately. Cloudflare or Vercel act as a reverse proxy and CDN in front of the Cloud Run URL:

- **Cloudflare:** Add your domain, set DNS to proxy mode, create a Page Rule or Worker that proxies `/*` to your Cloud Run URL. Enable "Cache Everything" only for static assets (`/static/*`). Do not cache `/api/*`.
- **Vercel:** Create a `vercel.json` with a rewrite rule pointing all routes to the Cloud Run URL. This gives you Vercel's edge network as a CDN layer without needing to migrate the application.

---

## Option B: Render Free Tier (Zero Cost with Cold Start)

Render's free tier provides a single web service with 512 MB RAM and automatic HTTPS. The service spins down after 15 minutes of inactivity and takes up to 60 seconds to cold-start on the next request.

**Limitations:**
- 512 MB RAM: Sufficient for extractive summarization. **Do not use BART/Transformers on Render free — it will OOM.** Use Gemini for generative mode.
- Cold start: The first request after inactivity will time out in the browser. Inform users or implement a health-check ping.
- No persistent disk: `outputs/` and `.cache/` directories are reset on each deployment. File-based cache and output downloads will not survive restarts.

### Setup

1. Push your code to a GitHub repository.
2. On Render, create a new **Web Service**, connect the repository.
3. Set the following:
   - **Runtime:** Python 3
   - **Build command:** `pip install -r requirements.txt`
   - **Start command:** (see `Procfile` below)

### Procfile

The existing `Procfile` in the repository is already configured for Render:

```
web: gunicorn --bind 0.0.0.0:$PORT --workers 1 --timeout 120 app:app
```

Use `--workers 1` on Render free tier. A single worker keeps memory usage below 512 MB. Render provides the `PORT` environment variable automatically.

### Environment Variables on Render

In the Render dashboard under **Environment**, add:

| Key | Value |
|---|---|
| `SECRET_KEY` | A long random string (generate with `python -c "import secrets; print(secrets.token_urlsafe(32))"`) |
| `GEMINI_API_KEY` | Your Google Gemini API key |
| `FLASK_DEBUG` | `false` |
| `CORS_ORIGINS` | `https://your-render-domain.onrender.com` |

---

## Docker Compose (Local Development)

For local development with live reloading and persistent volumes:

```yaml
version: "3.9"
services:
  api:
    build: .
    ports:
      - "5000:5000"
    env_file:
      - .env
    volumes:
      - ./outputs:/app/outputs
      - ./.cache:/app/.cache
    command: >
      gunicorn
      --bind 0.0.0.0:5000
      --workers 1
      --threads 2
      --timeout 120
      --reload
      app:app
```

Create a `.env` file (never commit this):

```
SECRET_KEY=local-dev-secret-not-for-production
GEMINI_API_KEY=your-key-here
FLASK_DEBUG=true
CORS_ORIGINS=*
```

Start with:

```bash
docker compose up --build
```

The `--reload` flag in gunicorn restarts workers on code changes, so you do not need to rebuild the container during development.

---

## Environment Variables Reference

| Variable | Required | Default | Description |
|---|---|---|---|
| `SECRET_KEY` | Yes (prod) | Random (dev only) | Flask session signing key. App refuses to start in production without this. |
| `GEMINI_API_KEY` | If using generative mode | — | Google Gemini API key. Extractive mode works without this. |
| `FLASK_DEBUG` | No | `false` | Set to `true` only in local development. Enables auto-reload and detailed error pages. Never `true` in production. |
| `FLASK_HOST` | No | `0.0.0.0` | Address Flask binds to. `0.0.0.0` is correct for containers. |
| `PORT` | No | `5000` | Port to listen on. Render and Cloud Run set this automatically. |
| `CORS_ORIGINS` | No | `*` | Comma-separated list of allowed CORS origins. Set to your frontend domain in production. `*` is acceptable only for local dev. |
| `TIMEOUT_EXTRACAO` | No | `30` | HTTP request timeout in seconds for web scraping. |
| `MAX_TENTATIVAS_EXTRACAO` | No | `3` | Number of scraper retry attempts with exponential backoff. |
| `METODO_SUMARIZACAO` | No | `extractive` | Default summarization method (`extractive` or `generative`). Per-request `metodo` overrides this. |
| `TAMANHO_RESUMO` | No | `medium` | Default summary length (`short`, `medium`, `long`). Per-request `tamanho` overrides this. |
| `DIRETORIO_SAIDA` | No | `outputs` | Directory where output files are written. |
| `CACHE_HABILITADO` | No | `true` | Set to `false` to disable the file-based result cache. |

---

## CI/CD Notes

A GitHub Actions workflow at `.github/workflows/ci.yml` is planned to run automatically on every push to `main` and on every pull request. It should:

1. Run `pytest tests/` with coverage reporting.
2. Run `pip audit` or `safety check` to detect known vulnerable dependencies.
3. Build the Docker image to verify the `Dockerfile` is valid.
4. (On merge to `main`) Push the image to Artifact Registry and trigger a Cloud Run deployment via `gcloud run deploy`.

Until the test suite is implemented (see Audit finding M3), the CI workflow should at minimum run a smoke test: start the Flask app and assert that `GET /` returns HTTP 200.

Reference the workflow file at `.github/workflows/ci.yml` once it is created.

---

## Post-Deployment Checklist

- [ ] `SECRET_KEY` is set to a strong random value (not hardcoded, not the dev default)
- [ ] `FLASK_DEBUG=false` in production
- [ ] `CORS_ORIGINS` is set to specific domains, not `*`
- [ ] SSRF protection is implemented in the scraper before any public exposure
- [ ] SSL verification is re-enabled in `web_scraper.py`
- [ ] Rate limiting is active on `/api/sumarizar` and `/api/limpar-cache`
- [ ] WAF bypass code (`selenium_scraper.py`, bypass logic in `web_scraper.py`) is removed
- [ ] `outputs/` and `.cache/` are excluded from version control (confirmed in `.gitignore`)
- [ ] Health check endpoint (`GET /api/status-agente`) is reachable and returns 200
- [ ] Error responses do not expose stack traces or file paths
