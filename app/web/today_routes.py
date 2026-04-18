from __future__ import annotations

from datetime import datetime
from html import escape
from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse

from pydantic import BaseModel
from ..application.current_budget_read_model import build_current_budget_view
from ..application.canonical_commit_bridge import record_budget_adjustment_to_canonical
from ..database import get_db, get_or_create_user
from ..domain import CurrentBudgetView

router = APIRouter()

class BudgetAdjustmentRequest(BaseModel):
    user_id: str
    delta_kcal: int
    local_date: str



def _resolve_today_local_date(local_date: str | None) -> str:
    if isinstance(local_date, str):
        stripped = local_date.strip()
        if stripped:
            return stripped
    return datetime.now().date().isoformat()


def _load_today_budget_view(
    db: Any,
    *,
    user_id: str,
    local_date: str | None,
) -> CurrentBudgetView:
    user = get_or_create_user(db, user_id)
    return build_current_budget_view(
        db,
        user_id=user.id,
        local_date=_resolve_today_local_date(local_date),
    )


def _render_today_surface(*, user_id: str, local_date: str, view: CurrentBudgetView) -> str:
    meal_items = []
    for meal in view.meals:
        occurred_at = meal.occurred_at.isoformat(sep=" ", timespec="minutes") if meal.occurred_at else "unknown"
        meal_items.append(
            f"""
            <li class=\"meal-item\">
                <div class=\"meal-title\">{escape(meal.meal_title or 'meal')}</div>
                <div class=\"meal-meta\">{escape(occurred_at)} | {int(meal.total_kcal or 0)} kcal | {escape(meal.resolution_status or 'completed_meal')}</div>
            </li>
            """.strip()
        )
    meals_html = "\n".join(meal_items) if meal_items else "<li class=\"empty\">No committed meals yet.</li>"
    last_recomputed = view.last_recomputed_at.isoformat(sep=" ", timespec="minutes") if view.last_recomputed_at else "n/a"
    return f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Today | Canary</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f8fafc;
      --panel: #ffffff;
      --text: #0f172a;
      --muted: #64748b;
      --line: #e2e8f0;
      --accent: #0f172a;
    }}
    body {{
      margin: 0;
      font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: linear-gradient(180deg, #f8fafc 0%, #ffffff 100%);
      color: var(--text);
    }}
    .shell {{
      max-width: 920px;
      margin: 0 auto;
      padding: 32px 20px 48px;
    }}
    .eyebrow {{
      text-transform: uppercase;
      letter-spacing: 0.18em;
      font-size: 11px;
      color: var(--muted);
      font-weight: 700;
    }}
    h1 {{
      margin: 8px 0 8px;
      font-size: 32px;
      line-height: 1.1;
    }}
    .subtle {{
      color: var(--muted);
      font-size: 14px;
      line-height: 1.5;
    }}
    .panel {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 16px;
      padding: 18px;
      margin-top: 20px;
      box-shadow: 0 8px 32px rgba(15, 23, 42, 0.04);
    }}
    .stats {{
      display: grid;
      gap: 12px;
      grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
      margin-top: 14px;
    }}
    .stat {{
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 14px;
      background: #fcfcfd;
    }}
    .stat-label {{
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.14em;
      color: var(--muted);
      font-weight: 700;
      margin-bottom: 8px;
    }}
    .stat-value {{
      font-size: 28px;
      font-weight: 800;
      line-height: 1;
    }}
    .stat-hint {{
      margin-top: 6px;
      color: var(--muted);
      font-size: 12px;
    }}
    ul {{
      list-style: none;
      padding: 0;
      margin: 14px 0 0;
    }}
    .meal-item {{
      padding: 14px 0;
      border-top: 1px solid var(--line);
    }}
    .meal-item:first-child {{
      border-top: none;
      padding-top: 0;
    }}
    .meal-title {{
      font-weight: 700;
      font-size: 15px;
      margin-bottom: 4px;
    }}
    .meal-meta, .empty {{
      color: var(--muted);
      font-size: 13px;
    }}
    .footer {{
      margin-top: 20px;
      color: var(--muted);
      font-size: 12px;
    }}
    .pill {{
      display: inline-block;
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 4px 10px;
      font-size: 11px;
      font-weight: 700;
      color: var(--muted);
      margin-right: 8px;
    }}
  </style>
</head>
<body>
  <main class=\"shell\">
    <div class=\"eyebrow\">Today Surface</div>
    <h1>Canonical current-budget truth</h1>
    <p class=\"subtle\">Reads from the current-budget read model only. No recommendation, rescue, calibration, or proactive behavior is introduced here.</p>

    <section class=\"panel\">
      <div>
        <span class=\"pill\">user: {escape(user_id)}</span>
        <span class=\"pill\">date: {escape(local_date)}</span>
        <span class=\"pill\">source: current_budget_read_model</span>
      </div>
      <div class=\"stats\">
        <div class=\"stat\">
          <div class=\"stat-label\">Budget</div>
          <div class=\"stat-value\">{int(view.budget_kcal or 0)}</div>
          <div class=\"stat-hint\">kcal target for the day</div>
        </div>
        <div class=\"stat\">
          <div class=\"stat-label\">Consumed</div>
          <div class=\"stat-value\">{int(view.consumed_kcal or 0)}</div>
          <div class=\"stat-hint\">from active canonical meal versions</div>
        </div>
        <div class=\"stat\">
          <div class=\"stat-label\">Remaining</div>
          <div class=\"stat-value\">{int(view.remaining_kcal or 0)}</div>
          <div class=\"stat-hint\">budget minus consumed and adjustments</div>
        </div>
        <div class=\"stat\">
          <div class=\"stat-label\">Meals</div>
          <div class=\"stat-value\">{int(view.active_meal_count or 0)}</div>
          <div class=\"stat-hint\">active meal versions today</div>
        </div>
      </div>
    </section>

    <section class=\"panel\">
      <div class=\"eyebrow\">Committed Meals</div>
      <ul>
        {meals_html}
      </ul>
    </section>

    <div class=\"footer\">
      Last recomputed: {escape(last_recomputed)}
    </div>
  </main>
</body>
</html>"""


@router.get("/today/current-budget")
async def today_current_budget(
    user_id: str = "default_user",
    local_date: str | None = None,
    db: Any = Depends(get_db),
) -> dict:
    view = _load_today_budget_view(db, user_id=user_id, local_date=local_date)
    return view.model_dump(mode="json")


@router.get("/today", response_class=HTMLResponse)
async def today(
    user_id: str = "default_user",
    local_date: str | None = None,
    db: Any = Depends(get_db),
) -> HTMLResponse:
    resolved_local_date = _resolve_today_local_date(local_date)
    view = _load_today_budget_view(db, user_id=user_id, local_date=resolved_local_date)
    return HTMLResponse(
        content=_render_today_surface(user_id=user_id, local_date=resolved_local_date, view=view),
        media_type="text/html; charset=utf-8",
    )

@router.post("/today/budget-adjustment")
async def post_budget_adjustment(req: BudgetAdjustmentRequest, db: Any = Depends(get_db)) -> dict:
    user = get_or_create_user(db, req.user_id)
    entry = record_budget_adjustment_to_canonical(
        db,
        user=user,
        delta_kcal=req.delta_kcal,
        local_date=req.local_date,
        metadata={"source": "ui_adjustment"}
    )
    return {
        "status": "ok",
        "ledger_entry_id": entry.id,
        "delta_kcal": req.delta_kcal,
    }

