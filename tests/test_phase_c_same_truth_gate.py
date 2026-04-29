from __future__ import annotations

from types import SimpleNamespace

from app.intake.application.phase_c_same_truth_gate import build_phase_c_same_truth_gate


def _state_after(*, consumed_kcal: int = 900, remaining_kcal: int = 900) -> SimpleNamespace:
    return SimpleNamespace(
        current_budget_view=SimpleNamespace(
            model_dump=lambda *, mode="json": {
                "consumed_kcal": consumed_kcal,
                "remaining_kcal": remaining_kcal,
            }
        )
    )


def test_phase_c_same_truth_gate_passes_aligned_structured_surfaces() -> None:
    phase_c_trace = {
        "mutation_outcome": {
            "canonical_commit_status": "committed",
            "ledger_mutation_status": "updated",
            "macro_visibility_status": "visible",
        },
        "same_truth_read_result": {
            "owner_alignment": "aligned",
            "consistency_flags": [],
            "compared_surfaces": ["persistence_result", "state_delta", "sidecar.state_mutation_summary"],
        },
    }

    gate = build_phase_c_same_truth_gate(
        phase_c_trace=phase_c_trace,
        persistence_result=SimpleNamespace(canonical_commit={"meal_thread_id": 77}),
        state_delta={"canonical_commit": True, "ledger_updated": True},
        sidecar={"state_mutation_summary": {"canonical_commit": True, "ledger_updated": True}},
        state_after=_state_after(),
        budget_summary={"predicted_consumed_kcal_after": 900, "predicted_remaining_kcal_after": 900},
    )

    assert gate["checked"] is True
    assert gate["status"] == "pass"
    assert gate["failure_family"] is None
    assert gate["consistency_flags"] == []
    assert "state_after.current_budget_view" in gate["compared_surfaces"]


def test_phase_c_same_truth_gate_hard_fails_existing_projection_contradiction() -> None:
    gate = build_phase_c_same_truth_gate(
        phase_c_trace={
            "mutation_outcome": {"canonical_commit_status": "contradictory"},
            "same_truth_read_result": {
                "owner_alignment": "contradictory",
                "consistency_flags": ["state_delta_persistence_commit_mismatch"],
                "compared_surfaces": ["persistence_result", "state_delta"],
            },
        },
        persistence_result=None,
        state_delta={"canonical_commit": True},
        sidecar={"state_mutation_summary": {"canonical_commit": True}},
        state_after=_state_after(),
        budget_summary=None,
    )

    assert gate["status"] == "hard_fail"
    assert gate["failure_family"] == "phase_c_same_truth_contradiction"
    assert "state_delta_persistence_commit_mismatch" in gate["consistency_flags"]


def test_phase_c_same_truth_gate_hard_fails_post_write_budget_mismatch_without_repairing() -> None:
    phase_c_trace = {
        "mutation_outcome": {
            "canonical_commit_status": "committed",
            "ledger_mutation_status": "updated",
            "macro_visibility_status": "visible",
        },
        "same_truth_read_result": {
            "owner_alignment": "aligned",
            "consistency_flags": [],
            "compared_surfaces": ["persistence_result", "state_delta", "sidecar.state_mutation_summary"],
        },
    }

    gate = build_phase_c_same_truth_gate(
        phase_c_trace=phase_c_trace,
        persistence_result=SimpleNamespace(canonical_commit={"meal_thread_id": 77}),
        state_delta={"canonical_commit": True, "ledger_updated": True},
        sidecar={"state_mutation_summary": {"canonical_commit": True, "ledger_updated": True}},
        state_after=_state_after(consumed_kcal=800, remaining_kcal=1000),
        budget_summary={"predicted_consumed_kcal_after": 900, "predicted_remaining_kcal_after": 900},
    )

    assert gate["status"] == "hard_fail"
    assert gate["failure_family"] == "phase_c_same_truth_contradiction"
    assert "budget_summary_state_after_mismatch" in gate["consistency_flags"]


def test_phase_c_same_truth_gate_flags_missing_projection_without_inventing_truth() -> None:
    gate = build_phase_c_same_truth_gate(
        phase_c_trace={},
        persistence_result=None,
        state_delta={},
        sidecar={},
        state_after=SimpleNamespace(current_budget_view=None),
        budget_summary=None,
    )

    assert gate["status"] == "flagged"
    assert gate["failure_family"] is None
    assert gate["consistency_flags"] == ["phase_c_trace_not_available"]
