from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.intake.application.boundary_output_honesty import SAFE_NO_COMMIT_REPLY
from app.intake.application.shadow_hypothesis_dialogue import (
    apply_shadow_hypothesis_dialogue_cue,
)


def _trace(
    *,
    created: bool = True,
    confidence: str = "medium",
    visibility_posture: str = "uncertainty_visible",
    mutation_authority: bool = False,
) -> dict[str, object]:
    return {
        "shadow_hypothesis_runtime": {
            "created": created,
            "role": "tentative_non_authoritative",
            "candidate_target_object_type": "meal_thread",
            "candidate_target_object_id": "77",
            "intent": "back_reference",
            "confidence": confidence,
            "visibility_posture": visibility_posture,
            "mutation_authority": mutation_authority,
        }
    }


def test_dialogue_cue_keeps_shadow_target_internal_for_medium_uncertainty() -> None:
    result = apply_shadow_hypothesis_dialogue_cue(
        assistant_message=SAFE_NO_COMMIT_REPLY,
        phase_a_trace=_trace(),
    )

    assert result.assistant_message == SAFE_NO_COMMIT_REPLY
    assert "meal thread" not in result.assistant_message
    assert "not a saved change" not in result.assistant_message
    assert result.phase_a_trace["shadow_hypothesis_dialogue"]["applied"] is False
    assert (
        result.phase_a_trace["shadow_hypothesis_dialogue"]["skip_reason"]
        == "user_visible_cue_disabled"
    )
    assert result.phase_a_trace["shadow_hypothesis_dialogue"]["candidate_target_object_id"] == "77"


def test_dialogue_cue_skips_internal_only_or_non_medium_shadow() -> None:
    high = apply_shadow_hypothesis_dialogue_cue(
        assistant_message="Base reply.",
        phase_a_trace=_trace(confidence="high", visibility_posture="internal_only"),
    )
    low = apply_shadow_hypothesis_dialogue_cue(
        assistant_message="Base reply.",
        phase_a_trace=_trace(confidence="low"),
    )

    assert high.assistant_message == "Base reply."
    assert high.phase_a_trace["shadow_hypothesis_dialogue"]["applied"] is False
    assert high.phase_a_trace["shadow_hypothesis_dialogue"]["skip_reason"] == "not_uncertainty_visible"
    assert low.assistant_message == "Base reply."
    assert low.phase_a_trace["shadow_hypothesis_dialogue"]["skip_reason"] == "confidence_not_medium"


def test_dialogue_cue_never_applies_when_shadow_has_mutation_authority() -> None:
    result = apply_shadow_hypothesis_dialogue_cue(
        assistant_message="Base reply.",
        phase_a_trace=_trace(mutation_authority=True),
    )

    assert result.assistant_message == "Base reply."
    assert result.phase_a_trace["shadow_hypothesis_dialogue"]["applied"] is False
    assert result.phase_a_trace["shadow_hypothesis_dialogue"]["skip_reason"] == "shadow_authoritative"


def test_dialogue_cue_never_applies_after_committed_mutation() -> None:
    result = apply_shadow_hypothesis_dialogue_cue(
        assistant_message="已更新上一筆餐點：珍珠奶茶 450 kcal。",
        phase_a_trace=_trace(),
        mutation_committed=True,
    )

    assert result.assistant_message == "已更新上一筆餐點：珍珠奶茶 450 kcal。"
    assert result.phase_a_trace["shadow_hypothesis_dialogue"]["applied"] is False
    assert result.phase_a_trace["shadow_hypothesis_dialogue"]["skip_reason"] == "mutation_already_committed"


@pytest.mark.asyncio
async def test_intake_execution_response_applies_shadow_dialogue_cue_without_state_changes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.composition import intake_execution_response as module

    assert not hasattr(module, "build_remaining_budget_answer_contract")

    class _View:
        user_id = 1
        onboarding_ready = True
        injected_context: dict[str, object] = {}

        def __init__(self) -> None:
            self.active_body_plan_view = self
            self.current_budget_view = self

        def model_dump(self, *, mode: str = "json") -> dict[str, object]:
            return {
                "body_plan_id": 1,
                "budget_kcal": 1800,
                "remaining_kcal": 900,
                "show_macro": False,
            }

    state_delta = {
        "meal_logged": False,
        "canonical_commit": False,
        "ledger_updated": False,
        "draft_saved": False,
        "new_meal_version_created": False,
        "old_version_superseded": False,
    }
    monkeypatch.setattr(module, "render_intake_reply", lambda **_: "Base reply.")
    monkeypatch.setattr(module, "write_intake_execution_trace_artifact", lambda **_: None)
    monkeypatch.setattr(module, "build_trace_refs", lambda **_: {"request_id": "req-shadow-dialogue"})

    result = module.build_intake_execution_response(
        None,
        request_id="req-shadow-dialogue",
        user_external_id="user-1",
        raw_user_input="that milk tea half sugar",
        local_date="2026-04-29",
        allow_search=False,
        state_before=_View(),
        state_after=_View(),
        manager_decision=SimpleNamespace(
            intent_type="log_meal",
            workflow_effect="none",
            response_summary="",
            pending_followup=None,
            tool_calls=[],
            llm_used=False,
            trace={},
        ),
        manager_result=SimpleNamespace(
            final_action="no_commit",
            workflow_effect="safe_failure",
            manager_rounds=[],
            tool_calls=[],
            tool_results=[],
        ),
        nutrition_artifact=None,
        persistence_result=None,
        budget_summary=None,
        tool_outputs={},
        state_mutation_summary=dict(state_delta),
        stage_timings=[],
        phase_a_trace=_trace(),
    )

    assert result["assistant_message"] == "Base reply."
    assert "meal thread" not in result["assistant_message"]
    assert result["state_delta"] == state_delta
    assert result["sidecar"]["state_mutation_summary"]["canonical_commit"] is False
