from __future__ import annotations

from typing import Any


NO_CLAIMS = [
    "no_packet_truth_claim",
    "no_runtime_truth_claim",
    "no_shared_contract_change",
    "no_live_provider_call",
    "report_only",
]

COVERAGE_STOP_RULE = {
    "common_serving_anchor_max_before_activation": 80,
    "listed_basket_components_max_before_activation": 60,
}


def build_food_evidence_candidate_triage_report(
    *,
    validation_artifact: dict[str, Any],
    auto_eligible_artifact: dict[str, Any],
) -> dict[str, Any]:
    validated_candidates = _validated_candidates(validation_artifact)
    auto_eligible_candidates = _auto_eligible_candidates(auto_eligible_artifact)

    tfda_generic_candidates = _filter_candidates(
        auto_eligible_candidates,
        source_class="taiwan_tfda_open_data",
        evidence_role="generic_anchor_candidate",
    )
    tfda_listed_component_candidates = _filter_candidates(
        auto_eligible_candidates,
        source_class="taiwan_tfda_open_data",
        evidence_role="listed_component_anchor_candidate",
    )
    official_exact_candidates = _filter_candidates(
        auto_eligible_candidates,
        source_class="official_brand_chain_page",
        evidence_role="exact_card_candidate",
    )
    local_packaged_exact_candidates = _filter_validated_candidates(
        validated_candidates,
        source_class="local_taiwan_packaged_extract",
        evidence_role="exact_card_candidate",
    )
    repair_candidates = [
        candidate
        for candidate in validated_candidates
        if candidate.get("validation_status") == "needs_source_repair"
    ]
    rejected_candidates = [
        candidate
        for candidate in validated_candidates
        if candidate.get("validation_status") == "rejected"
    ]

    source_repair_clusters = _source_repair_cluster_summary(
        list(validation_artifact.get("source_repair_report") or [])
    )

    return {
        "artifact_type": "accurate_intake_food_candidate_triage_report",
        "artifact_schema_version": "1.0",
        "generated_at_utc": None,
        "claim_scope": "food_candidate_triage_report_only",
        "track": "FDB",
        "runtime_truth_changed": False,
        "packet_truth_changed": False,
        "shared_contract_changed": False,
        "live_provider_used": False,
        "coverage_stop_rule": COVERAGE_STOP_RULE,
        "validation_summary_compact": _compact_summary(validation_artifact.get("summary") or {}),
        "auto_eligible_summary_compact": _compact_summary(
            auto_eligible_artifact.get("summary") or {}
        ),
        "auto_eligible_group_counts": _group_counts(auto_eligible_candidates),
        "summary": {
            "tfda_generic_auto_eligible_count": len(tfda_generic_candidates),
            "tfda_listed_component_auto_eligible_count": len(tfda_listed_component_candidates),
            "official_exact_candidate_only_count": len(official_exact_candidates),
            "local_packaged_exact_candidate_only_count": len(local_packaged_exact_candidates),
            "source_repair_required_count": len(repair_candidates),
            "rejected_count": len(rejected_candidates),
        },
        "lane_map": {
            "tfda_generic_runtime_batch_candidates": {
                "lane_kind": "runtime_batch_candidate",
                "lane_count": len(tfda_generic_candidates),
                "candidate_ids": [candidate["candidate_id"] for candidate in tfda_generic_candidates],
                "runtime_truth_allowed": False,
                "next_action": "runtime-batch-plan",
                "records": tfda_generic_candidates,
            },
            "tfda_listed_component_runtime_batch_candidates": {
                "lane_kind": "runtime_batch_candidate",
                "lane_count": len(tfda_listed_component_candidates),
                "candidate_ids": [
                    candidate["candidate_id"] for candidate in tfda_listed_component_candidates
                ],
                "runtime_truth_allowed": False,
                "next_action": "listed-component-runtime-batch-plan",
                "records": tfda_listed_component_candidates,
            },
            "official_exact_candidate_only": {
                "lane_kind": "candidate_only",
                "lane_count": len(official_exact_candidates),
                "candidate_ids": [candidate["candidate_id"] for candidate in official_exact_candidates],
                "runtime_truth_allowed": False,
                "next_action": "exact-candidate-review",
                "records": official_exact_candidates,
            },
            "local_packaged_exact_candidate_only": {
                "lane_kind": "candidate_only",
                "lane_count": len(local_packaged_exact_candidates),
                "candidate_ids": [
                    candidate["candidate_id"] for candidate in local_packaged_exact_candidates
                ],
                "runtime_truth_allowed": False,
                "next_action": "local-packaged-exact-candidate-review",
                "records": local_packaged_exact_candidates,
            },
            "source_repair_required": {
                "lane_kind": "repair",
                "lane_count": len(repair_candidates),
                "candidate_ids": [candidate["candidate_id"] for candidate in repair_candidates],
                "source_ids": [
                    source_id
                    for repair_cluster in source_repair_clusters.get("clusters", [])
                    for source_id in repair_cluster.get("source_ids") or []
                ],
                "next_action": "source-repair",
                "records": repair_candidates,
            },
            "rejected": {
                "lane_kind": "rejected",
                "lane_count": len(rejected_candidates),
                "candidate_ids": [candidate["candidate_id"] for candidate in rejected_candidates],
                "next_action": "do-not-promote",
                "records": rejected_candidates,
            },
        },
        "source_repair_cluster_summary": source_repair_clusters,
        "non_claims": NO_CLAIMS,
    }


