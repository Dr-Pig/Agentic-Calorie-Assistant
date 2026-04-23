from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
import re
from typing import Any

from sqlalchemy.orm import Session

from ...nutrition.agent.exact_item_packets import build_exact_item_lane_packet
from .commit_service import persist_text_meal_payload
from ...shared.time_labels import resolve_local_attribution
from ...shared.domain import ConversationState
from ...database import get_or_create_user
from ...logging import now_iso
from ...runtime.infrastructure.trace.stage_trace_store import append_stage_trace_event
from ...shared.contracts.intake import ComponentEstimate, EstimatePayload
from ...nutrition.application.evidence_eligibility import classify_query_family, is_high_variance_family
from ...nutrition.application.estimate_artifacts import (
    EstimatedNutritionArtifact,
    build_exact_item_artifact,
    build_shadow_stub_artifact,
    shadow_stub_estimate_enabled,
)


@dataclass(frozen=True)
class PersistMealLogResult:
    action: str
    status: str | None
    persisted_log_id: int | None
    linked_meal_log_id: int | None
    canonical_commit: dict[str, Any] | None


def _conversation_pending_followup(conversation_state: ConversationState | Any) -> dict[str, Any]:
    pending = getattr(conversation_state, "pending_followup_state", None)
    if pending is None:
        return {
            "is_open": False,
            "source_meal_id": None,
            "pending_question": None,
            "missing_high_impact_slots": [],
        }
    if hasattr(pending, "model_dump"):
        return pending.model_dump(mode="json")
    return dict(pending)


def _trace_slots(trace_contract: dict[str, Any], key: str) -> list[str]:
    return [str(item) for item in trace_contract.get(key, []) if str(item).strip()]


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


_GENERIC_MILK_TEA_TOKENS = ("珍珠奶茶", "奶茶", "milk tea", "bubble tea")
_BRAND_PACKAGE_TOKENS = ("7-11", "city cafe", "全家", "familymart", "coco", "50嵐", "五十嵐", "可不可", "麻古")
_SIZE_TOKENS = ("大杯", "中杯", "小杯", "l杯", "m杯", "s杯", "大", "中", "小")
_SWEETNESS_TOKENS = ("全糖", "半糖", "微糖", "少糖", "無糖", "正常糖")
_COUNT_ANCHOR_PATTERN = re.compile(r"\d+\s*(顆|個|粒|份|pcs?|pieces?)", re.IGNORECASE)
_MULTI_ITEM_SPLIT_TOKENS = ("\u548c", "\u3001", ",", "\uff0c", "\u9084\u6709", "+")


def _looks_like_generic_milk_tea(raw_user_input: str) -> bool:
    normalized = raw_user_input.strip().lower()
    return any(token in normalized for token in _GENERIC_MILK_TEA_TOKENS) or classify_query_family(raw_user_input) == "generic_milk_tea"


def _has_brand_or_package_cue(raw_user_input: str) -> bool:
    normalized = raw_user_input.strip().lower()
    return any(token in normalized for token in _BRAND_PACKAGE_TOKENS)


def _has_structuring_drink_details(raw_user_input: str) -> bool:
    normalized = raw_user_input.strip().lower()
    return any(token in normalized for token in _SIZE_TOKENS) and any(token in normalized for token in _SWEETNESS_TOKENS)


def _has_count_anchor(raw_user_input: str) -> bool:
    normalized = raw_user_input.strip().lower()
    return bool(_COUNT_ANCHOR_PATTERN.search(normalized))


def _looks_like_multi_item_input(raw_user_input: str) -> bool:
    normalized = str(raw_user_input or "").strip().lower()
    if any(token in normalized for token in _MULTI_ITEM_SPLIT_TOKENS):
        return True
    quantity_markers = ["一碗", "一杯", "一顆", "一個", "一份"]
    return sum(1 for token in quantity_markers if token in normalized) >= 2


