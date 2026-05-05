from __future__ import annotations

from dataclasses import dataclass
from html import escape
from typing import Any

from app.logging import find_latest_traces_for_user_date
from app.shared.domain import CurrentBudgetView

_Trace = dict[str, Any]
_TRACE_BUNDLES = ("intake_execution", "intake_turn", "v2_bundle2", "v2_bundle1")


@dataclass(frozen=True)
class _RequestDebugFields:
    request_id: str
    trace_link: str
    text: str


@dataclass(frozen=True)
class _PayloadDebugFields:
    estimated_kcal: int
    route_target: str
    action_taken: str


@dataclass(frozen=True)
class _ManagerDecisionDebugFields:
    should_render: bool
    clarify_posture: str
    final_action: str


@dataclass(frozen=True)
class _EvidenceDebugFields:
    eligibility: str
    why_not_exact: str


@dataclass(frozen=True)
class _MacroDebugFields:
    macro_display: str
    macro_reason: str


@dataclass(frozen=True)
class _LatencyDebugFields:
    latency_total_ms: int
    slowest_step_name: str


@dataclass(frozen=True)
class _TraceDebugFields:
    label: str
    request: _RequestDebugFields
    payload: _PayloadDebugFields
    manager: _ManagerDecisionDebugFields
    evidence: _EvidenceDebugFields
    macro: _MacroDebugFields
    latency: _LatencyDebugFields


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


def _select_latest_trace(latest_by_bundle: dict[str, _Trace | None]) -> tuple[_Trace | None, str]:
    latest_intake_execution_trace = latest_by_bundle.get("intake_execution") or latest_by_bundle.get("v2_bundle2")
    latest_intake_turn_trace = latest_by_bundle.get("intake_turn") or latest_by_bundle.get("v2_bundle1")
    latest_trace = latest_intake_execution_trace or latest_intake_turn_trace
    latest_trace_label = "Latest Intake Execution Trace" if latest_intake_execution_trace is not None else "Latest Intake Entry Trace"
    return latest_trace, latest_trace_label


def _sidecar_section(latest_trace: _Trace, key: str) -> _Trace:
    return (latest_trace.get("sidecar_output", {}) or {}).get(key) or {}


def _payload_from(tool_outputs: _Trace) -> _Trace:
    nutrition_artifact = tool_outputs.get("nutrition_artifact", {}) or {}
    return nutrition_artifact.get("payload", {}) or tool_outputs.get("nutrition_payload", {}) or {}


def _trace_payload_sections(latest_trace: _Trace) -> tuple[_Trace, _Trace, _Trace, _Trace, _Trace]:
    request = latest_trace.get("request", {}) or {}
    tool_outputs = latest_trace.get("tool_outputs", {}) or {}
    macro_summary = tool_outputs.get("macro_summary", {}) or _sidecar_section(latest_trace, "macro")
    evidence_summary = tool_outputs.get("evidence_summary", {}) or _sidecar_section(latest_trace, "evidence")
    latency_tracking = latest_trace.get("latency_tracking", {}) or {}
    return request, _payload_from(tool_outputs), macro_summary, evidence_summary, latency_tracking


def _first_manager_round_decision(latest_trace: _Trace) -> _Trace:
    manager_rounds = latest_trace.get("manager_rounds", []) or []
    if not isinstance(manager_rounds, list) or not manager_rounds:
        return {}
    first_round = manager_rounds[0] or {}
    if not isinstance(first_round, dict):
        return {}
    return first_round.get("decision", {}) or {}


def _request_id_and_link(latest_trace: _Trace) -> tuple[str, str]:
    trace_meta = latest_trace.get("trace_meta", {}) or {}
    request_id = str(latest_trace.get("request_id") or trace_meta.get("request_id") or "n/a")
    trace_link = f"/admin/trace/{request_id}" if request_id != "n/a" else ""
    return request_id, trace_link


def _why_not_exact(evidence_summary: _Trace) -> str:
    return ", ".join(str(item) for item in (evidence_summary.get("why_not_exact") or [])) or "n/a"


def _value_or(value: Any, default: Any) -> Any:
    return value or default


def _string_or(value: Any, default: str) -> str:
    return str(_value_or(value, default))


def _int_or_zero(value: Any) -> int:
    return int(_value_or(value, 0))


