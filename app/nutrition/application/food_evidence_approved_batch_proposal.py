from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

_REQUIRED_DECISION_NON_CLAIMS = {
    "no_fooddb_truth_promoted",
    "no_runtime_truth_changed",
    "no_anchor_update",
    "no_packet_truth_created",
    "no_manager_or_appshell_behavior_change",
    "no_eval_oracle_created",
    "no_mutation_authority",
}
_PROPOSAL_NON_CLAIMS = [
    "no_fooddb_truth_promoted",
    "no_runtime_truth_changed",
    "no_runtime_truth_promotion",
    "no_anchor_update",
    "no_exact_card_created",
    "no_nutrition_seed_created",
    "no_packet_truth_created",
    "no_packet_ready_claim",
    "no_websearch_runtime_truth",
    "no_manager_or_appshell_behavior_change",
    "no_eval_oracle_created",
    "no_mutation_authority",
    "no_self_use_approval",
    "no_product_readiness_claim",
]
_FORBIDDEN_PROMOTION_STAGES = {
    "runtime_truth",
    "packet_truth",
    "anchor_update",
    "exact_card_runtime_truth",
    "eval_oracle",
}


def build_food_evidence_approved_batch_proposal(
    *,
    review_pack: dict[str, Any],
    review_decision_artifact: dict[str, Any],
) -> dict[str, Any]:
    candidate_ids = _candidate_ids_from_review_pack(review_pack)
    decisions = [
        dict(decision)
        for decision in list(review_decision_artifact.get("decisions") or [])
        if isinstance(decision, dict)
    ]
    blockers = _proposal_blockers(
        candidate_ids=candidate_ids,
        review_decision_artifact=review_decision_artifact,
        decisions=decisions,
    )
    approved_candidates = [] if blockers else [
        _proposal_item(decision) for decision in decisions if _disposition(decision) == "approve"
    ]
    status = "blocked" if blockers else "valid_promotion_blocked_proposal"
    return {
        "artifact_schema_version": "1.0",
        "artifact_type": "accurate_intake_food_evidence_approved_batch_proposal",
        "status": status,
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "claim_scope": "approved_food_evidence_batch_proposal_no_truth_promotion",
        "source_artifacts": {
            "review_pack": str(review_pack.get("artifact_type") or "unknown"),
            "review_decision_artifact": str(
                review_decision_artifact.get("artifact_type") or "unknown"
            ),
        },
        "proposal_policy": {
            "truth_owner": "human_reviewer_then_explicit_promotion_slice",
            "deterministic_role": "package_approved_metadata_and_fail_closed_only",
            "proposal_success_promotes_truth": False,
            "food_gap_candidate_can_create_truth": False,
        },
        "promotion_blocked_by_default": True,
        "summary": _summary(decisions, blockers),
        "blockers": blockers,
        "approved_candidates": approved_candidates,
        "excluded_decisions": [
            {
                "candidate_id": _candidate_id(decision),
                "disposition": _disposition(decision),
            }
            for decision in decisions
            if _disposition(decision) in {"reject", "defer"}
        ],
        "non_claims": list(_PROPOSAL_NON_CLAIMS),
        "food_kb_truth_updated": False,
        "nutrition_seed_created": False,
        "exact_card_created": False,
        "packet_truth_created": False,
        "runtime_truth_changed": False,
        "canonical_eval_promoted": False,
        "manager_or_appshell_behavior_changed": False,
        "mutation_authority": False,
    }


def _proposal_blockers(
    *,
    candidate_ids: set[str],
    review_decision_artifact: dict[str, Any],
    decisions: list[dict[str, Any]],
) -> list[str]:
    blockers: list[str] = []
    if review_decision_artifact.get("status") != "valid_review_metadata":
        blockers.append("review_decision_artifact_not_valid")
    if list(review_decision_artifact.get("blockers") or []):
        blockers.append("review_decision_artifact_has_blockers")
    if not _REQUIRED_DECISION_NON_CLAIMS.issubset(
        {str(item) for item in list(review_decision_artifact.get("non_claims") or [])}
    ):
        blockers.append("artifact_missing_non_claims")
    if bool(review_decision_artifact.get("runtime_truth_changed")):
        blockers.append("runtime_truth_claim_present")
    if bool(review_decision_artifact.get("food_kb_truth_updated")):
        blockers.append("food_kb_truth_claim_present")
    if bool(review_decision_artifact.get("packet_truth_created")):
        blockers.append("packet_truth_claim_present")

    for decision in decisions:
        candidate_id = _candidate_id(decision) or "missing"
        if bool(decision.get("runtime_truth_allowed")):
            blockers.append(f"runtime_truth_allowed_claim:{candidate_id}")
        if bool(decision.get("promotion_allowed_by_validator")):
            blockers.append(f"validator_promotion_claim:{candidate_id}")
        if str(decision.get("promotion_stage") or "") in _FORBIDDEN_PROMOTION_STAGES:
            blockers.append(f"promotion_stage_claims_runtime_truth:{candidate_id}")
        if _disposition(decision) == "approve":
            blockers.extend(_approved_decision_blockers(candidate_id, decision, candidate_ids))
    return _dedup(blockers)


