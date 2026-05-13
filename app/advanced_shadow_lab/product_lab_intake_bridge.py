from __future__ import annotations

from dataclasses import asdict
from typing import Any, Mapping

from app.runtime.agent.manager_result_builder import IntakeManagerResult


FORBIDDEN_TRUE_ARGUMENTS = {
    "canonical_product_mutation_allowed",
    "meal_thread_mutated",
    "ledger_entry_created",
    "durable_product_memory_written",
    "production_db_migration_allowed",
}
REQUIRED_MANAGER_RESULT_FIELDS = (
    "intent",
    "manager_action",
    "final_action",
    "workflow_effect",
)
FALSE_FLAGS = {
    "canonical_product_mutation_allowed": False,
    "meal_thread_mutated": False,
    "ledger_entry_created": False,
    "durable_product_memory_written": False,
    "scheduler_delivery_allowed": False,
    "mainline_activation_enabled": False,
    "self_use_v1_affected": False,
}


def build_advanced_lab_intake_bridge_trace(
    *,
    turn: Mapping[str, Any],
    arguments: Mapping[str, Any],
) -> dict[str, Any]:
    payload = _mapping(arguments.get("intake_manager_result"))
    blockers = [
        *_payload_blockers(payload),
        *_argument_overclaim_blockers(arguments),
    ]
    result = None if blockers else _manager_result(payload)
    result_payload = _result_payload(result) if result is not None else {}
    return {
        "artifact_type": "advanced_product_lab_intake_bridge_trace",
        "artifact_schema_version": "1.0",
        "status": "blocked" if blockers else "pass",
        "owner": "app/advanced_shadow_lab/product_lab_intake_bridge.py",
        "consumer": "advanced_product_lab_manager_tool_loop",
        "current_shell_contract_ref": (
            "app.runtime.agent.manager_result_builder.IntakeManagerResult"
        ),
        "intake_bridge_contract_backed": result is not None,
        "manager_style_tool_result_returned": result is not None,
        "session_id": str(turn.get("session_id") or ""),
        "turn_id": str(turn.get("turn_id") or ""),
        "current_shell_intake_result": result_payload,
        "source_tool_calls": list(result.tool_calls) if result is not None else [],
        "source_tool_result_count": len(result.tool_results) if result is not None else 0,
        "blockers": blockers,
        **FALSE_FLAGS,
    }


def _payload_blockers(payload: Mapping[str, Any]) -> list[str]:
    blockers = []
    for field in REQUIRED_MANAGER_RESULT_FIELDS:
        if not payload.get(field):
            blockers.append(f"intake_manager_result.{field}.missing")
    return blockers


def _argument_overclaim_blockers(arguments: Mapping[str, Any]) -> list[str]:
    return [
        f"arguments.{field}_forbidden"
        for field in sorted(FORBIDDEN_TRUE_ARGUMENTS)
        if arguments.get(field) is True
    ]


def _manager_result(payload: Mapping[str, Any]) -> IntakeManagerResult:
    return IntakeManagerResult(
        intent=str(payload.get("intent") or ""),
        manager_action=str(payload.get("manager_action") or ""),
        final_action=str(payload.get("final_action") or ""),
        workflow_effect=str(payload.get("workflow_effect") or ""),
        exactness=str(payload.get("exactness") or "unknown"),
        confidence=str(payload.get("confidence") or "unknown"),
        evidence_posture=str(payload.get("evidence_posture") or "unknown"),
        answer_contract=dict(_mapping(payload.get("answer_contract"))),
        tool_calls=tuple(str(item) for item in payload.get("tool_calls") or []),
        tool_results=tuple(
            dict(item) for item in payload.get("tool_results") or [] if isinstance(item, Mapping)
        ),
    )


def _result_payload(result: IntakeManagerResult) -> dict[str, Any]:
    payload = asdict(result)
    payload["estimated_kcal"] = _estimated_kcal(result)
    payload["tool_calls"] = list(result.tool_calls)
    payload["tool_results"] = list(result.tool_results)
    return payload


def _estimated_kcal(result: IntakeManagerResult) -> int:
    answer_kcal = result.answer_contract.get("estimated_kcal")
    if isinstance(answer_kcal, int):
        return answer_kcal
    for tool_result in result.tool_results:
        evidence = _mapping(tool_result.get("evidence"))
        nutrition = _mapping(evidence.get("nutrition_payload"))
        kcal = nutrition.get("estimated_kcal")
        if isinstance(kcal, int):
            return kcal
    return 0


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = ["build_advanced_lab_intake_bridge_trace"]
