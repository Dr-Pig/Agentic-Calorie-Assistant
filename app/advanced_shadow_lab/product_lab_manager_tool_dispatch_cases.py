from __future__ import annotations

from typing import Any, Mapping

from app.advanced_shadow_lab.product_lab_manager_tool_contract import MEMORY_TOOL_NAMES
from app.advanced_shadow_lab.product_lab_intake_bridge import (
    build_advanced_lab_intake_bridge_trace,
)
from app.advanced_shadow_lab.product_lab_memory import empty_product_lab_memory_context_pack
from app.advanced_shadow_lab.product_lab_memory_store import ProductLabMemoryStore
from app.advanced_shadow_lab.product_lab_memory_tools import (
    execute_product_lab_memory_tool_call,
)
from app.advanced_shadow_lab.product_lab_proactive import run_product_lab_proactive
from app.advanced_shadow_lab.product_lab_query import run_product_lab_query
from app.advanced_shadow_lab.product_lab_recommendation import (
    run_product_lab_recommendation,
)
from app.advanced_shadow_lab.product_lab_reusable_meal import (
    run_product_lab_reusable_meal_search,
)
from app.advanced_shadow_lab.product_lab_rescue import run_product_lab_rescue


def dispatch_product_lab_manager_tool(
    *,
    tool_name: str,
    arguments: Mapping[str, Any],
    turn: Mapping[str, Any],
    fixture_inputs: Mapping[str, Any],
    store: ProductLabMemoryStore | None,
    prior_tool_results: Mapping[str, Mapping[str, Any]],
) -> tuple[dict[str, Any], list[str]]:
    if tool_name in MEMORY_TOOL_NAMES:
        return _dispatch_memory_tool(
            tool_name=tool_name,
            arguments=arguments,
            turn=turn,
            store=store,
        )
    if tool_name == "intake.run":
        return build_advanced_lab_intake_bridge_trace(turn=turn, arguments=arguments), []
    if tool_name == "query.run":
        return run_product_lab_query(fixture_inputs=fixture_inputs), []
    if tool_name == "reusable_meal.search":
        return (
            run_product_lab_reusable_meal_search(
                turn=turn,
                fixture_inputs=fixture_inputs,
                memory_summary=_memory_summary_from_args(
                    arguments,
                    prior_tool_results,
                ),
            ),
            [],
        )
    if tool_name == "recommendation.run":
        return (
            run_product_lab_recommendation(
                turn=turn,
                fixture_inputs=fixture_inputs,
                memory_context_pack=_memory_pack_from_args(arguments, prior_tool_results, turn),
                reusable_meal_context_pack=_prior_result(
                    arguments, prior_tool_results, "reusable_meal_call_id"
                ),
            ),
            [],
        )
    if tool_name == "rescue.run":
        return run_product_lab_rescue(fixture_inputs=fixture_inputs), []
    if tool_name == "proactive.run":
        return _dispatch_proactive_tool(
            arguments=arguments,
            turn=turn,
            fixture_inputs=fixture_inputs,
            prior_tool_results=prior_tool_results,
        )
    return {}, [f"tool.unsupported:{tool_name}"]


def _dispatch_memory_tool(
    *,
    tool_name: str,
    arguments: Mapping[str, Any],
    turn: Mapping[str, Any],
    store: ProductLabMemoryStore | None,
) -> tuple[dict[str, Any], list[str]]:
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


def _dispatch_proactive_tool(
    *,
    arguments: Mapping[str, Any],
    turn: Mapping[str, Any],
    fixture_inputs: Mapping[str, Any],
    prior_tool_results: Mapping[str, Mapping[str, Any]],
) -> tuple[dict[str, Any], list[str]]:
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


def _memory_summary_from_args(
    arguments: Mapping[str, Any],
    prior_tool_results: Mapping[str, Mapping[str, Any]],
) -> Mapping[str, Any]:
    artifact = _prior_result(arguments, prior_tool_results, "memory_context_call_id")
    context_pack = artifact.get("context_pack") if isinstance(artifact, Mapping) else {}
    if isinstance(context_pack, Mapping):
        return context_pack
    return {}


def _prior_result(
    arguments: Mapping[str, Any],
    prior_tool_results: Mapping[str, Mapping[str, Any]],
    argument_name: str,
) -> Mapping[str, Any]:
    wrapper = prior_tool_results.get(str(arguments.get(argument_name) or ""))
    result = wrapper.get("result_artifact") if isinstance(wrapper, Mapping) else {}
    return result if isinstance(result, Mapping) else {}


__all__ = ["dispatch_product_lab_manager_tool"]
