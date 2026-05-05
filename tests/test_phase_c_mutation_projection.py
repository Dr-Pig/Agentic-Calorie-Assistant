from __future__ import annotations

from types import SimpleNamespace

from app.intake.application.phase_c_mutation_projection import build_phase_c_trace


def _persistence_result(*, canonical_commit: dict[str, object] | None) -> SimpleNamespace:
    return SimpleNamespace(
        action="save_completed_log" if canonical_commit is not None else "save_draft_log",
        status="ok",
        persisted_log_id=42,
        linked_meal_log_id=41,
        canonical_commit=canonical_commit,
    )


def test_phase_c_projection_reports_aligned_committed_mutation_outcome() -> None:
    state_delta = {
        "meal_logged": True,
        "canonical_commit": True,
        "draft_saved": False,
        "new_meal_version_created": True,
        "old_version_superseded": False,
        "ledger_updated": True,
    }
    sidecar = {
        "state_mutation_summary": dict(state_delta),
        "macro": {"display_status": "show"},
    }
    trace = build_phase_c_trace(
        persistence_result=_persistence_result(
            canonical_commit={
                "meal_thread_id": 77,
                "meal_version_id": 88,
                "meal_id": 501,
            }
        ),
        state_delta=state_delta,
        sidecar=sidecar,
        phase_a_trace={"boundary_projection": {"commit_boundary_decision": {"intent": "commit"}}},
        budget_summary={"predicted_remaining_kcal_after": 900},
    )

    outcome = trace["mutation_outcome"]
    assert outcome["canonical_commit_status"] == "committed"
    assert outcome["ledger_mutation_status"] == "updated"
    assert outcome["meal_version_delta"] == "new_version_created"
    assert outcome["macro_visibility_status"] == "visible"
    assert outcome["canonical_ids"]["meal_thread_id"] == 77
    assert trace["same_truth_read_result"]["owner_alignment"] == "aligned"
    assert trace["same_truth_read_result"]["consistency_flags"] == []


def test_phase_c_projection_reports_not_available_for_missing_surfaces() -> None:
    trace = build_phase_c_trace(
        persistence_result=None,
        state_delta={},
        sidecar={},
        phase_a_trace={},
        budget_summary=None,
    )

    outcome = trace["mutation_outcome"]
    assert outcome["canonical_commit_status"] == "not_available"
    assert outcome["ledger_mutation_status"] == "not_available"
    assert outcome["meal_version_delta"] == "not_available"
    assert outcome["macro_visibility_status"] == "not_available"
    assert trace["same_truth_read_result"]["owner_alignment"] == "not_applicable"


def test_phase_c_projection_reports_structured_surface_contradictions_without_fixing() -> None:
    state_delta = {
        "meal_logged": True,
        "canonical_commit": True,
        "draft_saved": False,
        "new_meal_version_created": True,
        "old_version_superseded": False,
        "ledger_updated": True,
    }
    sidecar = {
        "state_mutation_summary": {
            "meal_logged": False,
            "canonical_commit": False,
            "draft_saved": True,
            "new_meal_version_created": False,
            "old_version_superseded": False,
            "ledger_updated": False,
        },
        "macro": {"display_status": "show"},
    }

    trace = build_phase_c_trace(
        persistence_result=None,
        state_delta=state_delta,
        sidecar=sidecar,
        phase_a_trace={"boundary_projection": {"commit_boundary_decision": {"intent": "draft"}}},
        budget_summary=None,
    )

    assert trace["mutation_outcome"]["canonical_commit_status"] == "contradictory"
    assert trace["mutation_outcome"]["ledger_mutation_status"] == "contradictory"
    assert trace["same_truth_read_result"]["owner_alignment"] == "contradictory"
    assert "state_delta_persistence_commit_mismatch" in trace["same_truth_read_result"]["consistency_flags"]
    assert "state_delta_sidecar_mutation_mismatch" in trace["same_truth_read_result"]["consistency_flags"]
    assert "macro_visible_without_commit" in trace["same_truth_read_result"]["consistency_flags"]


