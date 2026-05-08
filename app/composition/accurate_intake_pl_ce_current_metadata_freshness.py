from __future__ import annotations

from datetime import UTC, datetime
import json
from typing import Any

from app.composition.current_shell_compatibility_ids import (
    CURRENT_SHELL_COMPATIBILITY_ACTIVATION_REVIEW_ARTIFACT_TYPE,
    CURRENT_SHELL_COMPATIBILITY_ACTIVATION_REVIEW_GROUP_ID,
    CURRENT_SHELL_COMPATIBILITY_ACTIVATION_REVIEW_READY_STATUS,
    CURRENT_SHELL_COMPATIBILITY_BROWSER_ACTIVATION_ARTIFACT_TYPE,
    CURRENT_SHELL_COMPATIBILITY_CURRENT_METADATA_ARTIFACT_TYPE,
    CURRENT_SHELL_COMPATIBILITY_CURRENT_METADATA_CLAIM_SCOPE,
    CURRENT_SHELL_COMPATIBILITY_CURRENT_METADATA_READY_STATUS,
    CURRENT_SHELL_COMPATIBILITY_LOCAL_MVP_ARTIFACT_TYPE,
    CURRENT_SHELL_COMPATIBILITY_LOCAL_MVP_GROUP_ID,
    CURRENT_SHELL_COMPATIBILITY_LOCAL_MVP_READY_STATUS,
    CURRENT_SHELL_COMPATIBILITY_PRODUCT_PAGES_FLOW_ARTIFACT_TYPE,
    CURRENT_SHELL_COMPATIBILITY_UI_CONTEXT_ALIGNMENT_ARTIFACT_TYPE,
    LEGACY_ACTIVATION_REVIEW_ARTIFACT_TYPES,
    LEGACY_ACTIVATION_REVIEW_GROUP_IDS,
    LEGACY_ACTIVATION_REVIEW_READY_STATUSES,
    LEGACY_BROWSER_ACTIVATION_ARTIFACT_TYPES,
    LEGACY_CURRENT_METADATA_ARTIFACT_TYPES,
    LEGACY_CURRENT_METADATA_CLAIM_SCOPES,
    LEGACY_CURRENT_METADATA_READY_STATUSES,
    LEGACY_LOCAL_MVP_ARTIFACT_TYPES,
    LEGACY_LOCAL_MVP_GROUP_IDS,
    LEGACY_LOCAL_MVP_READY_STATUSES,
    LEGACY_PRODUCT_PAGES_FLOW_ARTIFACT_TYPES,
    LEGACY_UI_CONTEXT_ALIGNMENT_ARTIFACT_TYPES,
    first_group_payload,
    matches_alias,
    set_legacy_alias_metadata,
)


REQUIRED_CURRENT_CHAIN_ARTIFACTS = (
    "ui_same_truth_contract",
    "context_quality_pack",
    "product_pages_visual_qa",
    "product_pages_long_session_navigation_smoke",
    "pl_ce_ui_context_alignment_pack",
    CURRENT_SHELL_COMPATIBILITY_LOCAL_MVP_GROUP_ID,
    "pl_ce_product_pages_self_use_flow_gate",
    "pl_ce_browser_activation_evidence_gate",
    "non_fooddb_manager_tool_contract",
    CURRENT_SHELL_COMPATIBILITY_ACTIVATION_REVIEW_GROUP_ID,
)

