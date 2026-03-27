# Text Meal Canary Handoff

## Repo

- GitHub: `https://github.com/gn4677-lang/line-liff-calorie-helper-text-meal-canary`
- Local path: `C:\Users\exsaf\Documents\Playground\apps\line-liff-calorie-helper-text-meal-canary`

## Current goal

This repo is the isolated canary for text meal estimation.

The current design goal is:

1. Phase 1 resolves meal composition.
2. If composition is unclear, Phase 1 decides whether the missing composition should come from:
   - `search`
   - or `ask_user`
3. Phase 2 only estimates macros and kcal from known components.
4. If macros are usable, the system always answers.
5. If macros are usable but uncertain, it answers first and then explains what may move the numbers.

The code should prefer prompt-guided reasoning over hard-coded category rules or canned follow-up text.

## Current version

- `text-meal-canary.v5`

## Runtime surface

- `GET /ping`
- `GET /`
- `POST /estimate`
- `GET /logs`

## How to run locally

```powershell
cd C:\Users\exsaf\Documents\Playground\apps\line-liff-calorie-helper-text-meal-canary
python -m uvicorn app.main:app --host 127.0.0.1 --port 8011
```

Then open:

- `http://127.0.0.1:8011`

## Required env

At minimum:

- `AI_BUILDER_BASE_URL`
- `AI_BUILDER_TOKEN`
- `BUILDERSPACE_CHAT_MODEL`
- `TAVILY_API_KEY`

## Current reasoning shape

### Phase 1

Minimal structured output:

- `components`
- `source_decision`

Where `source_decision` is one of:

- `ready`
- `search`
- `ask_user`

Optional:

- `meal_title`
- `quantity_hints`
- `component_estimates`
- `followup_question`
- `search_query`

Important:

- `followup_question` is expected only when `source_decision = ask_user`
- `search_query` is expected only when `source_decision = search`
- programmatic canned follow-up fallback has been removed from the normal path

### Phase 2

Minimal structured output:

- `protein_g`
- `carb_g`
- `fat_g`
- `estimated_kcal`
- `answer_mode`

Where `answer_mode` is one of:

- `direct_answer`
- `answer_with_uncertainty`

Optional:

- `component_estimates`
- `uncertain_macro_areas`

## Important files

- `app/usecases/text_meal.py`
- `app/schemas.py`
- `app/providers/builderspace_adapter.py`
- `app/routes.py`
- `static/local-test.html`
- `tests/test_text_meal.py`
- `agent.md`

## Current implementation notes

- The old `component_decision` naming has been replaced in the new flow by `source_decision`.
- Search is only used to supplement composition.
- Search results are fed back into Phase 1 before Phase 2 runs.
- Macro fallback still exists as a safety net if Phase 2 times out or fails to return usable macro JSON.
- The code still keeps logs and traces rich enough for debugging:
  - `debug_steps`
  - `llm_traces`
  - full final payload

## Testing

Run:

```powershell
cd C:\Users\exsaf\Documents\Playground\apps\line-liff-calorie-helper-text-meal-canary
python -m pytest tests -q
```

## What was just changed

- Removed the old canned follow-up fallback from the main flow.
- Reworked Phase 1 to prefer:
  1. resolve components
  2. if not enough, decide whether search can help
  3. only then ask the user
- Slimmed schemas to the minimal required shape for both phases.
- Bumped version to `v5`.
- Rewrote tests around:
  - `ready`
  - `search`
  - `ask_user`

## Known gaps

- The model can still fail to provide a context-aware follow-up question in `ask_user` cases.
  - This is now treated as a prompt / model-output quality issue instead of silently patched by code.
- Phase 2 can still timeout on real BuilderSpace runtime.
  - `macro_fallback` currently covers those cases, but it is only a safety net, not the ideal path.
- Quantity hints are still only as good as the model outputs in Phase 1.
- Some common Taiwanese items may still need better quantity inference from the model, especially breakfast-store serving sizes.

## Next recommended steps

1. Use the local test page and inspect `/logs` for real cases.
2. Focus on improving:
   - Phase 1 quantity hints
   - contextual `ask_user` follow-up wording
   - Phase 2 timeout rate
3. Avoid re-introducing category routing tables or canned follow-up text.
4. Prefer prompt changes that improve the reasoning path rather than more code-side control.
