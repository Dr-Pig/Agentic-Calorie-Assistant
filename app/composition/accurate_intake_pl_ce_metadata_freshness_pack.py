from __future__ import annotations

from datetime import UTC, datetime
import json
from typing import Any

from app.composition import current_shell_compatibility_ids as cs_ids

REQUIRED_PL_CE_METADATA_ARTIFACTS = (
    "context_quality_pack", "product_pages_visual_qa", "pl_ce_local_review_decision_pack",
    "pl_ce_local_mvp_candidate_bundle", "pl_ce_activation_review_manifest",
    "ui_same_truth_render_contract",
)

EXPECTED_ARTIFACT_TYPES = {
    "context_quality_pack": "accurate_intake_context_quality_pack",
    "product_pages_visual_qa": "accurate_intake_product_pages_visual_qa",
    "pl_ce_local_review_decision_pack": cs_ids.CURRENT_SHELL_COMPATIBILITY_LOCAL_REVIEW_ARTIFACT_TYPE,
    "pl_ce_local_mvp_candidate_bundle": "accurate_intake_pl_ce_local_mvp_candidate_bundle",
    "pl_ce_activation_review_manifest": "accurate_intake_pl_ce_activation_review_manifest",
    "ui_same_truth_render_contract": "accurate_intake_ui_same_truth_render_contract",
}

EXPECTED_STATUSES = {
    "context_quality_pack": "context_quality_diagnostic_pass",
    "product_pages_visual_qa": "pass",
    "pl_ce_local_review_decision_pack": cs_ids.CURRENT_SHELL_COMPATIBILITY_LOCAL_REVIEW_READY_STATUS,
    "pl_ce_local_mvp_candidate_bundle": "pl_ce_local_mvp_candidate_ready_for_human_review",
    "pl_ce_activation_review_manifest": "pl_ce_activation_review_manifest_ready",
    "ui_same_truth_render_contract": "pass",
}

MIN_CONTEXT_SUMMARY_COUNTS = {
    "context_replay_scenario_count": 12, "pending_pin_scenarios": 3,
    "manager_semantic_required_scenarios": 1,
    "short_term_runtime_replay_scenario_count": 7,
    "fake_provider_handoff_scenario_count": 6,
}