EXPECTED_ARTIFACT_TYPES = {
    "ui_same_truth_contract": "accurate_intake_ui_same_truth_render_contract",
    "context_quality_pack": "accurate_intake_context_quality_pack",
    "product_pages_visual_qa": "accurate_intake_product_pages_visual_qa",
    "product_pages_long_session_navigation_smoke": "accurate_intake_product_pages_long_session_navigation_smoke",
    "pl_ce_ui_context_alignment_pack": CURRENT_SHELL_COMPATIBILITY_UI_CONTEXT_ALIGNMENT_ARTIFACT_TYPE,
    CURRENT_SHELL_COMPATIBILITY_LOCAL_MVP_GROUP_ID: (
        CURRENT_SHELL_COMPATIBILITY_LOCAL_MVP_ARTIFACT_TYPE
    ),
    "pl_ce_product_pages_self_use_flow_gate": CURRENT_SHELL_COMPATIBILITY_PRODUCT_PAGES_FLOW_ARTIFACT_TYPE,
    "pl_ce_browser_activation_evidence_gate": CURRENT_SHELL_COMPATIBILITY_BROWSER_ACTIVATION_ARTIFACT_TYPE,
    "non_fooddb_manager_tool_contract": "accurate_intake_non_fooddb_manager_tool_contract",
    CURRENT_SHELL_COMPATIBILITY_ACTIVATION_REVIEW_GROUP_ID: (
        CURRENT_SHELL_COMPATIBILITY_ACTIVATION_REVIEW_ARTIFACT_TYPE
    ),
}

EXPECTED_STATUSES = {
    "ui_same_truth_contract": "pass",
    "context_quality_pack": "context_quality_diagnostic_pass",
    "product_pages_visual_qa": "pass",
    "product_pages_long_session_navigation_smoke": "pass",
    "pl_ce_ui_context_alignment_pack": "ui_context_alignment_ready_for_human_review",
    CURRENT_SHELL_COMPATIBILITY_LOCAL_MVP_GROUP_ID: (
        CURRENT_SHELL_COMPATIBILITY_LOCAL_MVP_READY_STATUS
    ),
    "pl_ce_product_pages_self_use_flow_gate": "product_pages_self_use_flow_ready_for_human_review",
    "pl_ce_browser_activation_evidence_gate": "browser_activation_evidence_ready_for_human_review",
    "non_fooddb_manager_tool_contract": "non_fooddb_manager_tool_contract_ready_for_human_review",
    CURRENT_SHELL_COMPATIBILITY_ACTIVATION_REVIEW_GROUP_ID: (
        CURRENT_SHELL_COMPATIBILITY_ACTIVATION_REVIEW_READY_STATUS
    ),
}

FORBIDDEN_TRUTHY_FLAGS = (
    "ready_for_live_diagnostic_decision",
    "ready_for_fdb_integration",
    "live_llm_invoked",
    "live_provider_called",
    "web_tavily_used",
    "web_tavily_invoked",
    "websearch_evidence_used",
    "fooddb_evidence_used",
    "fooddb_truth_updated",
    "real_fooddb_pass_claimed",
    "dogfood_pass",
    "web_readiness_claimed",
    "product_readiness_claimed",
    "private_self_use_approved",
    "production_db_used",
    "manager_context_packet_schema_changed",
    "runtime_truth_changed",
    "mutation_changed",
    "frontend_semantic_owner",
    "deterministic_semantic_inference_used",
    "raw_text_intent_router_used",
    "mutation_authority",
)


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def _object_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _claim_is_true(value: Any) -> bool:
    if value is True:
        return True
    if value is False or value is None:
        return False
    if isinstance(value, int | float):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "claimed", "enabled"}
    return bool(value)


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


def _freshness_status(value: Any, *, now: datetime, max_age_hours: int) -> tuple[str, Any]:
    parsed = _parse_timestamp(value)
    if parsed is None:
        return "invalid_timestamp", "not_available"
    age_hours = (now - parsed).total_seconds() / 3600
    if age_hours < 0:
        return "future", round(age_hours, 3)
    if age_hours > max_age_hours:
        return "stale", round(age_hours, 3)
    return "fresh", round(age_hours, 3)


