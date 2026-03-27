# Text Meal Canary

獨立的本地 text-meal canary。這個 repo 只做：

- 文字描述餐點
- component sketch
- component-level kcal / macros 暫估
- uncertainty profile
- disposition
- 必要時 Tavily search
- 本地測試頁與 audit log

## Local Run

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python -m uvicorn app.main:app --host 127.0.0.1 --port 8011
```

本地頁：

- [http://127.0.0.1:8011](http://127.0.0.1:8011)

## Tests

```powershell
python -m pytest tests -q
```
