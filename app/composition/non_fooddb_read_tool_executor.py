from __future__ import annotations

from dataclasses import asdict, is_dataclass
import json
from typing import Any

from app.composition.app_usage_question_policy import build_app_usage_question_policy
from sqlalchemy.orm import Session

from app.composition.current_budget_answer import (
    build_remaining_budget_answer_contract_from_views,
)
from app.composition.intake_read_tools import (
    read_body_plan_tool,
    read_calibration_pending_proposal_tool,
    read_day_budget_tool,
    read_latest_weight_observation_tool,
)


_PUBLIC_TO_INTERNAL_TOOL_KEY = {
    "budget.get_today_summary": "read_day_budget",
    "budget.get_remaining_calories": "read_day_budget",
    "budget.get_day_meal_log": "read_day_budget",
    "body.get_active_plan": "read_body_plan",
    "body.get_latest_observation": "read_latest_weight_observation",
    "calibration.get_pending_proposal": "read_calibration_pending_proposal",
    "app.answer_usage_question": "answer_usage_question",
}


_LEGACY_TO_PUBLIC_CANONICAL_NAME = {
    "read_day_budget": "budget.get_today_summary",
    "read_body_plan": "body.get_active_plan",
    "read_latest_weight_observation": "body.get_latest_observation",
    "read_calibration_pending_proposal": "calibration.get_pending_proposal",
    "answer_usage_question": "app.answer_usage_question",
}


_PUBLIC_TRUTH_OWNER = {
    "budget.get_today_summary": "budget_domain",
    "budget.get_remaining_calories": "budget_domain",
    "budget.get_day_meal_log": "intake_and_budget_projection",
    "body.get_active_plan": "body_domain",
    "body.get_latest_observation": "body_domain",
    "calibration.get_pending_proposal": "calibration_domain",
    "app.answer_usage_question": "app_product_policy",
}


_LEGACY_TRUTH_OWNER = {
    "read_day_budget": "budget_read_model",
    "read_body_plan": "body_read_model",
    "read_latest_weight_observation": "body_read_model",
    "read_calibration_pending_proposal": "calibration_domain",
    "answer_usage_question": "app_product_policy",
}


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if is_dataclass(value):
        return _json_safe(asdict(value))
    if hasattr(value, "model_dump"):
        try:
            return _json_safe(value.model_dump(mode="json"))
        except TypeError:
            return _json_safe(value.model_dump())
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def _result(
    tool_name: str,
    *,
    evidence: dict[str, Any],
    truth_owner: str,
    canonical_tool_name: str | None = None,
    failure_family: str | None = None,
) -> dict[str, Any]:
    return {
        "tool_name": tool_name,
        "evidence": _json_safe(evidence),
        "mutation_result": {},
        "provenance": {
            "truth_owner": truth_owner,
            "tool_kind": "read_only",
            "mutation_authority": False,
            "canonical_tool_name": canonical_tool_name or tool_name,
        },
        "confidence": "available" if failure_family is None else "none",
        "failure_family": failure_family,
    }


def _internal_tool_key(tool_name: str) -> str:
    return _PUBLIC_TO_INTERNAL_TOOL_KEY.get(tool_name, tool_name)


def _canonical_public_tool_name(tool_name: str) -> str:
    return _LEGACY_TO_PUBLIC_CANONICAL_NAME.get(tool_name, tool_name)


def _truth_owner(tool_name: str, internal_tool_key: str) -> str:
    return _PUBLIC_TRUTH_OWNER.get(tool_name) or _LEGACY_TRUTH_OWNER.get(internal_tool_key) or "unknown"


async def execute_non_fooddb_read_tool_calls(
    *,
    db: Session,
    user_id: int,
    local_date: str,
    tool_calls: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for call in tool_calls:
        tool_name = str(call.get("name") or call.get("tool_name") or "").strip()
        canonical_public_tool_name = _canonical_public_tool_name(tool_name)
        internal_tool_key = _internal_tool_key(tool_name)
        if internal_tool_key == "read_day_budget":
            budget_view = read_day_budget_tool(db, user_id=user_id, local_date=local_date)
            active_plan = read_body_plan_tool(db, user_id=user_id)
            remaining_budget = build_remaining_budget_answer_contract_from_views(
                current_budget=budget_view,
                active_plan=active_plan,
            )
            results.append(
                _result(
                    tool_name,
                    evidence={
                        "current_budget_view": budget_view,
                        "active_body_plan_view": active_plan,
                        "remaining_budget_contract": remaining_budget,
                    },
                    truth_owner=_truth_owner(tool_name, internal_tool_key),
                    canonical_tool_name=canonical_public_tool_name,
                )
            )
            continue
        if internal_tool_key == "read_body_plan":
            active_plan = read_body_plan_tool(db, user_id=user_id)
            results.append(
                _result(
                    tool_name,
                    evidence={"active_body_plan_view": active_plan},
                    truth_owner=_truth_owner(tool_name, internal_tool_key),
                    canonical_tool_name=canonical_public_tool_name,
                )
            )
            continue
        if internal_tool_key == "read_latest_weight_observation":
            latest_weight = read_latest_weight_observation_tool(
                db,
                user_id=user_id,
                local_date=local_date,
            )
            results.append(
                _result(
                    tool_name,
                    evidence={
                        "latest_weight_status": "available" if latest_weight is not None else "not_available",
                        "latest_weight_observation": latest_weight,
                    },
                    truth_owner=_truth_owner(tool_name, internal_tool_key),
                    canonical_tool_name=canonical_public_tool_name,
                )
            )
            continue
        if internal_tool_key == "read_calibration_pending_proposal":
            proposals = read_calibration_pending_proposal_tool(db, user_id=user_id)
            results.append(
                _result(
                    tool_name,
                    evidence={
                        "pending_proposal_status": "available" if proposals else "not_available",
                        "proposal_count": len(proposals),
                        "open_calibration_proposals": proposals,
                    },
                    truth_owner=_truth_owner(tool_name, internal_tool_key),
                    canonical_tool_name=canonical_public_tool_name,
                )
            )
            continue
        if internal_tool_key == "answer_usage_question":
            results.append(
                _result(
                    tool_name,
                    evidence={"app_usage_policy": build_app_usage_question_policy()},
                    truth_owner=_truth_owner(tool_name, internal_tool_key),
                    canonical_tool_name=canonical_public_tool_name,
                )
            )
            continue
        results.append(
            _result(
                tool_name or "unknown",
                evidence={},
                truth_owner="unknown",
                canonical_tool_name=canonical_public_tool_name or "unknown",
                failure_family="unknown_tool",
            )
        )
    return results


__all__ = ["execute_non_fooddb_read_tool_calls"]
