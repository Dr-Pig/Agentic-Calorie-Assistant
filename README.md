# Text Meal Canary

Technical bootstrap starts at [AGENTS.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/AGENTS.md).

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

For VS Code, reopen the repository in the checked-in Dev Container. It uses the same `compose.yaml` `app` service and keeps source files mounted at `/app`.

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
