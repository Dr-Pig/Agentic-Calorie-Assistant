from __future__ import annotations

from html import escape

from app.logging import find_latest_traces_for_user_date
from app.shared.domain import CurrentBudgetView


def render_latest_debug(*, view: CurrentBudgetView) -> str:
    if not view.meals:
        return ""
    latest_meal = view.meals[-1]
    request_id = latest_meal.source_request_id or "n/a"
    trace_link = f"/admin/trace/{request_id}" if request_id != "n/a" else ""
    return f"""
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


def render_latest_trace_debug(*, user_id: str, local_date: str) -> str:
    latest_by_bundle = find_latest_traces_for_user_date(
        user_id=user_id,
        local_date=local_date,
        bundles=("intake_execution", "intake_turn", "v2_bundle2", "v2_bundle1"),
    )
    latest_intake_execution_trace = latest_by_bundle.get("intake_execution") or latest_by_bundle.get("v2_bundle2")
    latest_intake_turn_trace = latest_by_bundle.get("intake_turn") or latest_by_bundle.get("v2_bundle1")
    latest_trace = latest_intake_execution_trace or latest_intake_turn_trace
    latest_trace_label = "Latest Intake Execution Trace" if latest_intake_execution_trace is not None else "Latest Intake Entry Trace"
    if latest_trace is None:
        return ""
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
    return f"""
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
