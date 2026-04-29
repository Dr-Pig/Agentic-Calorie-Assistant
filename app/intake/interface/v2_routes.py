from __future__ import annotations

from datetime import datetime
import time
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from ..application import V2Bundle1OnboardingPayload, execute_bundle1_turn
from ..application.attachment_resolver import resolve_attachment_decision
from ..application.current_turn_context_assembler import build_current_turn_context_v1
from ..application.phase_a_trace import build_phase_a_trace
from ..application.transition_guard import resolve_transition_guard
from ...database import get_db
from ...runtime.application.state_resolver import resolve_v2_bundle1_state
from ...runtime.interface.provider_runtime import extract_provider, manager_provider, search_provider

router = APIRouter()


class V2OnboardingPayload(BaseModel):
    sex: str
    age_years: int
    height_cm: float
    current_weight_kg: float
    activity_level: str | None = None
    daily_lifestyle: str | None = None
    weekly_exercise_days_band: str | None = None
    goal_type: str
    weekly_target_rate_kg: float = 0.5
    timezone: str = "UTC"
    target_weight_kg: float | None = None


class V2EstimateRequest(BaseModel):
    user_id: str = "default_user"
    text: str | None = None
    local_date: str | None = None
    allow_search: bool = True
    onboarding: V2OnboardingPayload | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


def _compute_latency_bucket(total_ms: int) -> str:
    """Compute latency bucket based on total duration."""
    if total_ms < 2000:
        return "<2s"
    elif total_ms < 4000:
        return "2-4s"
    elif total_ms < 8000:
        return "4-8s"
    else:
        return ">8s"


@router.post("/v2/estimate")
async def v2_estimate(req: V2EstimateRequest, db: Any = Depends(get_db)) -> dict[str, Any]:
    print(f"DEBUG: v2_estimate called with {req.text}")
    request_start_ms = int(time.time() * 1000)
    
    try:
        onboarding_payload = (
            V2Bundle1OnboardingPayload(**req.onboarding.model_dump())
            if req.onboarding is not None
            else None
        )
        state_before = None
        phase_a_trace = None
        if req.text:
            resolved_local_date = req.local_date or datetime.now().date().isoformat()
            state_before = resolve_v2_bundle1_state(
                db,
                user_external_id=req.user_id,
                local_date=resolved_local_date,
                incoming_user_text=req.text,
            )
            current_turn_context = build_current_turn_context_v1(
                raw_user_input=req.text,
                resolved_state=state_before,
            )
            from ..application.history_expansion_runtime import activate_pre_manager_history_expansion

            attachment_decision = resolve_attachment_decision(current_turn_context)
            transition_guard_result = resolve_transition_guard(current_turn_context, attachment_decision)
            activation = activate_pre_manager_history_expansion(
                current_turn_context=current_turn_context,
                resolved_state=state_before,
                pre_attachment_decision=attachment_decision,
                pre_transition_guard_result=transition_guard_result,
            )
            current_turn_context = activation.enriched_current_turn_context
            attachment_decision = activation.post_attachment_decision
            transition_guard_result = activation.post_transition_guard_result
            phase_a_trace = build_phase_a_trace(
                current_turn_context=current_turn_context,
                attachment_decision=attachment_decision,
                transition_guard_result=transition_guard_result,
                history_expansion_activation=activation.trace_payload() if activation.applied else None,
            )
        result = await execute_bundle1_turn(
        db,
        user_external_id=req.user_id,
        raw_user_input=req.text,
        onboarding_payload=onboarding_payload,
        local_date=req.local_date,
        allow_search=req.allow_search,
        manager_provider=manager_provider,
        search_port=search_provider,
        extract_port=extract_provider,
        state_before=state_before,
        current_turn_context=current_turn_context if req.text else None,
        phase_a_trace=phase_a_trace,
        )
        
        # Compute total latency tracking (including route-level overhead)
        request_end_ms = int(time.time() * 1000)
        total_duration_ms = request_end_ms - request_start_ms
        
        # Use service-level latency_tracking and add total duration
        latency_tracking = result.get("latency_tracking", {})
        latency_tracking["total_duration_ms"] = total_duration_ms
        latency_tracking["latency_bucket"] = _compute_latency_bucket(total_duration_ms)
        result["latency_tracking"] = latency_tracking
        
        return result
    except Exception as exc:
        print(f"CRITICAL ERROR in v2_estimate: {str(exc)}")
        import traceback
        traceback.print_exc()
        return {"error": str(exc), "traceback": traceback.format_exc(), "status": "error"}
