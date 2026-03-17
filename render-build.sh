#!/usr/bin/env bash
# Render build script — installs Python dependencies and runs migrations.
# Chrome/Selenium are NOT supported on Render's free tier.
# JS rendering falls back gracefully to plain HTTP when selenium is absent.
set -o errexit

pip install -r requirements.txt
python -m alembic upgrade head

# Build frontend if Node is available
if command -v npm &> /dev/null && [ -d "frontend" ]; then
    cd frontend && npm ci && npm run build && cd ..
fi
