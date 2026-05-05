from __future__ import annotations

from datetime import UTC, datetime
import hashlib
from typing import Any

from app.nutrition.application.websearch_exact_card_runtime_promotion_policy import (
    evaluate_websearch_exact_card_runtime_promotion_request,
)


def build_websearch_exact_card_candidate_manifest_diagnostic(
    *,
    runtime_promotion_policy: dict[str, Any],
    promotion_requests: list[dict[str, Any]],
) -> dict[str, Any]:
    blockers: list[str] = []
    if not isinstance(promotion_requests, list):
        blockers.append("manifest_promotion_requests_not_list")
    elif not promotion_requests:
        blockers.append("manifest_promotion_request_missing")
    elif any(not isinstance(request, dict) for request in promotion_requests):
        blockers.append("manifest_promotion_request_malformed")
    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    if not blockers:
        for request in promotion_requests:
            result = evaluate_websearch_exact_card_runtime_promotion_request(
                policy_artifact=runtime_promotion_policy,
                request=request,
            )
            if result["policy_allows_future_manifest_entry"] is True:
                accepted.append(_manifest_candidate(request=request, result=result))
            else:
                rejected.append(_rejected_request(request=request, result=result))
                for blocker in result["blockers"]:
                    if str(blocker).startswith("policy_artifact_"):
                        blockers.append(str(blocker))
                    blockers.append(f"request_blocked:{blocker}")
    blockers.extend(_manifest_candidate_blockers(accepted))
    clear = not blockers
    return {
        "artifact_type": (
            "accurate_intake_websearch_exact_card_candidate_manifest_diagnostic_v1"
        ),
        "artifact_schema_version": "1.0",
        "generated_at_utc": _now(),
        "track": "FDB",
        "classification": (
            "deterministic_exact_card_candidate_manifest_diagnostic_only"
        ),
        "claim_scope": "websearch_exact_card_candidate_manifest_without_truth",
        "status": "pass_candidate_manifest_diagnostic" if clear else "blocked",
        "blockers": sorted(set(blockers)),
        "runtime_truth_changed": False,
        "mutation_changed": False,
        "runtime_mutation_allowed": False,
        "websearch_runtime_truth_allowed": False,
        "runtime_web_activation_approved": False,
        "runtime_web_activation_recommended": False,
        "manager_context_changed": False,
        "packetizer_format_changed": False,
        "shared_contract_changed": False,
        "live_provider_used": False,
        "live_websearch_used": False,
        "readiness_claimed": False,
        "exact_card_created": False,
        "source_artifacts": {
            "runtime_promotion_policy_type": runtime_promotion_policy.get(
                "artifact_type"
            ),
        },
        "manifest_candidates": [] if blockers else accepted,
        "rejected_requests": rejected,
        "summary": {
            "promotion_request_count": (
                len(promotion_requests) if isinstance(promotion_requests, list) else 0
            ),
            "manifest_candidate_count": 0 if blockers else len(accepted),
            "rejected_request_count": len(rejected),
            "runtime_truth_allowed_count": 0,
            "exact_card_created_count": 0,
            "promotion_allowed_count": 0,
        },
        "next_required_slice": (
            "websearch_exact_card_manifest_candidate_review_packet"
            if clear
            else "inspect_websearch_exact_card_candidate_manifest_blockers"
        ),
        "non_claims": [
            "no_websearch_runtime_truth",
            "no_exact_card_truth_promotion",
            "no_runtime_mutation",
            "no_live_websearch_call",
            "no_live_provider_call",
            "no_readiness_claim",
        ],
    }


def _manifest_candidate(*, request: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    return {
        "manifest_candidate_id": _candidate_id(request),
        "source_request_candidate_id": request.get("candidate_id"),
        "candidate_role": "exact_card_manifest_candidate_only",
        "truth_level": "manifest_candidate",
        "source_class": request.get("source_class"),
        "approval_id": request.get("approval_id"),
        "policy_result_next_required_slice": result.get("next_required_slice"),
        "runtime_truth_allowed": False,
        "websearch_runtime_truth_allowed": False,
        "packet_ready_truth_allowed": False,
        "promotion_allowed": False,
        "exact_card_created": False,
        "runtime_mutation_allowed": False,
        "raw_content_included": False,
        "raw_source_rows_included": False,
        "manager_visible_role": "candidate_manifest_only_not_manager_truth",
        "required_before_runtime_truth": [
            "exact_card_record_creation_slice",
            "exact_card_runtime_gate",
            "packetizer_contract_review",
        ],
    }


def _rejected_request(*, request: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    return {
        "candidate_id": request.get("candidate_id"),
        "requested_transition": request.get("requested_transition"),
        "source_class": request.get("source_class"),
        "blockers": result["blockers"],
        "runtime_truth_allowed": False,
        "exact_card_created": False,
    }


def _manifest_candidate_blockers(candidates: list[dict[str, Any]]) -> list[str]:
    blockers: list[str] = []
    for candidate in candidates:
        if candidate.get("runtime_truth_allowed") is not False:
            blockers.append("manifest_candidate_allowed_runtime_truth")
        if candidate.get("websearch_runtime_truth_allowed") is not False:
            blockers.append("manifest_candidate_allowed_websearch_runtime_truth")
        if candidate.get("packet_ready_truth_allowed") is not False:
            blockers.append("manifest_candidate_allowed_packet_ready_truth")
        if candidate.get("promotion_allowed") is not False:
            blockers.append("manifest_candidate_allowed_promotion")
        if candidate.get("exact_card_created") is not False:
            blockers.append("manifest_candidate_created_exact_card")
        if candidate.get("runtime_mutation_allowed") is not False:
            blockers.append("manifest_candidate_allowed_runtime_mutation")
        if candidate.get("raw_content_included") is not False:
            blockers.append("manifest_candidate_included_raw_content")
        if candidate.get("raw_source_rows_included") is not False:
            blockers.append("manifest_candidate_included_raw_source_rows")
    return sorted(set(blockers))


def _candidate_id(request: dict[str, Any]) -> str:
    seed = "|".join(
        str(request.get(key) or "")
        for key in ("candidate_id", "source_class", "approval_id")
    )
    digest = hashlib.sha1(seed.encode("utf-8")).hexdigest()[:12]
    return f"exact_card_manifest_candidate_{digest}"


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


__all__ = ["build_websearch_exact_card_candidate_manifest_diagnostic"]
