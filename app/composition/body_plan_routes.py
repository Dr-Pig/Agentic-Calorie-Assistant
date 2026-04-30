from __future__ import annotations

from html import escape
from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse

from app.body.application import build_active_body_plan_view
from app.database import get_db, get_or_create_user
from app.shared.domain import ActiveBodyPlanView

router = APIRouter()


def _load_active_body_plan(
    db: Any,
    *,
    user_id: str,
) -> ActiveBodyPlanView:
    user = get_or_create_user(db, user_id)
    return build_active_body_plan_view(db, user_id=user.id)


def _render_body_plan_surface(*, user_id: str, view: ActiveBodyPlanView) -> str:
    goal_type = view.goal_type or "unset"
    plan_source = view.plan_source or "unknown"
    return f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Body Plan | Canary</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f8fafc;
      --panel: #ffffff;
      --text: #0f172a;
      --muted: #64748b;
      --line: #e2e8f0;
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
    .panel {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 16px;
      padding: 18px;
      margin-top: 20px;
      box-shadow: 0 8px 32px rgba(15, 23, 42, 0.04);
    }}
    .eyebrow {{
      text-transform: uppercase;
      letter-spacing: 0.18em;
      font-size: 11px;
      color: var(--muted);
      font-weight: 700;
    }}
    h1 {{
      margin: 8px 0;
      font-size: 32px;
      line-height: 1.1;
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
  <main class="shell">
    <div class="eyebrow">Body Plan Surface</div>
    <h1>Active body-plan truth</h1>
    <section class="panel">
      <div>
        <span class="pill">user: {escape(user_id)}</span>
        <span class="pill">plan_status: {escape(view.plan_status)}</span>
        <span class="pill">source: active_body_plan_view</span>
      </div>
      <div class="stats">
        <div class="stat">
          <div class="stat-label">Goal</div>
          <div class="stat-value">{escape(goal_type)}</div>
        </div>
        <div class="stat">
          <div class="stat-label">Daily Target</div>
          <div class="stat-value">{int(view.recommended_target_kcal or 0)}</div>
        </div>
        <div class="stat">
          <div class="stat-label">Safety Floor</div>
          <div class="stat-value">{int(view.safety_floor_kcal or 0)}</div>
        </div>
        <div class="stat">
          <div class="stat-label">Plan Source</div>
          <div class="stat-value">{escape(plan_source)}</div>
        </div>
      </div>
    </section>
  </main>
</body>
</html>"""


@router.get("/body-plan/active")
async def body_plan_active(
    user_id: str = "default_user",
    db: Any = Depends(get_db),
) -> dict:
    view = _load_active_body_plan(db, user_id=user_id)
    return view.model_dump(mode="json")


@router.get("/body-plan", response_class=HTMLResponse)
async def body_plan(
    user_id: str = "default_user",
    db: Any = Depends(get_db),
) -> HTMLResponse:
    view = _load_active_body_plan(db, user_id=user_id)
    return HTMLResponse(
        content=_render_body_plan_surface(user_id=user_id, view=view),
        media_type="text/html; charset=utf-8",
    )
