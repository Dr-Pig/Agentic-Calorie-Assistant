from __future__ import annotations

from typing import Any, Mapping


REQUIRED_MILESTONE_ARTIFACTS = {
    "grokfast_extraction_diagnostic": [
        "advanced_product_lab_memory_record_grokfast_extraction_diagnostic"
    ],
    "memory_tool_lookup_diagnostic": [
        "advanced_product_lab_memory_tool_lookup_live_diagnostic"
    ],
    "recommendation_with_blockers": [
        "advanced_product_lab_recommendation_blocker_live_diagnostic"
    ],
    "rescue_memory_context_diagnostic": [
        "advanced_product_lab_rescue_memory_context_live_diagnostic"
    ],
    "proactive_feedback_projection": [
        "advanced_product_lab_proactive_feedback_live_diagnostic"
    ],
    "integrated_e2e_lab_loop": ["advanced_product_lab_integrated_live_e2e"],
}
REQUIRED_MILESTONE_CASE_SUITES = {"grokfast_extraction_diagnostic": "golden"}
SUPPORTING_LIVE_DIAGNOSTICS = {
    "negative_preference_holdout": (
        "advanced_product_lab_memory_record_grokfast_extraction_diagnostic",
        "negative_holdout",
    ),
    "source_safety_holdout": ("advanced_product_lab_memory_source_safety_holdout", ""),
    "memory_feedback_projection": (
        "advanced_product_lab_memory_feedback_live_diagnostic",
        "",
    ),
}
NON_CLAIMS = [
    "not_mainline_runtime_activation",
    "not_self_use_v1_activation",
    "not_production_scheduler_delivery",
    "not_canonical_mutation",
    "not_durable_product_memory",
    "not_kimi_live_diagnostic",
]


def live_edd_milestone_statuses(
    *,
    pr_train: Mapping[str, Any],
    diagnostic_artifacts: list[Mapping[str, Any]],
    failure_taxonomy_report: Mapping[str, Any],
    activation_wall_audit: Mapping[str, Any],
) -> dict[str, str]:
    statuses: dict[str, str] = {}
    for milestone_id in _milestone_ids(pr_train):
        if milestone_id == "failure_taxonomy_and_decision_pack":
            statuses[milestone_id] = _report_wall_status(
                failure_taxonomy_report, activation_wall_audit
            )
            continue
        statuses[milestone_id] = _best_live_status(
            diagnostic_artifacts,
            REQUIRED_MILESTONE_ARTIFACTS.get(milestone_id, []),
            case_suite=REQUIRED_MILESTONE_CASE_SUITES.get(milestone_id, ""),
        )
    return statuses


def supporting_diagnostic_statuses(
    diagnostic_artifacts: list[Mapping[str, Any]],
) -> dict[str, str]:
    return {
        support_id: _best_live_status(
            diagnostic_artifacts,
            [artifact_type],
            case_suite=case_suite,
        )
        for support_id, (artifact_type, case_suite) in SUPPORTING_LIVE_DIAGNOSTICS.items()
    }


def failure_taxonomy_summary(report: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "status": str(report.get("status") or ""),
        "failure_count": int(report.get("failure_count") or 0),
        "unclassified_failure_count": int(report.get("unclassified_failure_count") or 0),
        "semantic_hardening_allowed": report.get("semantic_hardening_allowed") is True,
    }


def wall_regression_summary(audit: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "status": str(audit.get("status") or ""),
        "route_mount_clear": audit.get("route_mount_clear") is True,
        "scheduler_delivery_clear": audit.get("scheduler_delivery_clear") is True,
        "production_db_migration_clear": audit.get("production_db_migration_clear") is True,
        "provider_default_runtime_clear": audit.get("provider_default_runtime_clear") is True,
    }


def next_allowed_slices(status: str) -> list[str]:
    if status != "pass":
        return []
    return [
        "operator_dogfood_trace_collection",
        "activation_plan_pr_after_explicit_human_approval",
    ]


def _milestone_ids(pr_train: Mapping[str, Any]) -> list[str]:
    return [
        str(item.get("milestone_id") or "")
        for item in pr_train.get("live_edd_milestones") or []
        if isinstance(item, Mapping)
    ]


def _report_wall_status(
    failure_taxonomy_report: Mapping[str, Any],
    activation_wall_audit: Mapping[str, Any],
) -> str:
    if failure_taxonomy_report.get("status") == "pass" and activation_wall_audit.get(
        "status"
    ) == "pass":
        return "satisfied_report_and_wall"
    return "blocked_report_or_wall"


def _best_live_status(
    artifacts: list[Mapping[str, Any]],
    artifact_types: list[str],
    *,
    case_suite: str = "",
) -> str:
    observed: list[str] = []
    for artifact in artifacts:
        if artifact.get("artifact_type") not in artifact_types:
            continue
        if case_suite and artifact.get("case_suite") != case_suite:
            continue
        status = str(artifact.get("live_milestone_status") or "")
        observed.append(status)
        if _satisfied_live_grokfast(artifact, status):
            return "satisfied_live_grokfast"
    return observed[0] if observed else "missing"


def _satisfied_live_grokfast(artifact: Mapping[str, Any], status: str) -> bool:
    return (
        artifact.get("status") == "pass"
        and artifact.get("diagnostic_evidence_class") == "live_grokfast"
        and status == "satisfied_live_grokfast"
    )
