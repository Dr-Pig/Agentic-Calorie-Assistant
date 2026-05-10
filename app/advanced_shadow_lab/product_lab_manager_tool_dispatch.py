from __future__ import annotations

from typing import Any, Mapping

from app.advanced_shadow_lab.product_lab_manager_tool_contract import (
    MANAGER_TOOL_NAMES,
    MEMORY_TOOL_NAMES,
    TOOL_FAMILIES,
    TOOL_MODES,
    dormant_activation_fields,
)
from app.advanced_shadow_lab.product_lab_memory import empty_product_lab_memory_context_pack
from app.advanced_shadow_lab.product_lab_memory_store import ProductLabMemoryStore
from app.advanced_shadow_lab.product_lab_memory_tools import (
    execute_product_lab_memory_tool_call,
)
from app.advanced_shadow_lab.product_lab_proactive import run_product_lab_proactive
from app.advanced_shadow_lab.product_lab_recommendation import (
    run_product_lab_recommendation,
)
from app.advanced_shadow_lab.product_lab_rescue import run_product_lab_rescue
from app.advanced_shadow_lab.product_lab_session_store import unsafe_segment_blocker


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
        result, dispatch_blockers = _dispatch_tool(
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


def _dispatch_tool(
    *,
    tool_name: str,
    arguments: Mapping[str, Any],
    turn: Mapping[str, Any],
    fixture_inputs: Mapping[str, Any],
    store: ProductLabMemoryStore | None,
    prior_tool_results: Mapping[str, Mapping[str, Any]],
) -> tuple[dict[str, Any], list[str]]:
    if tool_name in MEMORY_TOOL_NAMES:
        if store is None:
            return {}, ["memory_store.missing"]
        return (
            execute_product_lab_memory_tool_call(
                store=store,
                session_id=str(turn.get("session_id") or ""),
                turn_id=str(turn.get("turn_id") or ""),
                tool_name=tool_name,
                arguments=arguments,
            ),
            [],
        )
    if tool_name == "recommendation.run":
        return (
            run_product_lab_recommendation(
                turn=turn,
                fixture_inputs=fixture_inputs,
                memory_context_pack=_memory_pack_from_args(arguments, prior_tool_results, turn),
            ),
            [],
        )
    if tool_name == "rescue.run":
        return run_product_lab_rescue(fixture_inputs=fixture_inputs), []
    if tool_name == "proactive.run":
        recommendation = _prior_result(arguments, prior_tool_results, "recommendation_call_id")
        rescue = _prior_result(arguments, prior_tool_results, "rescue_call_id")
        missing = [
            name
            for name, artifact in (
                ("recommendation_call_id", recommendation),
                ("rescue_call_id", rescue),
            )
            if not artifact
        ]
        if missing:
            return {}, [f"prior_tool_result.missing:{name}" for name in missing]
        return (
            run_product_lab_proactive(
                turn=turn,
                fixture_inputs=fixture_inputs,
                memory_context_pack=_memory_pack_from_args(arguments, prior_tool_results, turn),
                recommendation_artifact=recommendation,
                rescue_artifact=rescue,
            ),
            [],
        )
    return {}, [f"tool.unsupported:{tool_name}"]


def _manager_tool_result(
    *,
    call_id: str,
    tool_name: str,
    status: str,
    result_artifact: Mapping[str, Any],
    blockers: list[str],
) -> dict[str, Any]:
    return {
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


def _memory_pack_from_args(
    arguments: Mapping[str, Any],
    prior_tool_results: Mapping[str, Mapping[str, Any]],
    turn: Mapping[str, Any],
) -> Mapping[str, Any]:
    artifact = _prior_result(arguments, prior_tool_results, "memory_context_call_id")
    context_pack = artifact.get("context_pack") if isinstance(artifact, Mapping) else {}
    if isinstance(context_pack, Mapping) and context_pack:
        return context_pack
    if isinstance(arguments.get("memory_context_pack"), Mapping):
        return arguments["memory_context_pack"]  # type: ignore[index]
    return empty_product_lab_memory_context_pack(
        session_id=str(turn.get("session_id") or ""),
        turn_id=str(turn.get("turn_id") or ""),
    )


def _prior_result(
    arguments: Mapping[str, Any],
    prior_tool_results: Mapping[str, Mapping[str, Any]],
    argument_name: str,
) -> Mapping[str, Any]:
    wrapper = prior_tool_results.get(str(arguments.get(argument_name) or ""))
    result = wrapper.get("result_artifact") if isinstance(wrapper, Mapping) else {}
    return result if isinstance(result, Mapping) else {}


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
