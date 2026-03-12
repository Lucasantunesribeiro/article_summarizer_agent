param(
    [ValidateSet("setup", "install", "lint", "format", "test", "test-cov", "run", "run-prod", "worker", "flower", "db-upgrade")]
    [string]$Task = "run",
    [string]$Url = ""
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Python = "python"
$Pip = Join-Path $Root ".venv\\Scripts\\pip.exe"
$Pytest = Join-Path $Root ".venv\\Scripts\\pytest.exe"
$Ruff = Join-Path $Root ".venv\\Scripts\\ruff.exe"
$Gunicorn = Join-Path $Root ".venv\\Scripts\\gunicorn.exe"
$Celery = Join-Path $Root ".venv\\Scripts\\celery.exe"
$Alembic = Join-Path $Root ".venv\\Scripts\\alembic.exe"

switch ($Task) {
    "setup" {
        & $Python -m venv "$Root\\.venv"
        & $Pip install --upgrade pip
        & $Pip install -r "$Root\\requirements-dev.txt"
    }
    "install" { & $Pip install -r "$Root\\requirements-dev.txt" }
    "lint" { & $Ruff check "$Root" }
    "format" { & $Ruff format "$Root" }
    "test" { & $Pytest "$Root\\tests" -v --ignore="$Root\\tests\\test_db_integration.py" }
    "test-cov" { & $Pytest "$Root\\tests" --cov --cov-report=term-missing --ignore="$Root\\tests\\test_db_integration.py" }
    "run" {
        $env:FLASK_DEBUG = "true"
        & $Python "$Root\\app.py"
    }
    "run-prod" { & $Gunicorn --bind 0.0.0.0:5000 --workers 2 --threads 4 --timeout 120 app:app }
    "worker" { & $Celery -A celery_app worker --loglevel=info }
    "flower" { & $Celery -A celery_app flower --port=5555 }
    "db-upgrade" { & $Alembic upgrade head }
    default {
        if (-not $Url) {
            throw "Use -Url para informar a URL do artigo."
        }
        & $Python "$Root\\main.py" --url $Url
    }
}
