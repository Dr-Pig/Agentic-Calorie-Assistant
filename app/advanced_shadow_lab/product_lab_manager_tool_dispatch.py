from __future__ import annotations

from typing import Any, Mapping

from app.advanced_shadow_lab.product_lab_manager_tool_contract import (
    MANAGER_TOOL_NAMES,
    TOOL_FAMILIES,
    TOOL_MODES,
    dormant_activation_fields,
)
from app.advanced_shadow_lab.product_lab_manager_tool_dispatch_cases import (
    dispatch_product_lab_manager_tool,
)
from app.advanced_shadow_lab.product_lab_memory_store import ProductLabMemoryStore
from app.advanced_shadow_lab.product_lab_session_store import unsafe_segment_blocker
from app.shared.contracts.manager_tool_result_envelope import (
    normalize_manager_tool_result,
)


def execute_product_lab_manager_tool_call(
    *,
    turn: Mapping[str, Any],
    fixture_inputs: Mapping[str, Any],
    tool_call: Mapping[str, Any],
    store: ProductLabMemoryStore | None,
    prior_tool_results: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    call_id = str(tool_call.get("call_id") or "")
    tool_name = str(tool_call.get("tool_name") or "")
    arguments = _mapping(tool_call.get("arguments"))
    blockers = _tool_call_blockers(call_id=call_id, tool_name=tool_name)
    if not blockers:
        result, dispatch_blockers = dispatch_product_lab_manager_tool(
            tool_name=tool_name,
            arguments=arguments,
            turn=turn,
            fixture_inputs=fixture_inputs,
            store=store,
            prior_tool_results=prior_tool_results or {},
        )
        blockers.extend(dispatch_blockers)
    else:
        result = {}
    if result.get("status") != "pass":
        blockers.append(f"result.status_{result.get('status') or 'missing'}")
    blockers.extend(str(blocker) for blocker in result.get("blockers") or [])
    return _manager_tool_result(
        call_id=call_id,
        tool_name=tool_name,
        status="blocked" if blockers else "pass",
        result_artifact=result,
        blockers=blockers,
    )


def _manager_tool_result(
    *,
    call_id: str,
    tool_name: str,
    status: str,
    result_artifact: Mapping[str, Any],
    blockers: list[str],
) -> dict[str, Any]:
    artifact = {
        "artifact_type": "advanced_product_lab_manager_tool_result",
        "artifact_schema_version": "1.0",
        "status": status,
        "call_id": call_id,
        "tool_name": tool_name,
        "capability_family": TOOL_FAMILIES.get(tool_name, "unknown"),
        "tool_mode": TOOL_MODES.get(tool_name, "unsupported"),
        "result_artifact_type": str(result_artifact.get("artifact_type") or ""),
        "result_status": str(result_artifact.get("status") or ""),
        "result_artifact": dict(result_artifact),
        "returned_to_manager": True,
        "raw_transcript_included": False,
        **dormant_activation_fields(),
        "blockers": blockers,
    }
    artifact["normalized_result_envelope"] = normalize_manager_tool_result(artifact)
    return artifact


def _tool_call_blockers(*, call_id: str, tool_name: str) -> list[str]:
    blockers: list[str] = []
    if not call_id or unsafe_segment_blocker("call_id", call_id):
        blockers.append("call_id.missing_or_unsafe")
    if tool_name not in MANAGER_TOOL_NAMES:
        blockers.append(f"tool.unsupported:{tool_name or 'missing'}")
    return blockers


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = ["execute_product_lab_manager_tool_call"]
