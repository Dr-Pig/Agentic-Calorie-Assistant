from __future__ import annotations

from typing import Any, Mapping

from app.memory.application.runtime_lab_store_paths import require_scope
from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "memory.application.runtime_lab_review_contract"
)

ACTION_STATUS = {
    "accept_shadow_candidate": "accepted_shadow",
    "reject_candidate": "rejected",
    "mark_do_not_save": "rejected",
    "forget_shadow_candidate": "deleted",
    "needs_more_evidence": "pending",
}
NON_CLAIMS = [
    "not_product_activation_evidence",
    "not_private_self_use_approval",
    "not_durable_product_memory",
    "not_manager_context_injection",
]


def build_memory_candidate_review_contract(
    candidates: list[Mapping[str, Any]],
    review_actions: list[Mapping[str, Any]],
) -> dict[str, Any]:
    candidates_by_id = {str(candidate.get("candidate_id")): candidate for candidate in candidates}
    blockers = [
        *_candidate_blockers(candidates),
        *_action_blockers(review_actions, candidates_by_id),
    ]
    results = [] if blockers else [
        _review_result(candidates_by_id[str(action["target_candidate_id"])], action)
        for action in review_actions
    ]
    return {
        "artifact_type": "runtime_lab_memory_candidate_review_contract",
        "status": "pass" if results and not blockers else "blocked",
        "owner": "app/memory",
        "consumer": "runtime_lab_memory_lifecycle_validator",
        "retirement_trigger": "approved_memory_runtime_activation_plan",
        "review_item_count": len(candidates),
        "review_action_count": len(review_actions),
        "review_results": results,
        "reviewed_shadow_candidates": [
            result["candidate_patch"] for result in results
        ],
        "blockers": blockers,
        "runtime_connected": False,
        "lab_isolated": True,
        "runtime_effect_allowed": False,
        "runtime_lab_store_written": False,
        "durable_product_memory_written": False,
        "confirmed_memory_promoted": False,
        "product_confirmed_memory_created": False,
        "user_facing_behavior_changed": False,
        "canonical_mutation_changed": False,
        "manager_context_packet_changed": False,
        "shadow_memory_context_pack_used": False,
        "manager_context_injected": False,
        "non_claims": list(NON_CLAIMS),
    }


def _candidate_blockers(candidates: list[Mapping[str, Any]]) -> list[str]:
    blockers: list[str] = []
    for candidate in candidates:
        candidate_id = str(candidate.get("candidate_id") or "unknown_candidate")
        try:
            require_scope(_mapping(candidate.get("scope_keys")))
        except ValueError as exc:
            blockers.append(f"{candidate_id}.{exc}")
        if not candidate.get("source_object_refs"):
            blockers.append(f"{candidate_id}.missing_source_object_refs")
        for flag in (
            "runtime_effect_allowed",
            "durable_product_memory_written",
            "manager_context_packet_changed",
        ):
            if candidate.get(flag) is True:
                blockers.append(f"{candidate_id}.{flag}")
    return blockers


def _action_blockers(
    review_actions: list[Mapping[str, Any]],
    candidates_by_id: dict[str, Mapping[str, Any]],
) -> list[str]:
    blockers: list[str] = []
    for action in review_actions:
        action_id = _action_id(action)
        action_type = str(action.get("action_type") or "")
        target_id = str(action.get("target_candidate_id") or "")
        if action_type not in ACTION_STATUS:
            blockers.append(f"{action_id}.unsupported_action_type")
        if not action.get("actor"):
            blockers.append(f"{action_id}.missing_actor")
        if not action.get("source_refs"):
            blockers.append(f"{action_id}.missing_source_refs")
        if target_id not in candidates_by_id:
            blockers.append(f"{action_id}.unknown_target_candidate:{target_id}")
    return blockers


def _review_result(
    candidate: Mapping[str, Any],
    action: Mapping[str, Any],
) -> dict[str, Any]:
    action_type = str(action["action_type"])
    status_after = ACTION_STATUS[action_type]
    candidate_patch = {
        **dict(candidate),
        "review_status": status_after,
        "source_object_refs": _source_refs(candidate, action, status_after),
        "promotion_allowed_now": False,
        "runtime_lab_store_write_required": False,
        "durable_product_memory_written": False,
        "runtime_effect_allowed": False,
        "manager_context_packet_changed": False,
    }
    return {
        "action_id": _action_id(action),
        "action_type": action_type,
        "candidate_id": str(candidate["candidate_id"]),
        "review_status_before": str(candidate.get("review_status") or "pending"),
        "review_status_after": status_after,
        "actor": str(action["actor"]),
        "reason_codes": [str(code) for code in action.get("reason_codes", []) if code],
        "memory_use_blocked": action_type in {"reject_candidate", "mark_do_not_save"},
        "do_not_save_requested": action_type == "mark_do_not_save",
        "forget_tombstone_requested": action_type == "forget_shadow_candidate",
        "promotion_allowed_now": False,
        "confirmed_memory_promoted": False,
        "runtime_effect_allowed": False,
        "durable_product_memory_written": False,
        "manager_context_packet_changed": False,
        "candidate_patch": candidate_patch,
    }


def _source_refs(
    candidate: Mapping[str, Any],
    action: Mapping[str, Any],
    status_after: str,
) -> list[str]:
    if status_after == "deleted":
        return []
    return [
        *[str(ref) for ref in candidate.get("source_object_refs", []) if ref],
        *[str(ref) for ref in action.get("source_refs", []) if ref],
    ]


def _action_id(action: Mapping[str, Any]) -> str:
    return str(action.get("action_id") or "review-action")


def _mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    return {}


__all__ = [
    "ACTION_STATUS",
    "SIDECAR_ACTIVATION_CONTRACT",
    "build_memory_candidate_review_contract",
]
