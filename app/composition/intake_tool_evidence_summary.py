from __future__ import annotations

from typing import Any

from app.intake.application.target_evidence_artifacts import payload_is_target_evidence
from app.composition.payload_macro_summary import build_payload_macro_summary


def payload_trace_contract(payload: Any) -> dict[str, Any]:
    return dict(getattr(payload, "trace_contract", None) or {})


def payload_unresolved_info(payload: Any) -> list[str]:
    raw = payload_trace_contract(payload).get("unresolved_info") or []
    return [str(item) for item in raw if str(item).strip()]


def macro_summary(payload: Any | None) -> dict[str, Any]:
    return build_payload_macro_summary(payload)


def evidence_summary(*, raw_user_input: str, payload: Any | None) -> dict[str, Any]:
    del raw_user_input
    trace_contract = payload_trace_contract(payload) if payload is not None else {}
    if payload_is_target_evidence(payload):
        target_contract = dict(trace_contract.get("target_evidence_contract") or {})
        return _summary(
            eligibility="target_evidence",
            target_evidence_present=True,
            target_evidence_source=target_contract.get("source"),
            intake_execution_guard_family=trace_contract.get("intake_execution_guard_family"),
        )
    component_breakdown = list(getattr(payload, "component_breakdown", None) or []) if payload is not None else []
    grounding_summary = dict(trace_contract.get("grounding_summary") or {})
    db_hit_type = str(trace_contract.get("db_hit_type") or "")
    exact_truth_detected = (
        bool(grounding_summary.get("exact_truth_present"))
        or db_hit_type == "exact_truth"
        or "exact_truth" in {str(item) for item in (grounding_summary.get("evidence_roles") or [])}
        or int(((trace_contract.get("reasoning_state") or {}).get("exact_lane_count") or 0)) > 0
    )
    if exact_truth_detected:
        return _summary(
            eligibility="exact",
            candidate_count=max(1, int(grounding_summary.get("retrieved_knowledge_count") or 1)),
            exact_count=1,
            db_hit_type=db_hit_type,
            search_attempt_count=int(trace_contract.get("search_attempt_count") or 0),
            search_query=trace_contract.get("search_query"),
        )
    if component_breakdown:
        count = len(component_breakdown)
        return _summary(
            eligibility="generic",
            candidate_count=count,
            generic_count=count,
            db_hit_type=db_hit_type,
            search_attempt_count=int(trace_contract.get("search_attempt_count") or 0),
            search_query=trace_contract.get("search_query"),
        )
    why_not_exact = _why_not_exact(trace_contract.get("why_not_exact") or [])
    return _summary(
        eligibility="unavailable",
        why_not_exact=why_not_exact,
        db_hit_type=db_hit_type,
        intake_execution_guard_family=trace_contract.get("intake_execution_guard_family"),
        search_attempt_count=int(trace_contract.get("search_attempt_count") or 0),
        search_query=trace_contract.get("search_query"),
    )


def _why_not_exact(raw_why_not_exact: Any) -> list[str]:
    if isinstance(raw_why_not_exact, str):
        return [raw_why_not_exact] if raw_why_not_exact.strip() else []
    return [str(item) for item in raw_why_not_exact if str(item).strip()]


def _summary(
    *,
    eligibility: str,
    candidate_count: int = 0,
    exact_count: int = 0,
    near_exact_count: int = 0,
    generic_count: int = 0,
    why_not_exact: list[str] | None = None,
    intake_execution_guard_family: Any = None,
    search_attempt_count: int = 0,
    search_query: Any = None,
    db_hit_type: str | None = None,
    target_evidence_present: bool = False,
    target_evidence_source: Any = None,
) -> dict[str, Any]:
    return {
        "eligibility": eligibility,
        "candidate_count": candidate_count,
        "exact_count": exact_count,
        "near_exact_count": near_exact_count,
        "generic_count": generic_count,
        "high_variance_family": False,
        "family_rule": None,
        "why_not_exact": list(why_not_exact or []),
        "intake_execution_guard_family": intake_execution_guard_family,
        "search_attempt_count": search_attempt_count,
        "search_query": search_query,
        "db_hit_type": db_hit_type or None,
        "nutrition_evidence_present": not target_evidence_present and eligibility != "target_evidence",
        "target_evidence_present": target_evidence_present,
        "target_evidence_source": target_evidence_source,
    }