def _group_blockers(group_id: str, payload: dict[str, Any], freshness_status: str) -> list[str]:
    blockers: list[str] = []
    if not payload or payload.get("status") == "missing":
        return [f"{group_id}.missing"]
    if group_id == CURRENT_SHELL_COMPATIBILITY_LOCAL_MVP_GROUP_ID:
        if not matches_alias(
            payload.get("artifact_type"),
            EXPECTED_ARTIFACT_TYPES[group_id],
            *LEGACY_LOCAL_MVP_ARTIFACT_TYPES,
        ):
            blockers.append(f"{group_id}.unexpected_artifact_type")
    elif group_id == CURRENT_SHELL_COMPATIBILITY_ACTIVATION_REVIEW_GROUP_ID:
        if not matches_alias(
            payload.get("artifact_type"),
            EXPECTED_ARTIFACT_TYPES[group_id],
            *LEGACY_ACTIVATION_REVIEW_ARTIFACT_TYPES,
        ):
            blockers.append(f"{group_id}.unexpected_artifact_type")
    elif group_id == "pl_ce_ui_context_alignment_pack":
        if not matches_alias(
            payload.get("artifact_type"),
            EXPECTED_ARTIFACT_TYPES[group_id],
            *LEGACY_UI_CONTEXT_ALIGNMENT_ARTIFACT_TYPES,
        ):
            blockers.append(f"{group_id}.unexpected_artifact_type")
    elif group_id == "pl_ce_browser_activation_evidence_gate":
        if not matches_alias(
            payload.get("artifact_type"),
            EXPECTED_ARTIFACT_TYPES[group_id],
            *LEGACY_BROWSER_ACTIVATION_ARTIFACT_TYPES,
        ):
            blockers.append(f"{group_id}.unexpected_artifact_type")
    elif group_id == "pl_ce_product_pages_self_use_flow_gate":
        if not matches_alias(
            payload.get("artifact_type"),
            EXPECTED_ARTIFACT_TYPES[group_id],
            *LEGACY_PRODUCT_PAGES_FLOW_ARTIFACT_TYPES,
        ):
            blockers.append(f"{group_id}.unexpected_artifact_type")
    elif payload.get("artifact_type") != EXPECTED_ARTIFACT_TYPES[group_id]:
        blockers.append(f"{group_id}.unexpected_artifact_type")
    if payload.get("artifact_schema_version") != "1.0":
        blockers.append(f"{group_id}.missing_artifact_schema_version")
    if group_id == CURRENT_SHELL_COMPATIBILITY_LOCAL_MVP_GROUP_ID:
        if not matches_alias(
            payload.get("status"),
            EXPECTED_STATUSES[group_id],
            *LEGACY_LOCAL_MVP_READY_STATUSES,
        ):
            blockers.append(f"{group_id}.unexpected_status:{payload.get('status')}")
    elif group_id == CURRENT_SHELL_COMPATIBILITY_ACTIVATION_REVIEW_GROUP_ID:
        if not matches_alias(
            payload.get("status"),
            EXPECTED_STATUSES[group_id],
            *LEGACY_ACTIVATION_REVIEW_READY_STATUSES,
        ):
            blockers.append(f"{group_id}.unexpected_status:{payload.get('status')}")
    elif payload.get("status") != EXPECTED_STATUSES[group_id]:
        blockers.append(f"{group_id}.unexpected_status:{payload.get('status')}")
    if freshness_status != "fresh":
        blockers.append(f"{group_id}.{freshness_status}")
    blockers.extend(
        f"{group_id}.{flag}" for flag in FORBIDDEN_TRUTHY_FLAGS if _claim_is_true(payload.get(flag))
    )
    return blockers


def _stop_gate_blockers(group_id: str, payload: dict[str, Any]) -> list[str]:
    if group_id == CURRENT_SHELL_COMPATIBILITY_ACTIVATION_REVIEW_GROUP_ID:
        gates = _object_dict(payload.get("remaining_stop_gates"))
        checks = (
            (gates.get("fooddb_artifact_status"), "blocked_waiting_for_fdb_artifact", "fooddb"),
            (gates.get("live_provider_status"), "blocked_pending_human_approval", "live_provider"),
        )
        return [
            f"{CURRENT_SHELL_COMPATIBILITY_ACTIVATION_REVIEW_GROUP_ID}.{name}_stop_gate_missing"
            for actual, expected, name in checks
            if actual != expected
        ]
    if group_id == CURRENT_SHELL_COMPATIBILITY_LOCAL_MVP_GROUP_ID:
        fooddb = _object_dict(payload.get("fooddb_dependency"))
        if fooddb.get("fooddb_artifact_status") != "blocked_waiting_for_fdb_artifact":
            return [f"{CURRENT_SHELL_COMPATIBILITY_LOCAL_MVP_GROUP_ID}.fooddb_stop_gate_missing"]
    return []