def _approved_decision_blockers(
    candidate_id: str,
    decision: dict[str, Any],
    candidate_ids: set[str],
) -> list[str]:
    blockers: list[str] = []
    if candidate_id not in candidate_ids:
        blockers.append(f"approved_candidate_not_in_review_pack:{candidate_id}")
    if not str(decision.get("source_class") or "").strip():
        blockers.append(f"approved_candidate_missing_source_class:{candidate_id}")
    provenance = _dict(decision.get("source_provenance_decision"))
    source_refs = [str(item) for item in list(provenance.get("source_refs") or []) if str(item)]
    if provenance.get("complete") is not True or not source_refs:
        blockers.append(f"approved_candidate_missing_provenance:{candidate_id}")
    serving = _dict(decision.get("serving_portion_decision"))
    if not str(serving.get("serving_basis") or "").strip():
        blockers.append(f"approved_candidate_missing_serving_basis:{candidate_id}")
    kcal = _dict(decision.get("kcal_decision"))
    if kcal.get("kcal_point") is None and not list(kcal.get("kcal_range") or []):
        blockers.append(f"approved_candidate_missing_kcal_decision:{candidate_id}")
    macro = _dict(decision.get("macro_decision"))
    visibility = str(macro.get("macro_visibility_decision") or "").strip()
    null_reason = str(macro.get("macro_null_reason") or "").strip()
    if not visibility or (visibility == "macro_null_allowed" and not null_reason):
        blockers.append(f"approved_candidate_missing_macro_visibility_or_null_reason:{candidate_id}")
    return blockers


def _proposal_item(decision: dict[str, Any]) -> dict[str, Any]:
    provenance = _dict(decision.get("source_provenance_decision"))
    return {
        "candidate_id": _candidate_id(decision),
        "source_class": str(decision.get("source_class") or ""),
        "source_provenance_refs": [
            str(item) for item in list(provenance.get("source_refs") or []) if str(item)
        ],
        "serving_portion_decision": _dict(decision.get("serving_portion_decision")),
        "kcal_decision": _dict(decision.get("kcal_decision")),
        "macro_decision": _dict(decision.get("macro_decision")),
        "promotion_stage": str(decision.get("promotion_stage") or "review_metadata_only"),
        "review_note": str(decision.get("review_note") or ""),
        "runtime_truth_allowed": False,
        "promotion_allowed_by_proposal": False,
        "promotion_blocked_by_default": True,
    }


def _summary(decisions: list[dict[str, Any]], blockers: list[str]) -> dict[str, int]:
    return {
        "approved_candidate_count": _decision_count(decisions, "approve"),
        "rejected_candidate_count": _decision_count(decisions, "reject"),
        "deferred_candidate_count": _decision_count(decisions, "defer"),
        "blocked_candidate_count": len(blockers),
    }


def _candidate_ids_from_review_pack(review_pack: dict[str, Any]) -> set[str]:
    packets = [p for p in list(review_pack.get("review_packets") or []) if isinstance(p, dict)]
    candidates = [
        c for packet in packets for c in list(packet.get("candidates") or []) if isinstance(c, dict)
    ]
    return {str(c.get("candidate_id") or "").strip() for c in candidates if c.get("candidate_id")}


def _candidate_id(decision: dict[str, Any]) -> str:
    return str(decision.get("candidate_id") or "").strip()


def _disposition(decision: dict[str, Any]) -> str:
    return str(decision.get("disposition") or "").strip()


def _dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _decision_count(decisions: list[dict[str, Any]], disposition: str) -> int:
    return sum(1 for decision in decisions if _disposition(decision) == disposition)


def _dedup(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))

__all__ = ["build_food_evidence_approved_batch_proposal"]
