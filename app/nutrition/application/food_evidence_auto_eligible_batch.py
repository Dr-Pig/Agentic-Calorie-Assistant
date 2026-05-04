from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.nutrition.application.food_evidence_candidate_normalization import NO_TRUTH_FLAGS


POLICY_VERSION = "food_evidence_mvp_auto_eligible_v1"
AUTO_ELIGIBLE_SOURCE_ROLE_PAIRS = {
    ("taiwan_tfda_open_data", "generic_anchor_candidate"),
    ("taiwan_tfda_open_data", "listed_component_anchor_candidate"),
    ("official_brand_chain_page", "exact_card_candidate"),
}


def build_food_evidence_auto_eligible_batch(
    *,
    validation_artifact: dict[str, Any],
    sample_size_per_group: int = 10,
) -> dict[str, Any]:
    auto_eligible: list[dict[str, Any]] = []
    exceptions: list[dict[str, Any]] = []

    for candidate in list(validation_artifact.get("validated_candidates") or []):
        if not isinstance(candidate, dict):
            continue
        reason = _exception_reason(candidate)
        if reason:
            exceptions.append(_exception(candidate, reason))
            continue
        auto_eligible.append(_auto_eligible_candidate(candidate))

    return {
        "artifact_type": "accurate_intake_food_auto_eligible_candidate_batch",
        "artifact_schema_version": "1.0",
        "generated_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "claim_scope": "food_evidence_auto_eligible_candidates_only",
        "truth_owner": "none",
        "semantic_owner": "none",
        "runtime_truth": False,
        **NO_TRUTH_FLAGS,
        "pipeline_stage_boundary": {
            "implemented_stage": "auto_eligible_packet_candidate",
            "next_stages_not_implemented": ["packet_ready"],
            "stop_gate_before_next_stage": "PR121 requires human approval of batch policy, exceptions, and sample audit",
        },
        "approval_policy": {
            "policy_version": POLICY_VERSION,
            "approval_mode": "batch_policy_pending",
            "validator_passed_is_sufficient_for_packet_ready": False,
            "runtime_truth_allowed_by_default": False,
            "requires_pr121_before_packet_ready": True,
        },
        "summary": {
            "validated_candidate_count": len(list(validation_artifact.get("validated_candidates") or [])),
            "auto_eligible_count": len(auto_eligible),
            "exception_count": len(exceptions),
            "sample_audit_group_count": len(
                _sample_audit_report(auto_eligible, sample_size_per_group)
            ),
        },
        "auto_eligible_candidates": auto_eligible,
        "exception_report": exceptions,
        "sample_audit_report": _sample_audit_report(auto_eligible, sample_size_per_group),
        "source_validation_summary": validation_artifact.get("summary") or {},
        "pr110_coverage_report": validation_artifact.get("pr110_coverage_report") or {},
    }


def _exception_reason(candidate: dict[str, Any]) -> str | None:
    if candidate.get("validation_status") != "validator_passed":
        return "validation_not_passed"
    pair = (str(candidate.get("source_class") or ""), str(candidate.get("evidence_role") or ""))
    if pair not in AUTO_ELIGIBLE_SOURCE_ROLE_PAIRS:
        return "source_class_not_auto_eligible"
    return None


def _auto_eligible_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    return {
        "candidate_id": str(candidate.get("candidate_id") or ""),
        "source_id": str(candidate.get("source_id") or ""),
        "source_class": str(candidate.get("source_class") or ""),
        "evidence_role": str(candidate.get("evidence_role") or ""),
        "canonical_label": str(candidate.get("canonical_label") or ""),
        "aliases": list(candidate.get("aliases") or []),
        "kcal_point": candidate.get("kcal_point"),
        "validation_status": "validator_passed",
        "promotion_status": "auto_eligible_packet_candidate",
        "runtime_truth_allowed": False,
        "packet_ready": False,
        "approval_metadata": _approval_metadata(),
    }


def _exception(candidate: dict[str, Any], reason: str) -> dict[str, Any]:
    return {
        "candidate_id": str(candidate.get("candidate_id") or ""),
        "source_id": str(candidate.get("source_id") or ""),
        "source_class": str(candidate.get("source_class") or ""),
        "evidence_role": str(candidate.get("evidence_role") or ""),
        "canonical_label": str(candidate.get("canonical_label") or ""),
        "validation_status": str(candidate.get("validation_status") or ""),
        "validation_reasons": list(candidate.get("validation_reasons") or []),
        "exception_reason": reason,
        "runtime_truth_allowed": False,
        "packet_ready": False,
    }


def _approval_metadata() -> dict[str, Any]:
    return {
        "approval_mode": "batch_policy_pending",
        "approval_scope": "source_class_and_semantic_role_batch",
        "policy_version": POLICY_VERSION,
        "approved_by": None,
        "approved_at": None,
        "runtime_truth_allowed": False,
    }


def _sample_audit_report(
    auto_eligible: list[dict[str, Any]],
    sample_size_per_group: int,
) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for candidate in auto_eligible:
        group = f"{candidate['source_class']}/{candidate['evidence_role']}"
        groups.setdefault(group, []).append(candidate)
    report = []
    for group in sorted(groups):
        samples = groups[group][: max(sample_size_per_group, 0)]
        report.append(
            {
                "sample_group": group,
                "available_count": len(groups[group]),
                "sample_size": len(samples),
                "sample_only_not_approved": True,
                "approval_granted": False,
                "samples": [
                    {
                        "candidate_id": sample["candidate_id"],
                        "canonical_label": sample["canonical_label"],
                        "source_id": sample["source_id"],
                        "kcal_point": sample["kcal_point"],
                        "runtime_truth_allowed": False,
                    }
                    for sample in samples
                ],
            }
        )
    return report


__all__ = ["build_food_evidence_auto_eligible_batch"]