def _build_trace_debug_fields(*, latest_trace: _Trace, latest_trace_label: str) -> _TraceDebugFields:
    request, payload, macro_summary, evidence_summary, latency_tracking = _trace_payload_sections(latest_trace)
    manager_round_1 = _first_manager_round_decision(latest_trace)
    manager_final_decision = latest_trace.get("manager_final_decision", {}) or {}
    request_id, trace_link = _request_id_and_link(latest_trace)
    return _TraceDebugFields(
        label=latest_trace_label,
        request=_RequestDebugFields(
            request_id=request_id,
            trace_link=trace_link,
            text=_string_or(request.get("text"), ""),
        ),
        payload=_PayloadDebugFields(
            estimated_kcal=_int_or_zero(payload.get("estimated_kcal")),
            route_target=_string_or(payload.get("route_target"), "n/a"),
            action_taken=_string_or(payload.get("action_taken"), "n/a"),
        ),
        manager=_ManagerDecisionDebugFields(
            should_render=bool(manager_round_1 or manager_final_decision),
            clarify_posture=_string_or(manager_round_1.get("clarify_posture"), "n/a"),
            final_action=_string_or(manager_final_decision.get("final_action"), "n/a"),
        ),
        evidence=_EvidenceDebugFields(
            eligibility=_string_or(evidence_summary.get("eligibility"), "n/a"),
            why_not_exact=_why_not_exact(evidence_summary),
        ),
        macro=_MacroDebugFields(
            macro_display=_string_or(macro_summary.get("display_status"), "hide"),
            macro_reason=_string_or(macro_summary.get("guard_reason"), "n/a"),
        ),
        latency=_LatencyDebugFields(
            latency_total_ms=_int_or_zero(latency_tracking.get("total_duration_ms")),
            slowest_step_name=_string_or(latency_tracking.get("slowest_step_name"), "n/a"),
        ),
    )


def _render_trace_debug_html(fields: _TraceDebugFields) -> str:
    manager_decision_html = ""
    if fields.manager.should_render:
        manager_decision_html = f'<div class=\"meal-meta\">clarify_posture: {escape(fields.manager.clarify_posture)} | final_action: {escape(fields.manager.final_action)}</div>'

    trace_link_html = ""
    if fields.request.trace_link:
        trace_link_html = f'<div class=\"meal-meta\"><a href=\"{escape(fields.request.trace_link)}\" target=\"_blank\">open /admin/trace/{escape(fields.request.request_id)}</a></div>'

    return f"""
    <section class=\"panel\">
      <div class=\"eyebrow\">{escape(fields.label)}</div>
      <div class=\"subtle\">Latest request artifact for this user and local day, even if the meal did not canonically commit.</div>
      <ul>
        <li class=\"meal-item\">
          <div class=\"meal-title\">Request {escape(fields.request.request_id)}</div>
          <div class=\"meal-meta\">text: {escape(fields.request.text)}</div>
          <div class=\"meal-meta\">estimated_kcal: {fields.payload.estimated_kcal} | route_target: {escape(fields.payload.route_target)}</div>
          <div class=\"meal-meta\">action_taken: {escape(fields.payload.action_taken)}</div>
          {manager_decision_html}
          <div class=\"meal-meta\">eligibility: {escape(fields.evidence.eligibility)} | why_not_exact: {escape(fields.evidence.why_not_exact)}</div>
          <div class=\"meal-meta\">macro_display: {escape(fields.macro.macro_display)} | macro_reason: {escape(fields.macro.macro_reason)}</div>
          <div class=\"meal-meta\">latency total: {fields.latency.latency_total_ms} ms | slowest: {escape(fields.latency.slowest_step_name)}</div>
          {trace_link_html}
        </li>
      </ul>
    </section>
    """


def render_latest_trace_debug(*, user_id: str, local_date: str) -> str:
    latest_by_bundle = find_latest_traces_for_user_date(
        user_id=user_id,
        local_date=local_date,
        bundles=_TRACE_BUNDLES,
    )
    latest_trace, latest_trace_label = _select_latest_trace(latest_by_bundle)
    if latest_trace is None:
        return ""
    fields = _build_trace_debug_fields(latest_trace=latest_trace, latest_trace_label=latest_trace_label)
    return _render_trace_debug_html(fields)