def build_pl_ce_current_metadata_freshness_pack(
    *,
    evidence: dict[str, Any],
    max_age_hours: int = 72,
    now: datetime | None = None,
) -> dict[str, Any]:
    current_time = (now or datetime.now(UTC)).astimezone(UTC)
    input_statuses: dict[str, dict[str, Any]] = {}
    blockers: list[str] = []
    for group_id in REQUIRED_CURRENT_CHAIN_ARTIFACTS:
        if group_id == CURRENT_SHELL_COMPATIBILITY_LOCAL_MVP_GROUP_ID:
            payload, _ = first_group_payload(
                evidence,
                CURRENT_SHELL_COMPATIBILITY_LOCAL_MVP_GROUP_ID,
                *LEGACY_LOCAL_MVP_GROUP_IDS,
            )
        elif group_id == CURRENT_SHELL_COMPATIBILITY_ACTIVATION_REVIEW_GROUP_ID:
            payload, _ = first_group_payload(
                evidence,
                CURRENT_SHELL_COMPATIBILITY_ACTIVATION_REVIEW_GROUP_ID,
                *LEGACY_ACTIVATION_REVIEW_GROUP_IDS,
            )
        else:
            payload = _object_dict(evidence.get(group_id))
        freshness, age_hours = _freshness_status(
            payload.get("generated_at_utc"),
            now=current_time,
            max_age_hours=max_age_hours,
        )
        input_statuses[group_id] = {
            "present": bool(payload) and payload.get("status") != "missing",
            "artifact_type": payload.get("artifact_type", "not_available"),
            "artifact_schema_version": payload.get("artifact_schema_version", "not_available"),
            "status": payload.get("status", "not_available"),
            "generated_at_utc": payload.get("generated_at_utc", "not_available"),
            "age_hours": age_hours,
            "freshness_status": freshness,
            "source_artifact_path": payload.get("_source_artifact_path", "not_available"),
        }
        blockers.extend(_group_blockers(group_id, payload, freshness))
        blockers.extend(_stop_gate_blockers(group_id, payload))
    status = CURRENT_SHELL_COMPATIBILITY_CURRENT_METADATA_READY_STATUS if not blockers else "blocked"
    payload = {
        "artifact_schema_version": "1.0",
        "artifact_type": CURRENT_SHELL_COMPATIBILITY_CURRENT_METADATA_ARTIFACT_TYPE,
        "claim_scope": CURRENT_SHELL_COMPATIBILITY_CURRENT_METADATA_CLAIM_SCOPE,
        "status": status,
        "generated_at_utc": current_time.isoformat(),
        "producer_track": "CurrentShell",
        "required_artifacts": list(REQUIRED_CURRENT_CHAIN_ARTIFACTS),
        "required_artifact_count": len(REQUIRED_CURRENT_CHAIN_ARTIFACTS),
        "fresh_artifact_count": sum(
            1 for row in input_statuses.values() if row["freshness_status"] == "fresh"
        ),
        "input_statuses": input_statuses,
        "blockers": blockers,
        "metadata_only": True,
        "source_status_only": True,
        "diagnostic_only": True,
        "local_only": True,
        "ready_for_serial_handoff": not blockers,
        "shared_contract_changed": False,
        "runtime_truth_changed": False,
        "mutation_changed": False,
    }
    set_legacy_alias_metadata(
        payload,
        legacy_artifact_types=LEGACY_CURRENT_METADATA_ARTIFACT_TYPES,
        legacy_statuses=LEGACY_CURRENT_METADATA_READY_STATUSES,
        legacy_claim_scopes=LEGACY_CURRENT_METADATA_CLAIM_SCOPES,
    )
    return _json_safe(payload)


__all__ = [
    "REQUIRED_CURRENT_CHAIN_ARTIFACTS",
    "build_pl_ce_current_metadata_freshness_pack",
]
