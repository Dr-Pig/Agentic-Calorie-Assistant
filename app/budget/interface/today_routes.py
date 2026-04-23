from __future__ import annotations

from datetime import datetime
from html import escape
from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse

from pydantic import BaseModel
from ...logging import find_latest_trace_for_user_date
from ..application import build_current_budget_view
from ...intake.application.canonical_commit_bridge import record_budget_adjustment_to_canonical
from ...database import get_db, get_or_create_user
from ...shared.domain import CurrentBudgetView

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
        request_meta = (
            f" | request {escape(meal.source_request_id)}"
            if isinstance(meal.source_request_id, str) and meal.source_request_id.strip()
            else ""
        )
        meal_items.append(
            f"""
            <li class=\"meal-item\">
                <div class=\"meal-title\">{escape(meal.meal_title or 'meal')}</div>
                <div class=\"meal-meta\">{escape(occurred_at)} | {int(meal.total_kcal or 0)} kcal | {escape(meal.resolution_status or 'completed_meal')}{request_meta}</div>
            </li>
            """.strip()
        )
    meals_html = "\n".join(meal_items) if meal_items else "<li class=\"empty\">No committed meals yet.</li>"
    last_recomputed = view.last_recomputed_at.isoformat(sep=" ", timespec="minutes") if view.last_recomputed_at else "n/a"
    latest_debug = ""
    latest_bundle2_trace = find_latest_trace_for_user_date(user_id=user_id, local_date=local_date, bundle="v2_bundle2")
    latest_bundle1_trace = find_latest_trace_for_user_date(user_id=user_id, local_date=local_date, bundle="v2_bundle1")
    latest_trace_debug = ""
    if view.meals:
        latest_meal = view.meals[-1]
        request_id = latest_meal.source_request_id or "n/a"
        trace_link = f"/admin/trace/{request_id}" if request_id != "n/a" else ""
        latest_debug = f"""
        <section class=\"panel\">
          <div class=\"eyebrow\">Latest Calculation Debug</div>
          <div class=\"subtle\">Latest committed meal provenance for independent audit.</div>
          <ul>
            <li class=\"meal-item\">
              <div class=\"meal-title\">Meal version {int(latest_meal.meal_version_id or 0)}</div>
              <div class=\"meal-meta\">title: {escape(latest_meal.meal_title or 'meal')} | total: {int(latest_meal.total_kcal or 0)} kcal</div>
            </li>
            <li class=\"meal-item\">
              <div class=\"meal-title\">Request trace</div>
              <div class=\"meal-meta\">request_id: {escape(request_id)}</div>
              {f'<div class=\"meal-meta\"><a href=\"{escape(trace_link)}\" target=\"_blank\">open /admin/trace/{escape(request_id)}</a></div>' if trace_link else ''}
            </li>
          </ul>
        </section>
        """
    latest_trace = latest_bundle2_trace or latest_bundle1_trace
    latest_trace_label = "Latest Bundle 2 Trace" if latest_bundle2_trace is not None else "Latest Bundle 1 Trace"
    if latest_trace is not None:
        trace_meta = latest_trace.get("trace_meta", {}) or {}
        request = latest_trace.get("request", {}) or {}
        tool_outputs = latest_trace.get("tool_outputs", {}) or {}
        nutrition_artifact = tool_outputs.get("nutrition_artifact", {}) or {}
        payload = nutrition_artifact.get("payload", {}) or tool_outputs.get("nutrition_payload", {}) or {}
        macro_summary = tool_outputs.get("macro_summary", {}) or ((latest_trace.get("sidecar_output", {}) or {}).get("macro") or {})
        evidence_summary = tool_outputs.get("evidence_summary", {}) or ((latest_trace.get("sidecar_output", {}) or {}).get("evidence") or {})
        latency_tracking = latest_trace.get("latency_tracking", {}) or {}
        manager_rounds = latest_trace.get("manager_rounds", []) or []
        manager_round_1 = {}
        if isinstance(manager_rounds, list) and manager_rounds:
            first_round = manager_rounds[0] or {}
            if isinstance(first_round, dict):
                manager_round_1 = first_round.get("decision", {}) or {}
        manager_final_decision = latest_trace.get("manager_final_decision", {}) or {}
        request_id = str(latest_trace.get("request_id") or trace_meta.get("request_id") or "n/a")
        trace_link = f"/admin/trace/{request_id}" if request_id != "n/a" else ""
        latest_trace_debug = f"""
        <section class=\"panel\">
          <div class=\"eyebrow\">{escape(latest_trace_label)}</div>
          <div class=\"subtle\">Latest request artifact for this user and local day, even if the meal did not canonically commit.</div>
          <ul>
            <li class=\"meal-item\">
              <div class=\"meal-title\">Request {escape(request_id)}</div>
              <div class=\"meal-meta\">text: {escape(str(request.get("text") or ""))}</div>
              <div class=\"meal-meta\">estimated_kcal: {int(payload.get("estimated_kcal") or 0)} | route_target: {escape(str(payload.get("route_target") or "n/a"))}</div>
              <div class=\"meal-meta\">action_taken: {escape(str(payload.get("action_taken") or "n/a"))}</div>
              {f'<div class=\"meal-meta\">clarify_posture: {escape(str(manager_round_1.get("clarify_posture") or "n/a"))} | final_action: {escape(str(manager_final_decision.get("final_action") or "n/a"))}</div>' if manager_round_1 or manager_final_decision else ''}
              <div class=\"meal-meta\">eligibility: {escape(str(evidence_summary.get("eligibility") or "n/a"))} | why_not_exact: {escape(", ".join(str(item) for item in (evidence_summary.get("why_not_exact") or [])) or "n/a")}</div>
              <div class=\"meal-meta\">macro_display: {escape(str(macro_summary.get("display_status") or "hide"))} | macro_reason: {escape(str(macro_summary.get("guard_reason") or "n/a"))}</div>
              <div class=\"meal-meta\">latency total: {int(latency_tracking.get("total_duration_ms") or 0)} ms | slowest: {escape(str(latency_tracking.get("slowest_step_name") or "n/a"))}</div>
              {f'<div class=\"meal-meta\"><a href=\"{escape(trace_link)}\" target=\"_blank\">open /admin/trace/{escape(request_id)}</a></div>' if trace_link else ''}
            </li>
          </ul>
        </section>
        """
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

    {latest_debug}
    {latest_trace_debug}

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