def _normalize_bundle1_live_payload(payload: EstimatePayload, *, raw_user_input: str) -> None:
    """Bridge V1 nutrition payloads into Bundle 1 execution semantics.

    Bundle 1 expects simple completed meals to:
    - surface item-level kcal in the renderer
    - commit canonically when the payload is best-effort but not actually asking a follow-up
    """

    if (
        payload.component_breakdown
        and (
            not payload.component_estimates
            or all(int(component.estimated_kcal or 0) <= 0 for component in payload.component_estimates)
        )
    ):
        payload.component_estimates = [
            ComponentEstimate(
                name=str(item.get("name") or "item"),
                quantity_hint=str(item.get("quantity_hint") or item.get("portion_basis") or "").strip() or None,
                estimated_kcal=int(item.get("estimated_kcal") or 0),
                protein_g=int(item.get("protein_g") or 0),
                carb_g=int(item.get("carb_g") or 0),
                fat_g=int(item.get("fat_g") or 0),
            )
            for item in payload.component_breakdown
            if int(item.get("estimated_kcal") or 0) > 0
        ]

    trace_contract = payload.trace_contract
    has_followup = bool(payload.followup_question) or bool(_trace_slots(trace_contract, "unresolved_info"))
    has_blocking = bool(_trace_slots(trace_contract, "blocking_slots"))
    has_missing = bool(_trace_slots(trace_contract, "missing_slots"))
    clarify_first = str(trace_contract.get("response_mode_hint") or "") == "clarify_first"

    if (
        payload.estimated_kcal > 0
        and payload.route_target == "clarify_user_private"
        and not has_followup
        and not has_blocking
        and not has_missing
        and not clarify_first
    ):
        payload.route_target = "best_effort_answer"

    if (
        payload.estimated_kcal > 0
        and payload.action_taken == "answer_with_uncertainty"
        and not has_followup
        and not has_blocking
        and not has_missing
    ):
        payload.follow_up_needed = False

    family_rule = classify_query_family(raw_user_input)
    if (
        payload.estimated_kcal > 0
        and is_high_variance_family(raw_user_input)
        and not _has_brand_or_package_cue(raw_user_input)
        and not _has_structuring_drink_details(raw_user_input)
        and not _has_count_anchor(raw_user_input)
    ):
        payload.route_target = "clarify_user_private"
        payload.action_taken = "answer_with_uncertainty"
        payload.follow_up_needed = True
        if not str(payload.followup_question or "").strip():
            if family_rule == "generic_milk_tea" or _looks_like_generic_milk_tea(raw_user_input):
                payload.followup_question = "請問是幾分糖、什麼杯型？"
            elif family_rule == "dumpling_count_required":
                payload.followup_question = "請問大概吃了幾顆？"
            else:
                payload.followup_question = "我還需要更完整的組成或份量，才能把這餐記準。"
        payload.trace_contract = {
            **dict(payload.trace_contract or {}),
            "bundle2_guard_family": family_rule or "high_variance_followup_required",
            "why_not_exact": ["high_variance_family_requires_followup", "missing_identity_or_customization"],
        }

    # Generic hand-shaken milk tea without brand/package or size/sweetness cues must not
    # be treated as exact-item truth. Demote to follow-up-required so Bundle 2 can ask for
    # the high-impact drink details before canonical commit.
    if (
        payload.estimated_kcal > 0
        and False
        and not _has_brand_or_package_cue(raw_user_input)
        and not _has_structuring_drink_details(raw_user_input)
    ):
        payload.route_target = "clarify_user_private"
        payload.action_taken = "answer_with_uncertainty"
        payload.follow_up_needed = True
        if not str(payload.followup_question or "").strip():
            payload.followup_question = "請問是幾分糖、什麼杯型？"
        payload.trace_contract = {
            **dict(payload.trace_contract or {}),
            "bundle2_guard_family": "legacy_disabled_high_variance_guard",
        }


def read_body_plan_tool(db: Session, *, user_id: int) -> Any:
    from ...body.application import build_active_body_plan_view

    return build_active_body_plan_view(db, user_id=user_id)


def read_day_budget_tool(db: Session, *, user_id: int, local_date: str) -> Any:
    from ...budget.application import build_current_budget_view

    return build_current_budget_view(db, user_id=user_id, local_date=local_date)


def read_active_meal_tool(db: Session, *, user_id: int, local_date: str) -> dict[str, Any] | None:
    budget = read_day_budget_tool(db, user_id=user_id, local_date=local_date)
    if not budget.meals:
        return None
    latest_meal = max(
        budget.meals,
        key=lambda meal: meal.occurred_at.isoformat() if meal.occurred_at is not None else "",
    )
    return {
        "meal_thread_id": latest_meal.meal_thread_id,
        "meal_version_id": latest_meal.meal_version_id,
        "meal_title": latest_meal.meal_title,
        "total_kcal": latest_meal.total_kcal,
    }


def append_trace_event_tool(
    *,
    request_id: str,
    stage: str,
    status: str,
    summary: dict[str, Any],
) -> None:
    append_stage_trace_event(
        request_id,
        {
            "request_id": request_id,
            "stage": stage,
            "status": status,
            "timestamp": now_iso(),
            "summary": _json_safe(summary),
        },
    )


def resolve_correction_target_tool(
    *,
    resolved_state: Any,
) -> dict[str, Any]:
    target = ((resolved_state.injected_context or {}).get("TARGET_MEAL_REFERENCE") or {}).copy()
    pending = _conversation_pending_followup(getattr(resolved_state, "conversation_state", None))
    if pending.get("is_open"):
        target["target_resolution_source"] = "pending_followup_state"
        target["correction_confidence"] = "high"
    return target


