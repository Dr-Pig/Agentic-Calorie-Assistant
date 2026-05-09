from __future__ import annotations

from typing import Any

BODY_OBSERVATION_SAME_TRUTH_GATE_ID = "body_observation_same_truth_gate"
BODY_OBSERVATION_SAME_TRUTH_READY_STATUS = "body_observation_same_truth_gate_ready_for_human_review"
BODY_OBSERVATION_UPSTREAM_GATE_ID = "rt6_bootstrap_no_plan_body_closure"


def _object_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def body_observation_same_truth_checked(payload: dict[str, Any]) -> bool:
    summary = _object_dict(payload.get("summary"))
    return (
        payload.get("status") == BODY_OBSERVATION_SAME_TRUTH_READY_STATUS
        and payload.get("browser_executed") is True
        and payload.get("upstream_runtime_gate") == BODY_OBSERVATION_UPSTREAM_GATE_ID
        and summary.get("upstream_gate_green") is True
        and summary.get("all_required_browser_flags_true") is True
    )


def body_observation_same_truth_blockers(group_id: str, payload: dict[str, Any]) -> list[str]:
    if group_id != BODY_OBSERVATION_SAME_TRUTH_GATE_ID:
        return []
    summary = _object_dict(payload.get("summary"))
    blockers: list[str] = []
    if payload.get("browser_executed") is not True:
        blockers.append(f"{group_id}.browser_not_executed")
    if payload.get("upstream_runtime_gate") != BODY_OBSERVATION_UPSTREAM_GATE_ID:
        blockers.append(f"{group_id}.upstream_gate_mismatch")
    if summary.get("upstream_gate_green") is not True:
        blockers.append(f"{group_id}.upstream_gate_not_green")
    if summary.get("all_required_browser_flags_true") is not True:
        blockers.append(f"{group_id}.all_required_browser_flags_not_true")
    return blockers
