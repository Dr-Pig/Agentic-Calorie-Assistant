from __future__ import annotations

from datetime import UTC, datetime
import json
from typing import Any

from app.composition.current_shell_metadata_freshness_policy import (
    EXPECTED_ARTIFACT_TYPES,
    EXPECTED_STATUSES,
    REQUIRED_PL_CE_METADATA_ARTIFACTS,
    _current_gap_count,
    _freshness_blockers,
    _group_specific_blockers,
    _identity_blockers,
    _int_value,
    _is_missing_payload,
    _metadata_row,
    _object_dict,
    _overclaim_blockers,
)


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def build_pl_ce_metadata_freshness_pack(
    *,
    evidence: dict[str, Any],
    max_age_hours: int = 72,
    now: datetime | None = None,
) -> dict[str, Any]:
    current_time = (now or datetime.now(UTC)).astimezone(UTC)
    evidence_status = {
        group_id: _object_dict(evidence.get(group_id))
        for group_id in REQUIRED_PL_CE_METADATA_ARTIFACTS
    }
    metadata_rows = {
        group_id: _metadata_row(
            group_id,
            payload,
            now=current_time,
            max_age_hours=max_age_hours,
        )
        for group_id, payload in evidence_status.items()
    }
    missing_artifacts = [
        group_id
        for group_id, payload in evidence_status.items()
        if _is_missing_payload(payload)
    ]
    invalid_metadata: list[str] = []
    stale_artifacts: list[str] = []
    blockers: list[str] = []
    for group_id, payload in evidence_status.items():
        group_blockers = [
            *_identity_blockers(group_id, payload),
            *_freshness_blockers(
                group_id,
                payload,
                now=current_time,
                max_age_hours=max_age_hours,
            ),
            *_overclaim_blockers(group_id, payload),
            *_group_specific_blockers(group_id, payload),
        ]
        blockers.extend(group_blockers)
        if any(
            blocker.startswith(f"{group_id}.missing_artifact_schema_version")
            or blocker.startswith(f"{group_id}.missing_generated_at_utc")
            or blocker.startswith(f"{group_id}.invalid_generated_at_utc")
            or blocker.startswith(f"{group_id}.invalid_artifact_file")
            or blocker.startswith(f"{group_id}.unexpected_artifact_type")
            for blocker in group_blockers
        ):
            invalid_metadata.append(group_id)
        if f"{group_id}.stale_metadata" in group_blockers:
            stale_artifacts.append(group_id)

    summary = _object_dict(evidence_status["context_quality_pack"].get("summary"))
    fresh_artifact_count = sum(
        1
        for group_id in REQUIRED_PL_CE_METADATA_ARTIFACTS
        if metadata_rows[group_id]["freshness_status"] == "fresh"
        and group_id not in missing_artifacts
    )
    status = (
        "metadata_freshness_ready_for_pl_ce_local_review"
        if not blockers and not missing_artifacts
        else "blocked"
    )
    return _json_safe(
        {
            "artifact_schema_version": "1.0",
            "artifact_type": "accurate_intake_pl_ce_metadata_freshness_pack",
            "claim_scope": "pl_ce_metadata_freshness_status_only",
            "status": status,
            "generated_at_utc": current_time.isoformat(),
            "diagnostic_only": True,
            "local_only": True,
            "source_status_only": True,
            "metadata_only": True,
            "producer_track": "PL_CE",
            "intended_consumers": ["human_operator_review", "future_pl_ce_serial_pr_planning"],
            "fixture_or_real": "fixture_or_local_diagnostic_metadata",
            "required_artifacts": list(REQUIRED_PL_CE_METADATA_ARTIFACTS),
            "required_artifact_count": len(REQUIRED_PL_CE_METADATA_ARTIFACTS),
            "fresh_artifact_count": fresh_artifact_count,
            "max_age_hours": max_age_hours,
            "input_statuses": metadata_rows,
            "missing_artifacts": missing_artifacts,
            "stale_artifacts": stale_artifacts,
            "invalid_metadata": sorted(set(invalid_metadata)),
            "blocked_artifacts": sorted(
                {
                    blocker.split(".", 1)[0]
                    for blocker in blockers
                    if "." in blocker
                }
            ),
            "blockers": blockers,
            "summary": {
                "context_replay_scenario_count": _int_value(
                    summary.get("context_replay_scenario_count")
                ),
                "pending_pin_scenarios": _int_value(summary.get("pending_pin_scenarios")),
                "manager_semantic_required_scenarios": _int_value(
                    summary.get("manager_semantic_required_scenarios")
                ),
                "short_term_runtime_replay_scenario_count": _int_value(
                    summary.get("short_term_runtime_replay_scenario_count")
                ),
                "short_term_context_current_gap_scenarios": _int_value(
                    _current_gap_count(evidence_status["context_quality_pack"])
                ),
                "fake_provider_handoff_scenario_count": _int_value(
                    summary.get("fake_provider_handoff_scenario_count")
                ),
            },
            "current_buildable_without_fooddb": True,
            "fooddb_dependency_status": "not_required_for_pl_ce_metadata_freshness",
            "review_required_before_provider_call": True,
            "autofix_attempted": False,
            "ready_for_other_tracks": False,
            "ready_for_live_diagnostic_decision": False,
            "ready_for_fdb_integration": False,
            "shared_contract_changed": False,
            "runtime_truth_changed": False,
            "mutation_changed": False,
            "live_llm_invoked": False,
            "web_tavily_used": False,
            "production_db_used": False,
            "fooddb_truth_updated": False,
            "fooddb_evidence_used": False,
            "websearch_evidence_used": False,
            "real_fooddb_pass_claimed": False,
            "dogfood_pass": False,
            "web_readiness_claimed": False,
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
            "long_term_memory_used": False,
            "next_recommended_slice": (
                "short_term_context_runtime_trace_review_v2"
                if status == "metadata_freshness_ready_for_pl_ce_local_review"
                else "regenerate_or_fix_pl_ce_metadata"
            ),
        }
    )


__all__ = [
    "EXPECTED_ARTIFACT_TYPES",
    "EXPECTED_STATUSES",
    "REQUIRED_PL_CE_METADATA_ARTIFACTS",
    "build_pl_ce_metadata_freshness_pack",
]
