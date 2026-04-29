from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.budget.application.current_budget_answer import RemainingBudgetAnswerContract
from app.intake.application.attachment_resolver import resolve_attachment_decision
from app.intake.application.boundary_output_honesty import (
    enforce_budget_output_honesty,
    enforce_intake_output_honesty,
)
from app.intake.application.commit_boundary_preflight import run_commit_boundary_preflight
from app.intake.application.context_injection_policy import build_manager_context_pack
from app.intake.application.current_turn_context_assembler import build_current_turn_context_v1
from app.intake.application.history_expansion_runtime import activate_pre_manager_history_expansion
from app.intake.application.history_expansion_manager_runtime import (
    PHASE_A_EXPAND_HISTORY_TOOL,
    activate_manager_triggered_history_expansion,
)
from app.intake.application.phase_a_boundary_projection import (
    build_budget_boundary_projection,
    build_intake_boundary_projection,
)
from app.intake.application.shadow_hypothesis_runtime import build_shadow_hypothesis_runtime
from app.intake.application.transition_guard import resolve_transition_guard
from app.runtime.application.manager_service import run_intake_manager
from app.runtime.contracts.phase_a import AttachmentDecision, TransitionGuardResult
from app.shared.contracts.intake_results import EstimatePayload


@dataclass(frozen=True)
class _PersistenceResult:
    action: str | None = None
    canonical_commit: dict | None = None


def _payload(
    *,
    meal_title: str,
    estimated_kcal: int,
    action_taken: str,
    follow_up_needed: bool = False,
    followup_question: str | None = None,
    response_mode_hint: str = "rough_estimate_ok",
    missing_slots: list[str] | None = None,
    unresolved_info: list[str] | None = None,
    canonical_write_allowed: bool = True,
) -> EstimatePayload:
    return EstimatePayload(
        request_id="req-phase-a-closure",
        meal_title=meal_title,
        estimated_kcal=estimated_kcal,
        action_taken=action_taken,
        follow_up_needed=follow_up_needed,
        followup_question=followup_question,
        route_target="clarify_user_private" if action_taken == "clarify_before_estimate" else "direct_answer",
        trace_contract={
            "response_mode_hint": response_mode_hint,
            "missing_slots": list(missing_slots or []),
            "unresolved_info": list(unresolved_info or []),
            "followup_question": followup_question,
            "canonical_write_decision": {"can_write_canonical": canonical_write_allowed},
        },
        reasoning_state={"missing_high_impact_slots": list(missing_slots or [])},
    )


def _meal_chunk(
    *,
    meal_id: int,
    meal_thread_id: int,
    meal_version_id: int,
    title: str,
    content: str,
    timestamp: str,
    local_date: str,
    matched_terms: list[str],
    relative_time_label: str | None = None,
) -> dict[str, object]:
    return {
        "chunk_id": f"meal:{meal_id}",
        "source_type": "meal_record",
        "source_id": meal_id,
        "content": content,
        "timestamp": timestamp,
        "linked_meal_id": meal_id,
        "score": 10.0,
        "matched_terms": matched_terms,
        "metadata": {
            "title": title,
            "meal_thread_id": meal_thread_id,
            "meal_version_id": meal_version_id,
            "local_date": local_date,
            "relative_time_label": relative_time_label,
        },
    }


def _resolved_state(
    *,
    local_date: str = "2026-04-29",
    pending_followup: dict[str, object] | None = None,
    retrieved_meal_records: list[dict[str, object]] | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        onboarding_ready=True,
        user_id=1,
        user_external_id="phase-a-closure-user",
        local_date=local_date,
        active_body_plan_view=None,
        current_budget_view=None,
        conversation_state=SimpleNamespace(
            retrieved_meal_records=retrieved_meal_records or [],
            historical_meal_chunks=[],
            transcript_chunks=[],
            session_summary=SimpleNamespace(),
        ),
        injected_context={
            "ACTIVE_MEAL": None,
            "PENDING_FOLLOWUP": pending_followup
            or {
                "is_open": False,
                "meal_id": None,
                "meal_thread_id": None,
                "pending_question": None,
            },
            "RECENT_COMMITTED_MEALS_SUMMARY": [],
            "TARGET_MEAL_REFERENCE": {
                "meal_thread_id": None,
                "meal_version_id": None,
                "meal_title": None,
                "target_resolution_source": "none",
                "correction_confidence": "low",
            },
            "SESSION_SUMMARY": {},
        },
    )