def _validated_candidates(validation_artifact: dict[str, Any]) -> list[dict[str, Any]]:
    return [candidate for candidate in validation_artifact.get("validated_candidates") or [] if isinstance(candidate, dict)]


def _auto_eligible_candidates(auto_eligible_artifact: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        candidate
        for candidate in auto_eligible_artifact.get("auto_eligible_candidates") or []
        if isinstance(candidate, dict)
    ]


def _filter_candidates(
    candidates: list[dict[str, Any]],
    *,
    source_class: str,
    evidence_role: str,
) -> list[dict[str, Any]]:
    filtered = [
        candidate
        for candidate in candidates
        if candidate.get("source_class") == source_class and candidate.get("evidence_role") == evidence_role
    ]
    return [_compact_candidate(candidate) for candidate in filtered]


def _filter_validated_candidates(
    candidates: list[dict[str, Any]],
    *,
    source_class: str,
    evidence_role: str,
) -> list[dict[str, Any]]:
    filtered = [
        candidate
        for candidate in candidates
        if candidate.get("validation_status") == "validator_passed"
        and candidate.get("source_class") == source_class
        and candidate.get("evidence_role") == evidence_role
    ]
    return [_compact_candidate(candidate) for candidate in filtered]


def _compact_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    return {
        "candidate_id": str(candidate.get("candidate_id") or ""),
        "source_id": str(candidate.get("source_id") or ""),
        "source_class": str(candidate.get("source_class") or ""),
        "evidence_role": str(candidate.get("evidence_role") or ""),
        "canonical_label": str(candidate.get("canonical_label") or ""),
        "validation_status": str(candidate.get("validation_status") or ""),
        "promotion_status": str(candidate.get("promotion_status") or ""),
        "runtime_truth_allowed": bool(candidate.get("runtime_truth_allowed") is True),
    }


def _group_counts(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], int] = {}
    for candidate in candidates:
        key = (str(candidate.get("source_class") or ""), str(candidate.get("evidence_role") or ""))
        grouped[key] = grouped.get(key, 0) + 1
    return [
        {
            "source_class": source_class,
            "evidence_role": evidence_role,
            "count": grouped[(source_class, evidence_role)],
        }
        for source_class, evidence_role in sorted(grouped)
    ]


def _compact_summary(summary: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "candidate_count",
        "validator_passed_count",
        "rejected_count",
        "needs_source_repair_count",
        "source_parse_error_count",
        "validated_candidate_count",
        "auto_eligible_count",
        "exception_count",
        "sample_audit_group_count",
    )
    compact = {key: summary[key] for key in keys if key in summary}
    return compact


def _source_repair_cluster_summary(source_repair_report: list[dict[str, Any]]) -> dict[str, Any]:
    clusters: dict[str, dict[str, Any]] = {}
    for item in source_repair_report:
        reason = str(item.get("reason") or "")
        cluster_name = reason.split(":", 1)[0] if reason else "unknown"
        cluster = clusters.setdefault(
            cluster_name,
            {
                "repair_cluster": cluster_name,
                "count": 0,
                "source_ids": [],
                "source_repair_reason": reason,
            },
        )
        cluster["count"] += 1
        source_id = str(item.get("source_id") or "")
        if source_id and source_id not in cluster["source_ids"]:
            cluster["source_ids"].append(source_id)
        if not cluster["source_repair_reason"]:
            cluster["source_repair_reason"] = reason
    return {
        "cluster_count": len(clusters),
        "clusters": [clusters[key] for key in sorted(clusters)],
    }


__all__ = ["build_food_evidence_candidate_triage_report"]
