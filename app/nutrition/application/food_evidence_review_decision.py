from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

_ALLOWED_DISPOSITIONS = {"approve", "reject", "defer"}
_REQUIRED_NON_CLAIMS = {
    "no_fooddb_truth_promoted",
    "no_runtime_truth_changed",
    "no_anchor_update",
    "no_packet_truth_created",
    "no_manager_or_appshell_behavior_change",
    "no_eval_oracle_created",
    "no_mutation_authority",
}
_FORBIDDEN_PROMOTION_STAGES = {
    "runtime_truth",
    "packet_truth",
    "anchor_update",
    "exact_card_runtime_truth",
    "eval_oracle",
}


def build_food_evidence_review_decision_artifact(
    *,
    review_pack: dict[str, Any],
    decision_payload: dict[str, Any],
) -> dict[str, Any]:
    candidate_ids = _candidate_ids_from_review_pack(review_pack)
    decisions = [
        _normalized_decision(decision)
        for decision in list(decision_payload.get("decisions") or [])
        if isinstance(decision, dict)
    ]
    blockers = _validate_decisions(
        candidate_ids=candidate_ids,
        decisions=decisions,
        non_claims=list(decision_payload.get("non_claims") or []),
    )
    return {
        "artifact_schema_version": "1.0",
        "artifact_type": "accurate_intake_food_evidence_human_review_decision",
        "status": "blocked" if blockers else "valid_review_metadata",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "claim_scope": "human_review_metadata_only",
        "source_artifacts": {
            "review_pack": str(review_pack.get("artifact_type") or "unknown"),
            "decision_payload": str(decision_payload.get("artifact_type") or "unknown"),
        },
        "reviewer_id": _required_text(decision_payload.get("reviewer_id"), "unknown_reviewer"),
        "reviewed_at_utc": _required_text(decision_payload.get("reviewed_at_utc"), "unknown"),
        "review_policy": {
            "truth_owner": "human_reviewer",
            "deterministic_role": "validate_shape_refs_and_non_claims_only",
            "validator_success_promotes_truth": False,
            "food_gap_candidate_can_create_truth": False,
        },
        "summary": _summary(decisions, blockers),
        "blockers": blockers,
        "decisions": decisions,
        "non_claims": list(_REQUIRED_NON_CLAIMS),
        "food_kb_truth_updated": False,
        "nutrition_seed_created": False,
        "exact_card_created": False,
        "packet_truth_created": False,
        "runtime_truth_changed": False,
        "canonical_eval_promoted": False,
        "manager_or_appshell_behavior_changed": False,
        "mutation_authority": False,
    }


def _candidate_ids_from_review_pack(review_pack: dict[str, Any]) -> set[str]:
    candidate_ids: set[str] = set()
    for packet in list(review_pack.get("review_packets") or []):
        if not isinstance(packet, dict):
            continue
        for candidate in list(packet.get("candidates") or []):
            if isinstance(candidate, dict):
                candidate_id = str(candidate.get("candidate_id") or "").strip()
                if candidate_id:
                    candidate_ids.add(candidate_id)
    return candidate_ids


def _normalized_decision(decision: dict[str, Any]) -> dict[str, Any]:
    candidate_id = _required_text(decision.get("candidate_id"), "")
    return {
        "candidate_id": candidate_id,
        "disposition": _required_text(decision.get("disposition"), ""),
        "source_class": _required_text(decision.get("source_class"), ""),
        "source_provenance_decision": _json_safe(decision.get("source_provenance_decision") or {}),
        "serving_portion_decision": _json_safe(decision.get("serving_portion_decision") or {}),
        "kcal_decision": _json_safe(decision.get("kcal_decision") or {}),
        "macro_decision": _json_safe(decision.get("macro_decision") or {}),
        "promotion_stage": _required_text(
            decision.get("promotion_stage"),
            "review_metadata_only",
        ),
        "review_note": _required_text(decision.get("review_note"), ""),
        "runtime_truth_allowed": False,
        "promotion_allowed_by_validator": False,
    }


def _validate_decisions(
    *,
    candidate_ids: set[str],
    decisions: list[dict[str, Any]],
    non_claims: list[Any],
) -> list[str]:
    blockers: list[str] = []
    if not _REQUIRED_NON_CLAIMS.issubset({str(item) for item in non_claims}):
        blockers.append("artifact_missing_non_claims")
    for decision in decisions:
        candidate_id = str(decision.get("candidate_id") or "")
        if candidate_id not in candidate_ids:
            blockers.append(f"unknown_candidate_id:{candidate_id or 'missing'}")
        if decision.get("disposition") not in _ALLOWED_DISPOSITIONS:
            blockers.append(f"invalid_disposition:{candidate_id or 'missing'}")
        provenance = _dict(decision.get("source_provenance_decision"))
        if provenance.get("complete") is not True or not list(provenance.get("source_refs") or []):
            blockers.append(f"missing_provenance_decision:{candidate_id or 'missing'}")
        macro = _dict(decision.get("macro_decision"))
        visibility = str(macro.get("macro_visibility_decision") or "").strip()
        null_reason = str(macro.get("macro_null_reason") or "").strip()
        if not visibility or (visibility == "macro_null_allowed" and not null_reason):
            blockers.append(f"missing_macro_visibility_or_null_reason:{candidate_id or 'missing'}")
        if str(decision.get("promotion_stage") or "") in _FORBIDDEN_PROMOTION_STAGES:
            blockers.append(f"promotion_stage_claims_runtime_truth:{candidate_id or 'missing'}")
    return blockers


def _summary(decisions: list[dict[str, Any]], blockers: list[str]) -> dict[str, int]:
    return {
        "decision_count": len(decisions),
        "approved_count": sum(1 for decision in decisions if decision["disposition"] == "approve"),
        "rejected_count": sum(1 for decision in decisions if decision["disposition"] == "reject"),
        "deferred_count": sum(1 for decision in decisions if decision["disposition"] == "defer"),
        "invalid_count": len(blockers),
    }


def _required_text(value: Any, default: str) -> str:
    text = str(value or "").strip()
    return text or default


def _dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


__all__ = ["build_food_evidence_review_decision_artifact"]