def test_phase_a_ms2_projection_closes_clarify_posture_cases() -> None:
    milk_tea = build_intake_boundary_projection(
        payload=_payload(
            meal_title="pearl milk tea",
            estimated_kcal=450,
            action_taken="answer_with_uncertainty",
            follow_up_needed=True,
            followup_question="What size and sugar level was it?",
            missing_slots=["size", "sugar_level"],
            canonical_write_allowed=False,
        ),
        persistence_result=_PersistenceResult(action="save_draft_log"),
        active_body_plan_present=True,
    )
    homemade = build_intake_boundary_projection(
        payload=_payload(
            meal_title="home cooked dish",
            estimated_kcal=0,
            action_taken="clarify_before_estimate",
            follow_up_needed=True,
            followup_question="What dishes or ingredients and how much?",
            response_mode_hint="clarify_first",
            unresolved_info=["dishes_or_ingredients", "portion"],
            canonical_write_allowed=False,
        ),
        persistence_result=_PersistenceResult(action="save_draft_log"),
        active_body_plan_present=True,
    )

    assert milk_tea.clarification_decision.mode == "estimate_with_followup"
    assert milk_tea.clarification_decision.followup_required is True
    assert milk_tea.clarification_decision.provisional_range_allowed is True
    assert milk_tea.commit_boundary_decision.intent == "draft"
    assert homemade.clarification_decision.mode == "clarify_before_estimate"
    assert homemade.clarification_decision.provisional_range_allowed is False
    assert homemade.commit_boundary_decision.intent == "draft"


def test_phase_a_ms7_blocks_false_commit_and_normalizes_structured_output() -> None:
    payload = _payload(
        meal_title="pearl milk tea",
        estimated_kcal=450,
        action_taken="answer_with_uncertainty",
        follow_up_needed=True,
        followup_question="What size and sugar level was it?",
        canonical_write_allowed=False,
    )
    preflight = run_commit_boundary_preflight(
        payload=payload,
        manager_final_action="commit",
        active_body_plan_present=True,
    )
    projection = build_intake_boundary_projection(
        payload=payload,
        persistence_result=None,
        active_body_plan_present=True,
    )
    state_delta = {
        "meal_logged": True,
        "canonical_commit": True,
        "draft_saved": False,
        "new_meal_version_created": True,
        "old_version_superseded": True,
        "ledger_updated": True,
    }

    output = enforce_intake_output_honesty(
        assistant_message="Logged. pearl milk tea 450 kcal.",
        state_delta=state_delta,
        sidecar={"state_mutation_summary": dict(state_delta)},
        phase_a_trace={
            "phase_a_commit_boundary_preflight": preflight.trace_payload(),
            "boundary_projection": projection.model_dump(mode="json"),
        },
        manager_final_action="no_commit",
        persistence_result=None,
    )

    assert preflight.blocked is True
    assert preflight.failure_family == "phase_a_commit_boundary_blocked"
    assert output.state_delta["canonical_commit"] is False
    assert output.state_delta["ledger_updated"] is False
    assert output.sidecar["state_mutation_summary"]["meal_logged"] is False
    assert output.phase_a_trace["phase_a_output_honesty"]["normalized"] is True
    assert output.phase_a_trace["phase_a_output_honesty"]["structured_sources"]


def test_phase_a_ms7_history_activation_enriches_context_without_manager_trigger_capability() -> None:
    resolved_state = _resolved_state(
        retrieved_meal_records=[
            _meal_chunk(
                meal_id=501,
                meal_thread_id=77,
                meal_version_id=88,
                title="milk tea",
                content="milk tea bubble tea half sugar",
                timestamp="2026-04-29T09:00:00Z",
                local_date="2026-04-29",
                matched_terms=["milk", "tea"],
                relative_time_label="today",
            )
        ],
    )
    context = build_current_turn_context_v1(
        raw_user_input="actually change that milk tea to half sugar",
        resolved_state=resolved_state,
    )
    pre_attachment = resolve_attachment_decision(context)
    pre_guard = resolve_transition_guard(context, pre_attachment)

    activation = activate_pre_manager_history_expansion(
        current_turn_context=context,
        resolved_state=resolved_state,
        pre_attachment_decision=pre_attachment,
        pre_transition_guard_result=pre_guard,
    )
    manager_pack = build_manager_context_pack(current_turn_context=activation.enriched_current_turn_context)

    assert activation.applied is True
    assert activation.resolution_gain is True
    assert activation.post_attachment_decision.disposition == "target_committed_thread"
    assert activation.selected_candidate_ids == ("77",)
    assert manager_pack.manager_context["candidate_attachment_targets"][0]["target_object_id"] == "77"


