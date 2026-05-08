# Agentic Calorie Assistant

Local-first calorie deficit logging app for daily desktop self-use.

Technical bootstrap starts at [AGENTS.md](AGENTS.md). Document navigation starts at [docs/DOC_INDEX.md](docs/DOC_INDEX.md).

## Docker / Mac Recommended

Use this path when moving between Windows, macOS, and Linux. Docker is for local deterministic development parity only; it is not a production deployment or readiness claim.

```bash
cp .env.example .env
# Fill AI_BUILDER_BASE_URL, AI_BUILDER_TOKEN, and optional TAVILY_API_KEY in .env.
docker compose build app
docker compose run --rm test
docker compose run --rm app python scripts/verify_environment.py
docker compose up app
```

Open [http://127.0.0.1:8011](http://127.0.0.1:8011).

No Dev Container is currently tracked. Use `compose.yaml` directly for container parity.

## Native Local Run

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python -m uvicorn app.main:app --host 127.0.0.1 --port 8011
```

Open [http://127.0.0.1:8011](http://127.0.0.1:8011).

Native verification is authoritative only on Python 3.12 or newer. Python 3.9 is not authoritative for Phase C active-runtime, persistence, SQLAlchemy app paths, or broader CI gates; use Docker or a Python 3.12 virtual environment instead.

## Tests

```powershell
python -m pytest tests -q
```
