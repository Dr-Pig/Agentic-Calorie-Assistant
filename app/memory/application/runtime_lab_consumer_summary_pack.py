from __future__ import annotations

from typing import Any, Mapping

from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "memory.application.runtime_lab_consumer_summary_pack"
)
POSITIVE_TYPES = {"preference", "temporary_preference"}
RAW_FIELD_NAMES = {"raw_user_input", "raw_transcript", "sanitized_source_trace"}
NON_CLAIMS = [
    "not_product_activation_evidence",
    "not_private_self_use_approval",
    "not_recommendation_serving",
    "not_proactive_sending",
    "not_rescue_commit",
]


def build_runtime_lab_memory_consumer_summary_pack(
    review_contract: Mapping[str, Any],
) -> dict[str, Any]:
    candidates = [_mapping(item) for item in review_contract.get("reviewed_shadow_candidates", [])]
    blockers = _contract_blockers(review_contract) + _candidate_blockers(candidates)
    positive = _accepted(candidates, POSITIVE_TYPES)
    negative = _accepted(candidates, {"negative_preference"})
    golden = _accepted(candidates, {"golden_order"})
    suppression = _accepted(candidates, {"interaction_preference"})
    return {
        "artifact_type": "runtime_lab_memory_consumer_summary_projection",
        "status": "pass" if not blockers else "blocked",
        "owner": "app/memory",
        "consumer": "recommendation_rescue_proactive_shadow_consumers",
        "retirement_trigger": "approved_memory_runtime_activation_plan",
        "source_review_contract_artifact_type": review_contract.get("artifact_type"),
        "preference_profile_summary": _preference_summary(positive, negative),
        "golden_order_summary": _golden_summary(golden),
        "suppression_summary": _suppression_summary(suppression),
        "omission_trace": _omissions(candidates),
        "blockers": blockers,
        "runtime_connected": False,
        "lab_isolated": True,
        "summary_first": True,
        "raw_transcript_included": False,
        "runtime_effect_allowed": False,
        "durable_product_memory_written": False,
        "user_facing_behavior_changed": False,
        "canonical_mutation_changed": False,
        "manager_context_packet_changed": False,
        "recommendation_served": False,
        "proactive_sent": False,
        "rescue_proposal_committed": False,
        "retrieval_ranking_changed": False,
        "non_claims": list(NON_CLAIMS),
    }


def _contract_blockers(review_contract: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    if review_contract.get("status") != "pass":
        blockers.append("review_contract_not_pass")
        blockers.extend(str(blocker) for blocker in review_contract.get("blockers", []))
    if review_contract.get("artifact_type") != "runtime_lab_memory_candidate_review_contract":
        blockers.append("unsupported_review_contract_artifact")
    return blockers


def _candidate_blockers(candidates: list[Mapping[str, Any]]) -> list[str]:
    blockers: list[str] = []
    for candidate in candidates:
        candidate_id = _candidate_id(candidate)
        payload = _mapping(candidate.get("payload"))
        if payload.get("runtime_truth_allowed") is True:
            blockers.append(f"{candidate_id}.runtime_truth_allowed")
        for flag in ("runtime_effect_allowed", "durable_product_memory_written"):
            if candidate.get(flag) is True:
                blockers.append(f"{candidate_id}.{flag}")
    return blockers


def _preference_summary(
    positive: list[Mapping[str, Any]],
    negative: list[Mapping[str, Any]],
) -> dict[str, Any]:
    return {
        "summary_type": "preference_profile_summary",
        "source_kind": "shadow_review_summary",
        "is_durable_memory_truth": False,
        "accepted_shadow_candidate_ids": [_candidate_id(candidate) for candidate in positive],
        "preference_summaries": [_summary_entry(candidate) for candidate in positive],
        "negative_preference_blockers": [_candidate_id(candidate) for candidate in negative],
    }


def _golden_summary(candidates: list[Mapping[str, Any]]) -> dict[str, Any]:
    return {
        "summary_type": "golden_order_summary",
        "source_kind": "shadow_review_summary",
        "is_durable_memory_truth": False,
        "projection_kind": "golden_order_projection_from_reviewed_shadow",
        "real_golden_order_materialized": False,
        "orders": [
            {
                "candidate_id": _candidate_id(candidate),
                "store_name": str(_payload(candidate).get("store_name") or ""),
                "item_names": list(_payload(candidate).get("item_names") or []),
                "summary": _summary(candidate),
            }
            for candidate in candidates
        ],
    }


def _suppression_summary(candidates: list[Mapping[str, Any]]) -> dict[str, Any]:
    return {
        "summary_type": "suppression_summary",
        "source_kind": "shadow_review_summary",
        "is_durable_memory_truth": False,
        "suppression_blockers": [
            {
                "candidate_id": _candidate_id(candidate),
                "trigger_type": str(_payload(candidate).get("trigger_type") or "unknown"),
                "summary": _summary(candidate),
            }
            for candidate in candidates
        ],
    }


def _omissions(candidates: list[Mapping[str, Any]]) -> list[dict[str, str]]:
    return [
        {"candidate_id": _candidate_id(candidate), "reason": "not_accepted_shadow"}
        for candidate in candidates
        if candidate.get("review_status") != "accepted_shadow"
    ]


def _accepted(
    candidates: list[Mapping[str, Any]],
    candidate_types: set[str],
) -> list[Mapping[str, Any]]:
    return [
        candidate
        for candidate in candidates
        if candidate.get("review_status") == "accepted_shadow"
        and str(candidate.get("candidate_type")) in candidate_types
    ]


def _summary_entry(candidate: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "candidate_id": _candidate_id(candidate),
        "candidate_type": str(candidate.get("candidate_type") or "unknown"),
        "summary": _summary(candidate),
        "source_object_refs": list(candidate.get("source_object_refs", [])),
    }


def _summary(candidate: Mapping[str, Any]) -> str:
    payload = _payload(candidate)
    return str(payload.get("summary") or candidate.get("candidate_type") or "")


def _payload(candidate: Mapping[str, Any]) -> Mapping[str, Any]:
    payload = _mapping(candidate.get("payload"))
    return {key: value for key, value in payload.items() if key not in RAW_FIELD_NAMES}


def _candidate_id(candidate: Mapping[str, Any]) -> str:
    return str(candidate.get("candidate_id") or "unknown_candidate")


def _mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    return {}


__all__ = [
    "SIDECAR_ACTIVATION_CONTRACT",
    "build_runtime_lab_memory_consumer_summary_pack",
]