def test_phase_a_ms14_no_plan_fallback_uses_structured_honesty_not_reply_wording() -> None:
    answer = RemainingBudgetAnswerContract(
        status="onboarding_required",
        user_id=1,
        local_date="2026-04-29",
        daily_target_kcal=0,
        consumed_kcal=600,
        remaining_kcal=500,
        meal_count=2,
    )
    projection = build_budget_boundary_projection(
        remaining_budget=answer,
        active_body_plan_present=False,
        observed_reply_text="You have remaining 500 kcal today.",
    )
    output = enforce_budget_output_honesty(
        reply_text="You have remaining 500 kcal today.",
        remaining_budget=answer,
        active_body_plan_present=False,
        phase_a_trace={"boundary_projection": projection.model_dump(mode="json")},
    )

    assert projection.fallback_honesty_decision.budget_answer_mode == "degraded"
    assert projection.fallback_honesty_decision.concrete_remaining_kcal_allowed is False
    assert output.phase_a_trace["phase_a_output_honesty"]["concrete_remaining_kcal_allowed"] is False
    assert output.phase_a_trace["phase_a_output_honesty"]["normalized"] is True
    assert "500" not in output.reply_text


class _ManagerPayloadProvider:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def readiness(self) -> dict[str, object]:
        return {"configured": True}

    async def complete_with_trace(self, **kwargs: object) -> tuple[dict[str, object], dict[str, object]]:
        self.calls.append(dict(kwargs))
        return (
            {
                "manager_action": "final",
                "intent": "log_meal",
                "final_action": "no_commit",
                "workflow_effect": "safe_failure",
                "target_attachment": {"mode": "existing_meal", "target_id": "77"},
                "exactness": "anchored",
                "confidence": "medium",
                "evidence_posture": "generic_with_uncertainty",
                "repair_ack": False,
                "answer_contract": {"reply_text": "ok"},
                "uncertainty_posture": "bounded",
                "evidence_honesty_posture": "generic_with_uncertainty",
            },
            {"source": "fake"},
        )


@pytest.mark.asyncio
async def test_phase_a_manager_payload_keeps_history_manager_trigger_disabled_after_enrichment() -> None:
    resolved_state = _resolved_state(
        retrieved_meal_records=[
            _meal_chunk(
                meal_id=501,
                meal_thread_id=77,
                meal_version_id=88,
                title="milk tea",
                content="milk tea bubble tea half sugar",
                timestamp="2026-04-29T09:00:00Z",
                local_date="2026-04-29",
                matched_terms=["milk", "tea"],
            )
        ],
    )
    context = build_current_turn_context_v1(
        raw_user_input="actually change that milk tea to half sugar",
        resolved_state=resolved_state,
    )
    activation = activate_pre_manager_history_expansion(
        current_turn_context=context,
        resolved_state=resolved_state,
    )
    provider = _ManagerPayloadProvider()

    await run_intake_manager(
        provider=provider,
        raw_user_input="actually change that milk tea to half sugar",
        resolved_state=resolved_state,
        current_turn_context=activation.enriched_current_turn_context,
        manager_context_pack=build_manager_context_pack(current_turn_context=activation.enriched_current_turn_context),
        available_tools=("resolve_correction_target",),
    )

    payload = provider.calls[0]["user_payload"]
    assert isinstance(payload, dict)
    assert payload["phase_a_history_expansion_enabled"] is False
    assert "history_expansion_request" not in payload
    assert payload["phase_a_manager_context_pack"]["manager_context"]["candidate_attachment_targets"][0]["target_object_id"] == "77"


