from __future__ import annotations

from html import escape
from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse

from ..application.canonical_commit_bridge import load_body_observation_history
from ..database import get_db, get_or_create_user
from ..domain import BodyObservation

router = APIRouter()


def _load_weight_history(
    db: Any,
    *,
    user_id: str,
    local_date: str | None,
) -> tuple[int, str | None, list[BodyObservation]]:
    user = get_or_create_user(db, user_id)
    resolved_local_date = None
    if isinstance(local_date, str) and local_date.strip():
        resolved_local_date = local_date.strip()
    history = load_body_observation_history(
        db,
        user_id=user.id,
        local_date=resolved_local_date,
    )
    return user.id, resolved_local_date, history


def _render_weight_surface(*, user_id: str, local_date: str | None, observations: list[BodyObservation]) -> str:
    observation_items = []
    for observation in observations:
        observed_at = observation.observed_at.isoformat(sep=" ", timespec="minutes") if observation.observed_at else "unknown"
        observation_items.append(
            f"""
            <li class=\"observation-item\">
                <div class=\"observation-value\">{observation.value:g} {escape(observation.unit)}</div>
                <div class=\"observation-meta\">{escape(observed_at)} | {escape(observation.local_date)} | {escape(observation.source)}</div>
            </li>
            """.strip()
        )
    observations_html = "\n".join(observation_items) if observation_items else "<li class=\"empty\">No body observations yet.</li>"
    resolved_local_date = local_date or "all dates"
    latest = observations[-1] if observations else None
    latest_value = f"{latest.value:g} {latest.unit}" if latest else "n/a"
    latest_date = latest.local_date if latest else "n/a"
    return f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Weight | Canary</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #fffdf7;
      --panel: #ffffff;
      --text: #111827;
      --muted: #6b7280;
      --line: #e5e7eb;
      --accent: #1f2937;
    }}
    body {{
      margin: 0;
      font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: linear-gradient(180deg, #fffdf7 0%, #ffffff 100%);
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
      margin: 8px 0;
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
      box-shadow: 0 8px 32px rgba(17, 24, 39, 0.04);
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
      background: #fffdfb;
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
    .observation-item {{
      padding: 14px 0;
      border-top: 1px solid var(--line);
    }}
    .observation-item:first-child {{
      border-top: none;
      padding-top: 0;
    }}
    .observation-value {{
      font-weight: 700;
      font-size: 15px;
      margin-bottom: 4px;
    }}
    .observation-meta, .empty {{
      color: var(--muted);
      font-size: 13px;
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
    <div class=\"eyebrow\">Weight Surface</div>
    <h1>Canonical body-observation truth</h1>
    <p class=\"subtle\">Reads from typed body-observation history only. No calibration proposal or recommendation logic is introduced here.</p>

    <section class=\"panel\">
      <div>
        <span class=\"pill\">user: {escape(user_id)}</span>
        <span class=\"pill\">date filter: {escape(resolved_local_date)}</span>
        <span class=\"pill\">source: body_observation_history</span>
      </div>
      <div class=\"stats\">
        <div class=\"stat\">
          <div class=\"stat-label\">Latest Weight</div>
          <div class=\"stat-value\">{escape(latest_value)}</div>
          <div class=\"stat-hint\">latest typed observation</div>
        </div>
        <div class=\"stat\">
          <div class=\"stat-label\">Latest Date</div>
          <div class=\"stat-value\">{escape(latest_date)}</div>
          <div class=\"stat-hint\">local date on record</div>
        </div>
        <div class=\"stat\">
          <div class=\"stat-label\">Observations</div>
          <div class=\"stat-value\">{len(observations)}</div>
          <div class=\"stat-hint\">matching entries in view</div>
        </div>
      </div>
    </section>

    <section class=\"panel\">
      <div class=\"eyebrow\">Observation History</div>
      <ul>
        {observations_html}
      </ul>
    </section>
  </main>
</body>
</html>"""


@router.get("/weight/observations")
async def weight_observations(
    user_id: str = "default_user",
    local_date: str | None = None,
    db: Any = Depends(get_db),
) -> dict:
    resolved_user_id, resolved_local_date, observations = _load_weight_history(
        db,
        user_id=user_id,
        local_date=local_date,
    )
    return {
        "user_id": resolved_user_id,
        "local_date": resolved_local_date,
        "observations": [observation.model_dump(mode="json") for observation in observations],
    }


@router.get("/weight", response_class=HTMLResponse)
async def weight(
    user_id: str = "default_user",
    local_date: str | None = None,
    db: Any = Depends(get_db),
) -> HTMLResponse:
    _, resolved_local_date, observations = _load_weight_history(
        db,
        user_id=user_id,
        local_date=local_date,
    )
    return HTMLResponse(
        content=_render_weight_surface(user_id=user_id, local_date=resolved_local_date, observations=observations),
        media_type="text/html; charset=utf-8",
    )