def compare_against_budget_tool(
    *,
    current_budget_view: Any,
    estimated_kcal: int,
    replaced_kcal: int = 0,
) -> dict[str, Any]:
    consumed_before = int(current_budget_view.consumed_kcal or 0)
    budget_kcal = int(current_budget_view.budget_kcal or 0)
    predicted_consumed = max(consumed_before - max(int(replaced_kcal or 0), 0), 0) + max(int(estimated_kcal or 0), 0)
    predicted_remaining = budget_kcal - predicted_consumed
    return {
        "budget_kcal": budget_kcal,
        "consumed_kcal_before": consumed_before,
        "replaced_kcal_before": max(int(replaced_kcal or 0), 0),
        "predicted_consumed_kcal_after": predicted_consumed,
        "predicted_remaining_kcal_after": predicted_remaining,
        "overshoot_detected": predicted_remaining < 0,
        "overshoot_kcal": abs(min(predicted_remaining, 0)),
    }


async def estimate_nutrition_tool(
    db: Session,
    *,
    user_external_id: str,
    raw_user_input: str,
    request_id: str,
    local_date: str,
    manager_provider: Any | None = None,
    provider: Any | None = None,
    search_adapter: Any | None = None,
    allow_search: bool = True,
    force_new_meal_context: bool = False,
    contextualized_query: str | None = None,
) -> EstimatedNutritionArtifact:
    active_provider = manager_provider or provider

    exact_packet = build_exact_item_lane_packet(raw_user_input, limit=3)
    top_exact_candidate = exact_packet.get("top_exact_candidate")
    if isinstance(top_exact_candidate, dict) and not _looks_like_multi_item_input(raw_user_input):
        artifact = build_exact_item_artifact(
            db,
            user_external_id=user_external_id,
            raw_user_input=raw_user_input,
            local_date=local_date or datetime.now().date().isoformat(),
            exact_candidate=top_exact_candidate,
        )
        _normalize_bundle1_live_payload(artifact.payload, raw_user_input=raw_user_input)
        return artifact

    if shadow_stub_estimate_enabled(provider=active_provider):
        return build_shadow_stub_artifact(
            db,
            user_external_id=user_external_id,
            raw_user_input=raw_user_input,
            local_date=local_date or datetime.now().date().isoformat(),
        )

    artifact = build_shadow_stub_artifact(
        db,
        user_external_id=user_external_id,
        raw_user_input=raw_user_input,
        local_date=local_date or datetime.now().date().isoformat(),
    )
    if force_new_meal_context:
        if hasattr(artifact.runtime_context, "latest_log"):
            artifact.runtime_context.latest_log = None
        if hasattr(artifact.runtime_context, "conversation_state"):
            conversation_state = getattr(artifact.runtime_context, "conversation_state")
            if conversation_state is not None and hasattr(conversation_state, "pending_followup_state"):
                pending_state = getattr(conversation_state, "pending_followup_state")
                if pending_state is not None and hasattr(pending_state, "is_open"):
                    pending_state.is_open = False
    trace_contract = dict(artifact.payload.trace_contract or {})
    if not str(trace_contract.get("local_date") or "").strip():
        attribution = resolve_local_attribution(
            trace_contract.get("occurred_at"),
            timezone_name=str(trace_contract.get("timezone") or "") or None,
        )
        if attribution.get("occurred_at") is not None:
            trace_contract["occurred_at"] = attribution["occurred_at"]
        if str(attribution.get("occurred_at_utc") or "").strip():
            trace_contract["occurred_at_utc"] = attribution["occurred_at_utc"]
        if str(attribution.get("occurred_at_local") or "").strip():
            trace_contract["occurred_at_local"] = attribution["occurred_at_local"]
        if str(attribution.get("local_date") or "").strip():
            trace_contract["local_date"] = attribution["local_date"]
        if str(attribution.get("timezone") or "").strip():
            trace_contract["timezone"] = attribution["timezone"]
    trace_contract.setdefault("search_attempt_count", 0)
    trace_contract.setdefault("grounding_summary", {"exact_truth_present": False, "retrieved_knowledge_count": 0, "evidence_roles": []})
    trace_contract.setdefault("reasoning_state", {"exact_lane_count": 0, "search_attempt_count": 0})
    artifact.payload.trace_contract = trace_contract
    _normalize_bundle1_live_payload(artifact.payload, raw_user_input=raw_user_input)
    return artifact


def persist_meal_log_tool(
    db: Session,
    *,
    artifact: EstimatedNutritionArtifact,
    request_id: str,
) -> PersistMealLogResult:
    user = artifact.runtime_context.user or get_or_create_user(db, artifact.request.user_id)
    decision = persist_text_meal_payload(
        db=db,
        user=user,
        latest_log=artifact.runtime_context.latest_log,
        planner_intent=artifact.planner_result.intent,
        payload=artifact.payload,
        raw_input=artifact.request.text,
        request_id=request_id,
        incoming_user_message_id=artifact.runtime_context.incoming_user_message_id,
        conversation_state=artifact.runtime_context.conversation_state,
        planner_result=artifact.planner_result,
    )
    return PersistMealLogResult(
        action=str(decision.get("action") or "noop"),
        status=decision.get("status"),
        persisted_log_id=decision.get("persisted_log_id"),
        linked_meal_log_id=decision.get("linked_meal_log_id"),
        canonical_commit=decision.get("canonical_commit"),
    )
