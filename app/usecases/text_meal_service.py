from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from ..application.evidence_assembly import (
    build_evidence_bundle as _build_evidence_bundle,
    merge_evidence_items as _merge_evidence_items,
    source_class_for_item as _source_class_for_item,
    to_evidence_candidate as _to_evidence_candidate,
)
from ..application.time_labels import resolve_local_attribution
from ..application.text_meal_commit_service import persist_text_meal_payload
from ..schemas import EstimatePayload, EstimateRequest
from .text_meal_orchestration_support import execute_text_meal_orchestration
from .text_meal_request_support import load_request_runtime_context
from .text_meal_stage_support import pass_envelope as _pass_envelope
from .text_meal_stage_support import run_text_stage as _run_text_stage


async def run_text_meal_canary(
    request: EstimateRequest,
    *,
    provider: Any,
    planner_provider: Any | None = None,
    primary_provider: Any | None = None,
    request_id: str,
    search_adapter: Any | None = None,
    db: Session | None = None,
) -> EstimatePayload:
    runtime_context = load_request_runtime_context(
        request=request,
        db=db,
        provider=provider,
        planner_provider=planner_provider,
        primary_provider=primary_provider,
    )
    orchestration = await execute_text_meal_orchestration(
        request=request,
        request_id=request_id,
        runtime_context=runtime_context,
        search_adapter=search_adapter,
        db=db,
        run_stage=_run_text_stage,
        pass_envelope=_pass_envelope,
        build_evidence_bundle=_build_evidence_bundle,
        merge_evidence_items=_merge_evidence_items,
        source_class_for_item=_source_class_for_item,
        to_evidence_candidate=_to_evidence_candidate,
    )

    if db and runtime_context.user:
        trace_contract = dict(orchestration.payload.trace_contract or {})
        trace_meta = dict(orchestration.payload.trace_meta or {})
        if not str(trace_contract.get("local_date") or "").strip():
            attribution = resolve_local_attribution(
                trace_contract.get("occurred_at") or trace_meta.get("timestamp"),
                timezone_name=str(trace_contract.get("timezone") or trace_meta.get("timezone") or "") or None,
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
            orchestration.payload.trace_contract = trace_contract
        persist_text_meal_payload(
            db=db,
            user=runtime_context.user,
            latest_log=runtime_context.latest_log,
            planner_intent=orchestration.planner_result.intent,
            payload=orchestration.payload,
            raw_input=request.text,
            request_id=request_id,
            incoming_user_message_id=runtime_context.incoming_user_message_id,
            conversation_state=runtime_context.conversation_state,
            planner_result=orchestration.planner_result,
        )

    return orchestration.payload
