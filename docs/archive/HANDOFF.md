# Text Meal Canary Handoff

## Repo

- Local path: `C:\Users\User\Documents\Playground\line-liff-calorie-helper-text-meal-canary-main`

## Current version

- Version: `text-meal-canary.v10.4`
- Schema signature:
  - `risk_gate+structured_main_path+local_retrieval_then_search_fallback+zero_kcal_guard+retry+uncertainty_drivers|request_id_trace`

## Read this first

1. [TEXT_MEAL_HISTORY_AND_HANDBOOK.md](C:\Users\User\Documents\Playground\line-liff-calorie-helper-text-meal-canary-main\docs\TEXT_MEAL_HISTORY_AND_HANDBOOK.md)
2. [agent.md](C:\Users\User\Documents\Playground\line-liff-calorie-helper-text-meal-canary-main\agent.md)
3. [text_meal.py](C:\Users\User\Documents\Playground\line-liff-calorie-helper-text-meal-canary-main\app\usecases\text_meal.py)

## Runtime surface

- `GET /ping`
- `GET /`
- `POST /estimate`
- `GET /logs`

## How to run locally

```powershell
cd C:\Users\User\Documents\Playground\line-liff-calorie-helper-text-meal-canary-main
python -m uvicorn app.main:app --host 127.0.0.1 --port 8011
```

Then open:

- [http://127.0.0.1:8011](http://127.0.0.1:8011)

## Required env

At minimum:

- `AI_BUILDER_BASE_URL`
- `AI_BUILDER_TOKEN`
- `BUILDERSPACE_CHAT_MODEL`
- `TAVILY_API_KEY`

## Notes

- Do not use this file as the full architecture history.
- The old `v5` design in previous handoff content is obsolete.
- The complete design history, wrong turns, and next-step guidance now live in the main handbook.
