from __future__ import annotations

from typing import Any, Mapping


CLAIM_FALSE_FIELDS = [
    "mainline_activation_enabled",
    "mainline_runtime_connected",
    "self_use_v1_affected",
    "durable_product_memory_written",
    "canonical_product_mutation_allowed",
    "production_scheduler_delivery_allowed",
    "production_db_migration_allowed",
]


def build_blockers(
    *,
    pr_train: Mapping[str, Any],
    diagnostic_artifacts: list[Mapping[str, Any]],
    failure_taxonomy_report: Mapping[str, Any],
    activation_wall_audit: Mapping[str, Any],
    milestone_statuses: Mapping[str, str],
    supporting_statuses: Mapping[str, str],
) -> list[str]:
    return [
        *_pr_train_blockers(pr_train),
        *_diagnostic_blockers(diagnostic_artifacts),
        *_milestone_blockers(milestone_statuses),
        *_supporting_blockers(supporting_statuses),
        *_report_blockers("failure_taxonomy", failure_taxonomy_report),
        *_report_blockers("activation_wall", activation_wall_audit),
        *_claim_drift_blockers(
            {
                "failure_taxonomy": failure_taxonomy_report,
                "activation_wall": activation_wall_audit,
                **_diagnostic_sources(diagnostic_artifacts),
            }
        ),
    ]


def _pr_train_blockers(pr_train: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    if pr_train.get("artifact_type") != "advanced_product_lab_memory_live_edd_pr_train":
        blockers.append("pr_train.artifact_type_mismatch")
    if pr_train.get("planned_pr_count") != 14:
        blockers.append("pr_train.planned_pr_count_not_14")
    branch_strategy = _mapping(pr_train.get("branch_strategy"))
    if branch_strategy.get("lab_runtime_surface_may_be_complete") is not True:
        blockers.append("pr_train.lab_runtime_surface_not_complete")
    for field in (
        "mainline_activation_enabled",
        "self_use_v1_affected",
        "kimi_live_calls_allowed",
    ):
        if branch_strategy.get(field) is True:
            blockers.append(f"pr_train.branch_strategy.{field}.claim_drift")
    return blockers


def _diagnostic_blockers(
    diagnostic_artifacts: list[Mapping[str, Any]],
) -> list[str]:
    blockers: list[str] = []
    for index, artifact in enumerate(diagnostic_artifacts, start=1):
        label = f"diagnostic:{index}:{artifact.get('artifact_type') or 'missing'}"
        if artifact.get("status") != "pass":
            blockers.append(f"{label}.status_{artifact.get('status')}")
        if artifact.get("lab_enabled") is not True:
            blockers.append(f"{label}.lab_enabled_missing")
    return blockers


def _milestone_blockers(milestone_statuses: Mapping[str, str]) -> list[str]:
    return [
        f"milestone.{milestone_id}.missing_or_not_satisfied"
        for milestone_id, status in milestone_statuses.items()
        if status not in {"satisfied_live_grokfast", "satisfied_report_and_wall"}
    ]


def _supporting_blockers(supporting_statuses: Mapping[str, str]) -> list[str]:
    return [
        f"supporting.{support_id}.missing_or_not_satisfied"
        for support_id, status in supporting_statuses.items()
        if status != "satisfied_live_grokfast"
    ]


def _report_blockers(label: str, report: Mapping[str, Any]) -> list[str]:
    if report.get("status") == "pass":
        return []
    blockers = [f"{label}.status_{report.get('status')}"]
    blockers.extend(f"{label}.{item}" for item in report.get("blockers") or [])
    return blockers


def _claim_drift_blockers(sources: Mapping[str, Mapping[str, Any]]) -> list[str]:
    blockers: list[str] = []
    for source_name, source in sources.items():
        for field in CLAIM_FALSE_FIELDS:
            if source.get(field) is True:
                blockers.append(f"{source_name}.{field}.claim_drift")
    return blockers


def _diagnostic_sources(
    diagnostic_artifacts: list[Mapping[str, Any]],
) -> dict[str, Mapping[str, Any]]:
    return {
        f"diagnostic:{index}:{artifact.get('artifact_type') or 'missing'}": artifact
        for index, artifact in enumerate(diagnostic_artifacts, start=1)
    }


def _mapping(value: object) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


__all__ = ["build_blockers"]
