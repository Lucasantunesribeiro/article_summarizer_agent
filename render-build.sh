#!/usr/bin/env bash
# Render build script — installs Python dependencies, runs migrations, builds frontend.
set -o errexit

pip install -r requirements.txt
python -m alembic upgrade head

# Build React SPA — required; deploy fails if this step fails
cd frontend && npm ci && npm run build && cd ..