OVERCLAIM_FLAGS = (
    "ready_for_live_diagnostic_decision",
    "ready_for_fdb_integration",
    "live_llm_invoked",
    "web_tavily_used",
    "web_tavily_invoked",
    "production_db_used",
    "fooddb_truth_updated",
    "fooddb_evidence_used",
    "websearch_evidence_used",
    "real_fooddb_pass_claimed",
    "dogfood_pass",
    "web_readiness_claimed",
    "product_readiness_claimed",
    "private_self_use_approved",
    "frontend_semantic_owner",
    "runtime_truth_changed",
    "mutation_changed",
    "manager_context_packet_schema_changed",
    "context_engineering_fault_claimed",
    "deterministic_semantic_inference_used",
    "raw_text_intent_router_used",
    "mutation_authority",
    "canonical_eval_promoted",
)


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def _object_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _int_value(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _claim_is_true(value: Any) -> bool:
    if value is True:
        return True
    if value is False or value is None:
        return False
    if isinstance(value, int | float):
        return value != 0
    if isinstance(value, str):
        normalized = value.strip().lower()
        return normalized in {"1", "true", "yes", "y", "claimed", "enabled"}
    return False


def _parse_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _age_hours(generated_at_utc: Any, *, now: datetime) -> float | None:
    parsed = _parse_timestamp(generated_at_utc)
    if parsed is None:
        return None
    return (now - parsed).total_seconds() / 3600


def _metadata_row(
    group_id: str,
    payload: dict[str, Any],
    *,
    now: datetime,
    max_age_hours: int,
) -> dict[str, Any]:
    age = _age_hours(payload.get("generated_at_utc"), now=now)
    if age is None:
        freshness_status = "invalid_timestamp"
    elif age < 0:
        freshness_status = "future"
    elif age > max_age_hours:
        freshness_status = "stale"
    else:
        freshness_status = "fresh"
    return {
        "group_id": group_id,
        "artifact_path": payload.get("artifact_path", "not_available"),
        "present": not _is_missing_payload(payload),
        "artifact_type": payload.get("artifact_type", "not_available"),
        "artifact_schema_version": payload.get("artifact_schema_version", "not_available"),
        "status": payload.get("status", "not_available"),
        "generated_at_utc": payload.get("generated_at_utc", "not_available"),
        "file_mtime_utc": payload.get("file_mtime_utc", "not_available"),
        "age_hours": round(age, 3) if age is not None else "not_available",
        "freshness_status": freshness_status,
    }


def _identity_blockers(group_id: str, payload: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if _is_missing_payload(payload):
        return [f"{group_id}.missing"]
    if _is_invalid_read_payload(payload):
        return [f"{group_id}.invalid_artifact_file"]
    expected_type = EXPECTED_ARTIFACT_TYPES[group_id]
    legacy_types = cs_ids.LEGACY_LOCAL_REVIEW_ARTIFACT_TYPES if group_id == "pl_ce_local_review_decision_pack" else ()
    if not cs_ids.matches_alias(payload.get("artifact_type"), expected_type, *legacy_types):
        blockers.append(f"{group_id}.unexpected_artifact_type")
    if not payload.get("artifact_schema_version"):
        blockers.append(f"{group_id}.missing_artifact_schema_version")
    if not payload.get("generated_at_utc"):
        blockers.append(f"{group_id}.missing_generated_at_utc")
    expected_status = EXPECTED_STATUSES[group_id]
    legacy_statuses = cs_ids.LEGACY_LOCAL_REVIEW_READY_STATUSES if group_id == "pl_ce_local_review_decision_pack" else ()
    if not cs_ids.matches_alias(payload.get("status"), expected_status, *legacy_statuses):
        blockers.append(f"{group_id}.unexpected_status")
    return blockers


def _freshness_blockers(
    group_id: str,
    payload: dict[str, Any],
    *,
    now: datetime,
    max_age_hours: int,
) -> list[str]:
    if _is_missing_payload(payload) or _is_invalid_read_payload(payload):
        return []
    age = _age_hours(payload.get("generated_at_utc"), now=now)
    if age is None:
        return [f"{group_id}.invalid_generated_at_utc"]
    if age < 0:
        return [f"{group_id}.future_generated_at_utc"]
    if age > max_age_hours:
        return [f"{group_id}.stale_metadata"]
    return []


def _overclaim_blockers(group_id: str, payload: dict[str, Any]) -> list[str]:
    return [
        f"{group_id}.{flag}"
        for flag in OVERCLAIM_FLAGS
        if _claim_is_true(payload.get(flag))
    ]


def _is_missing_payload(payload: dict[str, Any]) -> bool:
    if not payload:
        return True
    return (
        payload.get("status") == "missing"
        or payload.get("artifact_type") == "missing_pl_ce_metadata_freshness_input"
    )


def _is_invalid_read_payload(payload: dict[str, Any]) -> bool:
    return payload.get("artifact_type") == "invalid_pl_ce_metadata_freshness_input"


def _context_quality_blockers(payload: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if payload.get("runtime_trace_input_used") is not True:
        blockers.append("context_quality_pack.runtime_trace_input_missing")
    if payload.get("short_term_context_runtime_replay_checked") is not True:
        blockers.append("context_quality_pack.short_term_runtime_replay_missing")
    summary = _object_dict(payload.get("summary"))
    for key, minimum in MIN_CONTEXT_SUMMARY_COUNTS.items():
        if _int_value(summary.get(key)) < minimum:
            suffix = "missing" if minimum == 1 else "too_low"
            blockers.append(f"context_quality_pack.{key}_{suffix}")
    if _current_gap_count(payload) != 0:
        blockers.append("context_quality_pack.short_term_context_current_gap_scenarios_present")
    return blockers


def _current_gap_count(payload: dict[str, Any]) -> int:
    summary = _object_dict(payload.get("summary"))
    if "short_term_context_current_gap_scenarios" in payload:
        return _int_value(payload.get("short_term_context_current_gap_scenarios"))
    if "short_term_context_current_gap_scenarios" in summary:
        return _int_value(summary.get("short_term_context_current_gap_scenarios"))
    return _int_value(summary.get("short_term_runtime_replay_current_gap_scenarios"))


def _product_pages_visual_qa_blockers(payload: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    for key in (
        "browser_executed",
        "three_distinct_pages_verified",
        "chat_surface_verified",
        "today_surface_verified",
        "body_surface_verified",
        "visible_trace_debug_terms_absent",
    ):
        if payload.get(key) is not True:
            blockers.append(f"product_pages_visual_qa.{key}_not_true")
    return blockers


def _decision_pack_blockers(payload: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if payload.get("ready_for_live_diagnostic_decision") is not False:
        blockers.append("pl_ce_local_review_decision_pack.ready_for_live_diagnostic_decision_not_false")
    if payload.get("ready_for_fdb_integration") is not False:
        blockers.append("pl_ce_local_review_decision_pack.ready_for_fdb_integration_not_false")
    return blockers


def _local_mvp_candidate_blockers(payload: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if payload.get("activation_gate_status") != "blocked_pending_human_and_browser_activation":
        blockers.append("pl_ce_local_mvp_candidate_bundle.activation_gate_status_missing")
    fooddb_dependency = _object_dict(payload.get("fooddb_dependency"))
    if fooddb_dependency.get("fooddb_artifact_status") != "blocked_waiting_for_fdb_artifact":
        blockers.append("pl_ce_local_mvp_candidate_bundle.fooddb_stop_gate_missing")
    if fooddb_dependency.get("ready_for_fdb_integration") is not False:
        blockers.append("pl_ce_local_mvp_candidate_bundle.fooddb_integration_not_blocked")
    return blockers


def _activation_manifest_blockers(payload: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if payload.get("human_review_required") is not True:
        blockers.append("pl_ce_activation_review_manifest.human_review_required_not_true")
    if payload.get("live_diagnostic_human_approval_required") is not True:
        blockers.append("pl_ce_activation_review_manifest.live_human_approval_not_required")
    stop_gates = _object_dict(payload.get("remaining_stop_gates"))
    if stop_gates.get("fooddb_artifact_status") != "blocked_waiting_for_fdb_artifact":
        blockers.append("pl_ce_activation_review_manifest.fooddb_stop_gate_missing")
    if stop_gates.get("live_provider_status") != "blocked_pending_human_approval":
        blockers.append("pl_ce_activation_review_manifest.live_provider_stop_gate_missing")
    return blockers


def _ui_same_truth_blockers(payload: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if payload.get("frontend_semantic_owner") is not False:
        blockers.append("ui_same_truth_render_contract.frontend_semantic_owner_not_false")
    if payload.get("runtime_truth_changed") is not False:
        blockers.append("ui_same_truth_render_contract.runtime_truth_changed_not_false")
    if payload.get("mutation_changed") is not False:
        blockers.append("ui_same_truth_render_contract.mutation_changed_not_false")
    return blockers


def _group_specific_blockers(group_id: str, payload: dict[str, Any]) -> list[str]:
    if _is_missing_payload(payload) or _is_invalid_read_payload(payload):
        return []
    if group_id == "context_quality_pack":
        return _context_quality_blockers(payload)
    if group_id == "product_pages_visual_qa":
        return _product_pages_visual_qa_blockers(payload)
    if group_id == "pl_ce_local_review_decision_pack":
        return _decision_pack_blockers(payload)
    if group_id == "pl_ce_local_mvp_candidate_bundle":
        return _local_mvp_candidate_blockers(payload)
    if group_id == "pl_ce_activation_review_manifest":
        return _activation_manifest_blockers(payload)
    if group_id == "ui_same_truth_render_contract":
        return _ui_same_truth_blockers(payload)
    return []


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