@pytest.mark.asyncio
async def test_phase_a_shadow_payload_and_dialogue_are_non_authoritative_closure() -> None:
    resolved_state = _resolved_state(
        retrieved_meal_records=[],
    )
    resolved_state.injected_context["RECENT_COMMITTED_MEALS_SUMMARY"] = [
        {
            "meal_thread_id": 77,
            "meal_version_id": 88,
            "meal_title": "milk tea",
            "local_date": "2026-04-29",
        }
    ]
    context = build_current_turn_context_v1(
        raw_user_input="that milk tea half sugar",
        resolved_state=resolved_state,
    )
    attachment = AttachmentDecision(
        disposition="answer_only",
        target_object_type="none",
        target_object_id=None,
        reason="no_attachment_signal",
        confidence="low",
        ambiguity_flag=True,
        allowed_transition_class="none",
    )
    guard = TransitionGuardResult(
        verdict="answer_only",
        reason="no_state_mutation_allowed",
        blocked_mutation="meal_mutation",
        affected_object_type="none",
        affected_object_id=None,
    )
    shadow_runtime = build_shadow_hypothesis_runtime(
        current_turn_context=context,
        attachment_decision=attachment,
        transition_guard_result=guard,
    )
    provider = _ManagerPayloadProvider()

    await run_intake_manager(
        provider=provider,
        raw_user_input="that milk tea half sugar",
        resolved_state=resolved_state,
        current_turn_context=context,
        manager_context_pack=build_manager_context_pack(current_turn_context=context),
        phase_a_shadow_hypothesis=shadow_runtime.manager_payload,
        available_tools=("resolve_correction_target",),
    )

    payload = provider.calls[0]["user_payload"]
    assert shadow_runtime.manager_payload["role"] == "tentative_non_authoritative"
    assert shadow_runtime.manager_payload["mutation_authority"] is False
    assert payload["phase_a_shadow_hypothesis"]["candidate_target_object_id"] == "77"
    assert "target_object_id" not in payload["phase_a_shadow_hypothesis"]
    assert payload["phase_a_shadow_hypothesis_instruction"]["must_not_authorize_mutation"] is True


def test_phase_a_manager_triggered_history_is_active_local_only_closure() -> None:
    resolved_state = _resolved_state(
        retrieved_meal_records=[
            _meal_chunk(
                meal_id=501,
                meal_thread_id=77,
                meal_version_id=88,
                title="milk tea",
                content="milk tea bubble tea half sugar",
                timestamp="2026-04-29T09:00:00Z",
                local_date="2026-04-29",
                matched_terms=["milk", "tea"],
            )
        ],
    )
    context = build_current_turn_context_v1(
        raw_user_input="that milk tea half sugar",
        resolved_state=resolved_state,
    )
    expansion = activate_manager_triggered_history_expansion(
        current_turn_context=context,
        resolved_state=resolved_state,
    )

    assert PHASE_A_EXPAND_HISTORY_TOOL == "phase_a_expand_history"
    assert expansion.attempted is True
    assert expansion.tool_result()["provenance"]["phase_a_owner"] == "intake/application"
    assert expansion.tool_result()["mutation_result"] == {}
    assert expansion.tool_result()["evidence"]["history_expansion_result"]["transcript_snippets"] == []


def test_phase_a_runtime_docs_mark_slice11_active_and_provider_history_deferred() -> None:
    spec = Path("docs/specs/V2_WAVE_1_MINIMAL_IMPLEMENTATION_CONTRACTS.md").read_text(encoding="utf-8-sig")
    bootstrap = Path("docs/specs/V2_WAVE_1_CODING_AGENT_BOOTSTRAP.md").read_text(encoding="utf-8-sig")

    assert "`Slice 11`: manager-triggered history expansion is active" in spec
    assert "provider-side history tools and provider/tool-loop protocol redesign remain deferred" in spec
    assert "manager-triggered history expansion remains deferred" not in bootstrap


def test_phase_c_projection_baseline_docs_are_active_and_enforcement_deferred() -> None:
    spec = Path("docs/specs/V2_WAVE_1_MINIMAL_IMPLEMENTATION_CONTRACTS.md").read_text(encoding="utf-8-sig")
    bootstrap = Path("docs/specs/V2_WAVE_1_CODING_AGENT_BOOTSTRAP.md").read_text(encoding="utf-8-sig")

    assert "Phase C Mutation Projection Baseline" in spec
    assert "`phase_c_trace` is the active diagnostic surface" in spec
    assert "missing Phase C values must be emitted as `not_available`" in spec
    assert "Phase C enforcement and UI same-truth remain deferred" in spec
    assert "Phase C projection baseline is active" in bootstrap


def test_phase_c_same_truth_gate_docs_are_active_without_runtime_repair() -> None:
    spec = Path("docs/specs/V2_WAVE_1_MINIMAL_IMPLEMENTATION_CONTRACTS.md").read_text(encoding="utf-8-sig")
    bootstrap = Path("docs/specs/V2_WAVE_1_CODING_AGENT_BOOTSTRAP.md").read_text(encoding="utf-8-sig")

    assert "Phase C Structured Same-Truth Closure Gate" in spec
    assert "`same_truth_closure_gate` is active as hard-fail evidence" in spec
    assert "status: pass | flagged | hard_fail" in spec
    assert "must not rewrite, repair, or block runtime output" in spec
    assert "Phase C structured same-truth closure gate is active" in bootstrap
