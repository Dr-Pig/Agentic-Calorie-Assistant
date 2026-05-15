from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.body.application.body_observation_service import (
    record_body_observation_to_canonical,
)
from app.database import get_or_create_user


def _serialize_observation(observation: Any) -> dict[str, Any]:
    observed_at = getattr(observation, "observed_at", None)
    return {
        "observation_id": getattr(observation, "observation_id", None),
        "user_id": getattr(observation, "user_id", None),
        "observation_type": str(getattr(observation, "observation_type", "") or ""),
        "value": float(getattr(observation, "value", 0.0) or 0.0),
        "unit": str(getattr(observation, "unit", "") or ""),
        "local_date": str(getattr(observation, "local_date", "") or ""),
        "observed_at": observed_at.isoformat() if isinstance(observed_at, datetime) else None,
        "source": str(getattr(observation, "source", "") or ""),
        "metadata": dict(getattr(observation, "metadata", {}) or {}),
    }


def _coerce_weight_arguments(arguments: dict[str, Any]) -> tuple[float, str]:
    observation_type = str(arguments.get("observation_type") or "weight").strip().lower()
    if observation_type != "weight":
        raise ValueError("body.record_observation only supports weight observations")
    raw_value = arguments.get("value")
    if raw_value in (None, ""):
        raise ValueError("body.record_observation requires a numeric weight value")
    value = float(raw_value)
    unit = str(arguments.get("unit") or "kg").strip().lower() or "kg"
    if unit != "kg":
        raise ValueError("body.record_observation weight unit must be kg")
    return value, unit


def _body_observation_tool_result(
    *,
    tool_name: str,
    failure_family: str | None = None,
    evidence: dict[str, Any] | None = None,
    mutation_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "tool_name": tool_name,
        "evidence": dict(evidence or {}),
        "mutation_result": dict(mutation_result or {}),
        "provenance": {
            "truth_owner": "body_domain",
            "tool_kind": "mutation_bearing",
            "mutation_authority": False,
            "canonical_tool_name": "body.record_observation",
        },
        "confidence": "available" if failure_family is None else "none",
        "failure_family": failure_family,
    }


def build_body_observation_tool_executor(
    db: Session,
    *,
    user_external_id: str,
    local_date: str,
) -> Any:
    def _execute(**kwargs: Any) -> list[dict[str, Any]]:
        user = get_or_create_user(db, user_external_id)
        results: list[dict[str, Any]] = []
        for raw_call in list(kwargs.get("tool_calls") or []):
            tool_name = str(raw_call.get("name") or raw_call.get("tool_name") or "").strip()
            if tool_name != "body.record_observation":
                results.append(
                    _body_observation_tool_result(
                        tool_name=tool_name or "unknown",
                        failure_family="unknown_tool",
                        mutation_result={"status": "blocked"},
                    )
                )
                continue
            arguments = raw_call.get("arguments") if isinstance(raw_call.get("arguments"), dict) else {}
            try:
                value, unit = _coerce_weight_arguments(arguments)
                observation = record_body_observation_to_canonical(
                    db,
                    user=user,
                    value=value,
                    unit=unit,
                    observation_type="weight",
                    local_date=local_date,
                    source="manager_tool_loop",
                    metadata={
                        "source": "manager_tool_loop",
                        "raw_user_input": str(kwargs.get("raw_user_input") or ""),
                    },
                )
            except Exception as exc:
                results.append(
                    _body_observation_tool_result(
                        tool_name="body.record_observation",
                        failure_family="invalid_body_observation_payload",
                        mutation_result={
                            "status": "blocked",
                            "reason": str(exc),
                            "body_observation_recorded": False,
                            "body_plan_mutated": False,
                            "ledger_mutated": False,
                        },
                    )
                )
                continue
            results.append(
                _body_observation_tool_result(
                    tool_name="body.record_observation",
                    evidence={
                        "recorded_body_observation": _serialize_observation(observation),
                    },
                    mutation_result={
                        "status": "recorded",
                        "body_observation_recorded": True,
                        "body_plan_mutated": False,
                        "ledger_mutated": False,
                    },
                )
            )
        return results

    return _execute


def body_observation_guard(
    *,
    manager_payload: dict[str, Any],
    tool_results: list[dict[str, Any]],
    resolved_state: Any,
) -> dict[str, Any]:
    del resolved_state
    success_result = None
    for item in tool_results:
        if not isinstance(item, dict):
            continue
        provenance = item.get("provenance") if isinstance(item.get("provenance"), dict) else {}
        if str(provenance.get("canonical_tool_name") or item.get("tool_name") or "") != "body.record_observation":
            continue
        mutation_result = item.get("mutation_result") if isinstance(item.get("mutation_result"), dict) else {}
        if mutation_result.get("body_observation_recorded") is True:
            success_result = item
            break
    if success_result is None:
        return {
            "ok": False,
            "failure_family": "body_observation_missing_successful_tool_result",
            "repair_request": True,
            "required_tool": "body.record_observation",
            "deterministic_semantic_authority": False,
        }
    success_mutation = (
        success_result.get("mutation_result")
        if isinstance(success_result.get("mutation_result"), dict)
        else {}
    )
    if success_mutation.get("body_plan_mutated") or success_mutation.get("ledger_mutated"):
        return {"ok": False, "failure_family": "body_observation_forbidden_plan_or_ledger_mutation"}
    if str(manager_payload.get("intent_type") or "") != "body_observation":
        return {"ok": False, "failure_family": "body_observation_intent_type_mismatch"}
    if str(manager_payload.get("workflow_effect") or "") != "record_weight":
        return {"ok": False, "failure_family": "body_observation_workflow_effect_mismatch"}
    return {
        "ok": True,
        "selected_tool": "body.record_observation",
        "body_observation_recorded": True,
        "body_plan_mutated": False,
        "ledger_mutated": False,
    }


__all__ = [
    "body_observation_guard",
    "build_body_observation_tool_executor",
]
