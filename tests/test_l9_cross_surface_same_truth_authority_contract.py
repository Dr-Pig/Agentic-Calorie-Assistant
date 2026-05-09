from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from app.composition.accurate_intake_today_macro_mirror_gate import (
    build_today_macro_mirror_gate_artifact,
)
from app.composition.accurate_intake_ui_same_truth_render_contract import (
    build_ui_same_truth_render_contract,
)
from app.shared.contracts.l9_cross_surface_same_truth_authority_contract import (
    build_l9_cross_surface_same_truth_authority_contract,
)
from app.intake.application.phase_c_same_truth_gate import build_phase_c_same_truth_gate
from app.runtime.application.proactive_no_send_shadow_evaluator import (
    SIDECAR_ACTIVATION_CONTRACT as PROACTIVE_NO_SEND_CONTRACT,
)


def _state_after() -> SimpleNamespace:
    return SimpleNamespace(
        current_budget_view=SimpleNamespace(
            model_dump=lambda *, mode="json": {
                "consumed_kcal": 900,
                "remaining_kcal": 900,
            }
        )
    )


def _phase_c_pass_gate() -> dict[str, object]:
    return build_phase_c_same_truth_gate(
        phase_c_trace={
            "mutation_outcome": {
                "canonical_commit_status": "committed",
                "ledger_mutation_status": "updated",
                "macro_visibility_status": "visible",
            },
            "same_truth_read_result": {
                "owner_alignment": "aligned",
                "consistency_flags": [],
                "compared_surfaces": ["persistence_result"],
            },
        },
        persistence_result=SimpleNamespace(canonical_commit={"meal_thread_id": 77}),
        state_delta={"canonical_commit": True, "ledger_updated": True},
        sidecar={"state_mutation_summary": {"canonical_commit": True, "ledger_updated": True}},
        state_after=_state_after(),
        budget_summary={
            "predicted_consumed_kcal_after": 900,
            "predicted_remaining_kcal_after": 900,
        },
    )


def test_l9_contract_accepts_existing_mirror_gate_and_sidecar_surfaces() -> None:
    artifact = build_l9_cross_surface_same_truth_authority_contract(
        [
            {
                "surface_id": "local_shell_render_contract",
                "surface_role": "render_mirror",
                "canonical_truth_owner": "runtime_and_domain_read_models",
                "artifact": build_ui_same_truth_render_contract(
                    Path("static/accurate-intake-local-shell.html").read_text(encoding="utf-8")
                ),
            },
            {
                "surface_id": "today_macro_mirror_gate",
                "surface_role": "render_mirror",
                "canonical_truth_owner": "CurrentBudgetView.macro_visibility",
                "artifact": build_today_macro_mirror_gate_artifact(),
            },
            {
                "surface_id": "phase_c_same_truth_gate",
                "surface_role": "diagnostic_gate",
                "canonical_truth_owner": "phase_c_trace_and_budget_read_model",
                "diagnostic_only": True,
                "runtime_truth_changed": False,
                "mutation_changed": False,
                "artifact": _phase_c_pass_gate(),
            },
            {
                "surface_id": "calibration_proposal_inbox",
                "surface_role": "read_model_mirror",
                "canonical_truth_owner": "ProposalContainer_and_ProposalOption",
                "read_only": True,
                "runtime_truth_changed": False,
                "mutation_changed": False,
                "artifact": {"diagnostic_metadata_exposed": False},
            },
            {
                "surface_id": "proactive_no_send_shadow",
                "surface_role": "offline_sidecar_shadow",
                "canonical_truth_owner": "proactive_scheduler_future_contract",
                "artifact": PROACTIVE_NO_SEND_CONTRACT.model_dump(),
            },
        ]
    )

    assert artifact["artifact_type"] == "l9_cross_surface_same_truth_authority_contract"
    assert artifact["status"] == "pass"
    assert artifact["blockers"] == []
    assert artifact["local_only"] is True
    assert artifact["diagnostic_only"] is True
    assert artifact["frontend_semantic_owner"] is False
    assert artifact["runtime_connected"] is False
    assert artifact["runtime_truth_changed"] is False
    assert artifact["mutation_changed"] is False
    assert artifact["summary"]["surface_count"] == 5
    assert artifact["summary"]["role_counts"] == {
        "diagnostic_gate": 1,
        "offline_sidecar_shadow": 1,
        "read_model_mirror": 1,
        "render_mirror": 2,
    }


def test_l9_contract_blocks_ui_truth_claims_and_sidecar_activation() -> None:
    artifact = build_l9_cross_surface_same_truth_authority_contract(
        [
            {
                "surface_id": "bad_ui",
                "surface_role": "render_mirror",
                "canonical_truth_owner": "ui",
                "artifact": {
                    "frontend_semantic_owner": True,
                    "runtime_truth_changed": True,
                    "mutation_changed": True,
                },
            },
            {
                "surface_id": "bad_shadow",
                "surface_role": "offline_sidecar_shadow",
                "canonical_truth_owner": "memory",
                "artifact": {
                    "offline_only": False,
                    "activation_blocked": False,
                    "not_runtime_authority": False,
                    "user_facing_activation": True,
                    "mutation_authority": True,
                },
            },
        ]
    )

    assert artifact["status"] == "blocked"
    assert "bad_ui.canonical_truth_owner_invalid" in artifact["blockers"]
    assert "bad_ui.frontend_semantic_owner" in artifact["blockers"]
    assert "bad_ui.runtime_truth_changed" in artifact["blockers"]
    assert "bad_ui.mutation_changed" in artifact["blockers"]
    assert "bad_shadow.offline_only" in artifact["blockers"]
    assert "bad_shadow.activation_blocked" in artifact["blockers"]
    assert "bad_shadow.not_runtime_authority" in artifact["blockers"]
    assert "bad_shadow.user_facing_activation" in artifact["blockers"]
    assert "bad_shadow.mutation_authority" in artifact["blockers"]