def test_intake_execution_response_exposes_phase_c_trace_in_response_and_trace_artifact(
    monkeypatch,
) -> None:
    from app.composition import intake_execution_response as module

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
                "show_macro": True,
                "macro_guard_reason": "committed_and_aligned",
            }

    captured_trace_kwargs: dict[str, object] = {}

    monkeypatch.setattr(module, "render_intake_reply", lambda **_: "Logged. milk tea 420 kcal.")
    monkeypatch.setattr(module, "write_intake_execution_trace_artifact", lambda **kwargs: captured_trace_kwargs.update(kwargs))
    monkeypatch.setattr(module, "build_trace_refs", lambda **_: {"request_id": "req-phase-c"})

    result = module.build_intake_execution_response(
        None,
        request_id="req-phase-c",
        user_external_id="user-1",
        raw_user_input="milk tea",
        local_date="2026-04-29",
        allow_search=False,
        state_before=_View(),
        state_after=_View(),
        manager_decision=SimpleNamespace(
            intent_type="log_meal",
            workflow_effect="commit",
            response_summary="",
            pending_followup=None,
            tool_calls=[],
            llm_used=False,
            trace={},
        ),
        manager_result=SimpleNamespace(
            final_action="commit",
            workflow_effect="committed",
            manager_rounds=[],
            tool_calls=[],
            tool_results=[],
        ),
        nutrition_artifact=None,
        persistence_result=_persistence_result(
            canonical_commit={
                "meal_thread_id": 77,
                "meal_version_id": 88,
                "meal_id": 501,
            }
        ),
        budget_summary={"predicted_remaining_kcal_after": 900},
        tool_outputs={},
        state_mutation_summary={
            "meal_logged": True,
            "canonical_commit": True,
            "ledger_updated": True,
            "draft_saved": False,
            "new_meal_version_created": True,
            "old_version_superseded": False,
        },
        stage_timings=[],
        phase_a_trace={"boundary_projection": {"commit_boundary_decision": {"intent": "commit"}}},
    )

    assert result["phase_c_trace"]["mutation_outcome"]["canonical_commit_status"] == "committed"
    assert result["phase_c_trace"]["same_truth_read_result"]["owner_alignment"] == "aligned"
    assert result["phase_c_trace"]["same_truth_closure_gate"]["status"] == "pass"
    assert captured_trace_kwargs["phase_c_trace"] == result["phase_c_trace"]


def test_intake_execution_response_reports_same_truth_hard_fail_without_rewriting_output(
    monkeypatch,
) -> None:
    from app.composition import intake_execution_response as module

    class _View:
        user_id = 1
        onboarding_ready = True
        injected_context: dict[str, object] = {}

        def __init__(self, *, remaining_kcal: int) -> None:
            self.active_body_plan_view = self
            self.current_budget_view = self
            self.remaining_kcal = remaining_kcal

        def model_dump(self, *, mode: str = "json") -> dict[str, object]:
            return {
                "body_plan_id": 1,
                "budget_kcal": 1800,
                "consumed_kcal": 900,
                "remaining_kcal": self.remaining_kcal,
                "show_macro": True,
                "macro_guard_reason": "committed_and_aligned",
            }

    captured_trace_kwargs: dict[str, object] = {}

    monkeypatch.setattr(module, "render_intake_reply", lambda **_: "Logged. milk tea 420 kcal.")
    monkeypatch.setattr(module, "write_intake_execution_trace_artifact", lambda **kwargs: captured_trace_kwargs.update(kwargs))
    monkeypatch.setattr(module, "build_trace_refs", lambda **_: {"request_id": "req-phase-c-hard-fail"})

    result = module.build_intake_execution_response(
        None,
        request_id="req-phase-c-hard-fail",
        user_external_id="user-1",
        raw_user_input="milk tea",
        local_date="2026-04-29",
        allow_search=False,
        state_before=_View(remaining_kcal=1200),
        state_after=_View(remaining_kcal=1000),
        manager_decision=SimpleNamespace(
            intent_type="log_meal",
            workflow_effect="commit",
            response_summary="",
            pending_followup=None,
            tool_calls=[],
            llm_used=False,
            trace={},
        ),
        manager_result=SimpleNamespace(
            final_action="commit",
            workflow_effect="committed",
            manager_rounds=[],
            tool_calls=[],
            tool_results=[],
        ),
        nutrition_artifact=None,
        persistence_result=_persistence_result(
            canonical_commit={
                "meal_thread_id": 77,
                "meal_version_id": 88,
                "meal_id": 501,
            }
        ),
        budget_summary={"predicted_consumed_kcal_after": 900, "predicted_remaining_kcal_after": 900},
        tool_outputs={},
        state_mutation_summary={
            "meal_logged": True,
            "canonical_commit": True,
            "ledger_updated": True,
            "draft_saved": False,
            "new_meal_version_created": True,
            "old_version_superseded": False,
        },
        stage_timings=[],
        phase_a_trace={"boundary_projection": {"commit_boundary_decision": {"intent": "commit"}}},
    )

    assert result["assistant_message"] == "Logged. milk tea 420 kcal."
    assert result["state_delta"]["canonical_commit"] is True
    assert result["phase_c_trace"]["same_truth_closure_gate"]["status"] == "hard_fail"
    assert result["hard_fail_conditions"] == ["phase_c_same_truth_contradiction"]
    assert captured_trace_kwargs["phase_c_trace"] == result["phase_c_trace"]
