from __future__ import annotations

from typing import Any, Mapping

from app.shared.contracts.current_shell_runtime_bridge import (
    CURRENT_SHELL_TOOL_TO_SHARED_CANDIDATE,
)


def build_manager_tool_result_envelope_contract() -> dict[str, Any]:
    return {
        "artifact_type": "shared_manager_tool_result_envelope_contract",
        "artifact_schema_version": "1.0",
        "status": "pass",
        "allowed_source_runtimes": ["current_shell", "advanced_product_lab"],
        "required_fields": [
            "tool_name",
            "capability_id",
            "source_runtime",
            "returned_to_manager",
            "source_refs",
            "blockers",
        ],
        "derived_current_shell_read_model_refs_allowed": True,
        "raw_transcript_included_default": False,
        "blockers": [],
    }


def normalize_manager_tool_result(
    tool_result: Mapping[str, Any],
) -> dict[str, Any]:
    raw = dict(tool_result)
    if raw.get("artifact_type") == "advanced_product_lab_manager_tool_result":
        return _normalize_advanced_product_lab_result(raw)
    return _normalize_current_shell_result(raw)


def _normalize_advanced_product_lab_result(raw: Mapping[str, Any]) -> dict[str, Any]:
    tool_name = str(raw.get("tool_name") or "")
    capability_id = _capability_id_for_tool_name(tool_name)
    inner = _mapping(raw.get("result_artifact"))
    blockers = [str(blocker) for blocker in raw.get("blockers") or []]
    if capability_id is None:
        blockers.append(f"capability_id.unmapped:{tool_name or 'missing'}")
    source_refs = _advanced_product_lab_source_refs(inner)
    return {
        "artifact_type": "shared_manager_tool_result_envelope",
        "artifact_schema_version": "1.0",
        "status": "pass" if not blockers else "blocked",
        "source_runtime": "advanced_product_lab",
        "tool_name": tool_name,
        "capability_id": capability_id or "unknown",
        "returned_to_manager": bool(raw.get("returned_to_manager", True)),
        "source_refs": source_refs,
        "source_ref_count": len(source_refs),
        "payload_summary": {
            "result_artifact_type": str(inner.get("artifact_type") or ""),
            "result_status": str(inner.get("status") or ""),
            "selected_record_ids": [
                str(item)
                for item in _mapping(inner.get("context_pack")).get("selected_record_ids") or []
            ],
        },
        "raw_transcript_included": bool(inner.get("raw_transcript_included") is True),
        "blockers": blockers,
    }


def _normalize_current_shell_result(raw: Mapping[str, Any]) -> dict[str, Any]:
    tool_name = str(raw.get("tool_name") or raw.get("name") or "")
    capability_id = _capability_id_for_tool_name(tool_name)
    evidence = _mapping(raw.get("evidence"))
    blockers: list[str] = []
    if capability_id is None:
        blockers.append(f"capability_id.unmapped:{tool_name or 'missing'}")
    failure_family = str(raw.get("failure_family") or "")
    if failure_family:
        blockers.append(f"tool.failure_family:{failure_family}")
    source_refs = _current_shell_source_refs(tool_name=tool_name, evidence=evidence)
    return {
        "artifact_type": "shared_manager_tool_result_envelope",
        "artifact_schema_version": "1.0",
        "status": "pass" if not blockers else "blocked",
        "source_runtime": "current_shell",
        "tool_name": tool_name,
        "capability_id": capability_id or "unknown",
        "returned_to_manager": True,
        "source_refs": source_refs,
        "source_ref_count": len(source_refs),
        "payload_summary": {
            "evidence_keys": sorted(evidence.keys()),
            "provenance_keys": sorted(_mapping(raw.get("provenance")).keys()),
        },
        "raw_transcript_included": False,
        "blockers": blockers,
    }


def _advanced_product_lab_source_refs(inner: Mapping[str, Any]) -> list[str]:
    refs: list[str] = []
    refs.extend(_string_list(inner.get("source_refs")))
    refs.extend(_string_list(_mapping(inner.get("context_pack")).get("source_refs")))
    refs.extend(_string_list(_mapping(inner.get("record")).get("source_object_refs")))
    for hit in inner.get("hits") or []:
        if not isinstance(hit, Mapping):
            continue
        refs.extend(_string_list(hit.get("source_refs")))
        refs.extend(_string_list(hit.get("source_object_refs")))
    return _dedupe_preserve_order(refs)


def _current_shell_source_refs(
    *,
    tool_name: str,
    evidence: Mapping[str, Any],
) -> list[str]:
    refs = _string_list(evidence.get("source_refs"))
    if refs:
        return _dedupe_preserve_order(refs)
    if tool_name.startswith("budget.") or "remaining_budget_contract" in evidence or "current_budget_view" in evidence:
        return ["read_model:current_budget_view"]
    if tool_name.startswith("body.") and "latest_weight_observation" in evidence:
        return ["read_model:latest_weight_observation"]
    if tool_name.startswith("body.") or "active_body_plan_view" in evidence:
        return ["read_model:active_body_plan_view"]
    if tool_name.startswith("calibration.") or "pending_proposal_status" in evidence:
        return ["read_model:pending_proposal"]
    if tool_name.startswith("app."):
        return ["read_model:app_usage_policy"]
    return []


def _capability_id_for_tool_name(tool_name: str) -> str | None:
    mapped = CURRENT_SHELL_TOOL_TO_SHARED_CANDIDATE.get(tool_name)
    if mapped is not None:
        return str(mapped["capability_id"])
    if tool_name.startswith(("budget.", "body.", "app.", "calibration.")):
        return "query"
    if tool_name.startswith("memory.") or tool_name == "conversation_recall.search":
        return "memory"
    if tool_name == "intake.run":
        return "intake"
    if tool_name == "query.run":
        return "query"
    if tool_name == "recommendation.run":
        return "recommendation"
    if tool_name == "rescue.run":
        return "rescue"
    if tool_name == "proactive.run":
        return "proactive"
    if tool_name == "reusable_meal.search":
        return "reusable_meal"
    return None


def _string_list(value: Any) -> list[str]:
    return [str(item) for item in value or []]


def _dedupe_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = [
    "build_manager_tool_result_envelope_contract",
    "normalize_manager_tool_result",
]
