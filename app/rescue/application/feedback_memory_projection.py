from __future__ import annotations

from typing import Any, Mapping

from app.memory.application.memory_feedback_contract import NON_MUTATION_FLAGS
from app.memory.application.memory_feedback_projection import (
    project_feedback_event_to_shadow_controls,
)
from app.memory.application.runtime_lab_candidate_records import candidate_record
from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "rescue.application.feedback_memory_projection"
)
FEEDBACK_KIND_TO_SUBTYPE = {
    "accept": "accepted_rescue_pattern",
    "dismiss": "dismissed_rescue_instance",
    "complaint": "rescue_hardness_feedback",
    "correction": "rescue_correction_signal",
    "outcome": "rescue_outcome_signal",
}
REASON_BY_SUBTYPE = {
    "accepted_rescue_pattern": "accepted_rescue_requires_review_before_memory",
    "dismissed_rescue_instance": "dismiss_is_instance_feedback_not_permanent_opt_out",
    "rescue_hardness_feedback": "complaint_is_negotiation_feedback_not_dismiss",
    "rescue_correction_signal": "correction_requires_validator_review",
    "rescue_outcome_signal": "outcome_requires_pattern_review",
}
PRODUCTION_DORMANT_FLAGS = {
    "mainline_activation_enabled": False,
    "mainline_route_or_api_mount_allowed": False,
    "production_scheduler_delivery_allowed": False,
    "production_db_mutation_allowed": False,
    "durable_product_memory_written_in_mainline": False,
}


def build_rescue_feedback_memory_projection(
    *,
    feedback_event: Mapping[str, Any],
    rescue_feedback_target: Mapping[str, Any],
) -> dict[str, Any]:
    projection = project_feedback_event_to_shadow_controls(
        feedback_event=feedback_event,
        targets=[rescue_feedback_target],
    )
    blockers = list(projection.get("blockers") or [])
    if str(feedback_event.get("target_type") or "") != "rescue_plan":
        blockers.append("feedback_event.target_type_not_rescue_plan")
    subtype = FEEDBACK_KIND_TO_SUBTYPE.get(str(rescue_feedback_target.get("feedback_kind") or ""))
    if not subtype:
        blockers.append("rescue_feedback_target.feedback_kind_unsupported")
    candidates = [] if blockers else [_candidate(feedback_event, rescue_feedback_target, subtype or "")]
    return {
        "artifact_type": "rescue_feedback_memory_projection",
        "status": "pass" if not blockers else "blocked",
        "owner": "app/rescue",
        "consumer": "memory_review_queue",
        "lab_enabled": True,
        "source_projection_artifact_type": projection.get("artifact_type"),
        "reviewed_memory_candidates": candidates,
        "candidate_count": len(candidates),
        "blockers": blockers,
        "confirmed_memory_promoted": False,
        "auto_promotes_memory": False,
        "rescue_plan_mutated": False,
        "proactive_delivery_enabled": False,
        "scheduler_delivery_allowed": False,
        **dict(NON_MUTATION_FLAGS),
        **dict(PRODUCTION_DORMANT_FLAGS),
    }


def _candidate(
    event: Mapping[str, Any],
    target: Mapping[str, Any],
    subtype: str,
) -> dict[str, Any]:
    payload = {
        "review_status": "pending",
        "promotion_allowed_now": False,
        "human_review_required": True,
        "feedback_action": str(event.get("action") or ""),
        "feedback_kind": str(target.get("feedback_kind") or ""),
        "rescue_memory_subtype": subtype,
        "summary": _summary(event, target, subtype),
        "not_permanent_rescue_opt_out": subtype == "dismissed_rescue_instance",
        "memory_truth_claimed": False,
    }
    return candidate_record(
        case_id=str(event.get("source_turn_id") or "rescue-feedback"),
        candidate_type="rescue_shadow",
        scope_keys={str(k): str(v) for k, v in _mapping(event.get("scope_keys")).items()},
        source_refs=[str(ref) for ref in target.get("source_refs", []) if ref],
        payload=payload,
        reason_codes=[REASON_BY_SUBTYPE[subtype]],
        runtime_connected=True,
    )


def _summary(
    event: Mapping[str, Any],
    target: Mapping[str, Any],
    subtype: str,
) -> str:
    reason = str(event.get("reason") or target.get("summary") or "").strip()
    if subtype == "accepted_rescue_pattern":
        return f"User accepted a rescue plan. {reason}".strip()
    if subtype == "dismissed_rescue_instance":
        return f"User dismissed this rescue proposal instance. {reason}".strip()
    if subtype == "rescue_hardness_feedback":
        return f"User gave hardness or feasibility feedback on rescue. {reason}".strip()
    if subtype == "rescue_correction_signal":
        return f"User corrected rescue assumptions or constraints. {reason}".strip()
    return f"User reported rescue outcome. {reason}".strip()


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = ["SIDECAR_ACTIVATION_CONTRACT", "build_rescue_feedback_memory_projection"]
