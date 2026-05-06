from __future__ import annotations

from typing import Any

from app.composition.accurate_intake_pl_ce_activation_manifest_contract import (
    BROWSER_ARTIFACTS,
    EXPECTED_ARTIFACT_TYPES,
    EXPECTED_NESTED_STATUSES,
    EXPECTED_STATUSES,
    EXPECTED_UPSTREAM_REQUIRED_INPUTS,
    FORBIDDEN_TRUTHY_FLAGS,
)
from app.composition.accurate_intake_pl_ce_activation_manifest_group_checks import (
    browser_gate_blockers,
    context_dry_run_blockers,
    local_mvp_blockers,
    ui_context_blockers,
)
from app.composition.accurate_intake_pl_ce_context_live_manifest_checks import (
    OPTIONAL_LIVE_EVIDENCE_ALLOWED_FLAGS,
    context_live_optional_group_blockers,
)


def _object_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _status(payload: dict[str, Any]) -> str:
    return str(payload.get("status") or "")


def _claim_is_true(value: Any) -> bool:
    if value is True:
        return True
    if value is False or value is None:
        return False
    if isinstance(value, int | float):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "claimed", "enabled"}
    return False


def _allowed_statuses(expected_status: Any) -> set[str]:
    if isinstance(expected_status, str):
        return {expected_status}
    if isinstance(expected_status, set | frozenset | tuple | list):
        return {str(status) for status in expected_status}
    return {str(expected_status)}


def _list_contains_all(value: Any, expected_values: tuple[str, ...]) -> bool:
    if not isinstance(value, list):
        return False
    return set(expected_values).issubset(set(str(item) for item in value))


def _identity_blockers(group_id: str, payload: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if _status(payload) not in _allowed_statuses(EXPECTED_STATUSES[group_id]):
        blockers.append(f"{group_id}.unexpected_status:{_status(payload)}")
    if payload.get("artifact_type") != EXPECTED_ARTIFACT_TYPES[group_id]:
        blockers.append(f"{group_id}.unexpected_artifact_type:{payload.get('artifact_type')}")
    return blockers


def _claim_blockers(group_id: str, payload: dict[str, Any]) -> list[str]:
    allowed_flags = OPTIONAL_LIVE_EVIDENCE_ALLOWED_FLAGS.get(group_id, set())
    return [
        f"{group_id}.{flag}"
        for flag in FORBIDDEN_TRUTHY_FLAGS
        if flag not in allowed_flags
        if _claim_is_true(payload.get(flag))
    ]


def _structural_blockers(group_id: str, payload: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if payload.get("artifact_schema_version") != "1.0":
        blockers.append(f"{group_id}.missing_artifact_schema_version")
    upstream_blockers = payload.get("blockers")
    if upstream_blockers != []:
        suffix = "upstream_blockers_present" if upstream_blockers else "upstream_blockers_missing"
        blockers.append(f"{group_id}.{suffix}")
    if group_id.startswith("context_live_"):
        return blockers
    if not _list_contains_all(payload.get("required_inputs"), EXPECTED_UPSTREAM_REQUIRED_INPUTS[group_id]):
        blockers.append(f"{group_id}.required_inputs_incomplete")
    blockers.extend(_nested_status_blockers(group_id, payload))
    for flag, expected in (
        ("aggregate_only", True),
        ("self_generated_evidence_used", False),
        ("review_required_before_provider_call", True),
    ):
        if payload.get(flag) is not expected:
            blockers.append(f"{group_id}.{flag}_not_{str(expected).lower()}")
    return blockers


def _nested_status_blockers(group_id: str, payload: dict[str, Any]) -> list[str]:
    included = payload.get("included_artifact_statuses")
    if not isinstance(included, dict) or not included:
        return [f"{group_id}.included_artifact_statuses_missing"]
    expected_inputs = EXPECTED_UPSTREAM_REQUIRED_INPUTS[group_id]
    if not set(expected_inputs).issubset(included):
        return [f"{group_id}.included_artifact_statuses_incomplete"]
    blockers: list[str] = []
    for input_id, expected_status in EXPECTED_NESTED_STATUSES[group_id].items():
        nested_status = _object_dict(included.get(input_id))
        if str(nested_status.get("status") or "") not in _allowed_statuses(expected_status):
            blockers.append(
                f"{group_id}.included_artifact_statuses."
                f"{input_id}.unexpected_status:{nested_status.get('status')}"
            )
        if group_id == "pl_ce_browser_activation_evidence_gate" and input_id in BROWSER_ARTIFACTS:
            if nested_status.get("browser_executed") is not True:
                blockers.append(f"{group_id}.included_artifact_statuses.{input_id}.browser_not_executed")
        if group_id == "pl_ce_ui_context_alignment_pack" and input_id.startswith("product_pages_"):
            if input_id != "product_pages_renderer_source_map" and nested_status.get("browser_executed") is not True:
                blockers.append(f"{group_id}.included_artifact_statuses.{input_id}.browser_not_executed")
    return blockers


def activation_manifest_blockers(group_id: str, payload: dict[str, Any]) -> list[str]:
    blockers = _identity_blockers(group_id, payload)
    blockers.extend(_claim_blockers(group_id, payload))
    blockers.extend(_structural_blockers(group_id, payload))
    if group_id == "pl_ce_local_mvp_candidate_bundle":
        blockers.extend(local_mvp_blockers(payload))
    elif group_id == "pl_ce_browser_activation_evidence_gate":
        blockers.extend(browser_gate_blockers(payload))
    elif group_id == "pl_ce_ui_context_alignment_pack":
        blockers.extend(ui_context_blockers(payload))
    elif group_id in {"context_live_diagnostic_dry_run_evaluator", "context_live_response_contract_dry_run"}:
        blockers.extend(context_dry_run_blockers(group_id, payload))
    blockers.extend(context_live_optional_group_blockers(group_id, payload))
    return blockers


def artifact_statuses(payloads: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {
        group_id: {
            "artifact_type": payload.get("artifact_type") or "not_available",
            "status": _status(payload),
            "source_artifact_path": payload.get("_source_artifact_path") or "not_available",
        }
        for group_id, payload in payloads.items()
    }
