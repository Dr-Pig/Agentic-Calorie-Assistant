# Text Meal Canary

Technical bootstrap starts at [AGENTS.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/AGENTS.md).

## Local Run

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python -m uvicorn app.main:app --host 127.0.0.1 --port 8011
```

Open [http://127.0.0.1:8011](http://127.0.0.1:8011).

## Tests

```powershell
python -m pytest tests -q
```
