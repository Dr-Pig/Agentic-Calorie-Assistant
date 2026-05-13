from __future__ import annotations

from app.nutrition.application.fooddb_grokfast_live_diagnostic_case_catalog import (
    REQUIRED_CASE_IDS,
)


def _diagnostic(*, case_ids: list[str], live_provider_used: bool = True) -> dict:
    return {
        "artifact_type": "accurate_intake_grokfast_fooddb_packet_smoke",
        "status": "pass",
        "live_provider_used": live_provider_used,
        "runtime_truth_changed": False,
        "runtime_mutation_attempted": False,
        "readiness_claimed": False,
        "self_use_approved": False,
        "production_selected": False,
        "selected_case_ids": list(case_ids),
        "summary": {
            "case_count": len(case_ids),
            "pass_count": len(case_ids),
            "fail_count": 0,
            "selected_case_count": len(case_ids),
            "failure_families": [],
        },
        "cases": [
            {
                "case_id": case_id,
                "status": "pass",
                "failure_families": [],
            }
            for case_id in case_ids
        ],
    }


def test_fooddb_live_stage_gate_accepts_single_case_probe() -> None:
    from app.nutrition.application.fooddb_live_diagnostic_stage_gate import (
        build_fooddb_live_diagnostic_stage_gate_artifact,
    )

    artifact = build_fooddb_live_diagnostic_stage_gate_artifact(
        live_stage="single-case",
        fooddb_live_diagnostic=_diagnostic(case_ids=[REQUIRED_CASE_IDS[0]]),
    )

    assert artifact["artifact_type"] == "accurate_intake_fooddb_live_diagnostic_stage_gate"
    assert artifact["status"] == "fooddb_live_single_case_probe_pass"
    assert artifact["live_stage"] == "single-case"
    assert artifact["summary"]["case_ids"] == [REQUIRED_CASE_IDS[0]]
    assert artifact["full_matrix_live_probe_allowed"] is False


def test_fooddb_live_stage_gate_requires_single_case_before_full_matrix() -> None:
    from app.nutrition.application.fooddb_live_diagnostic_stage_gate import (
        build_fooddb_live_diagnostic_stage_gate_artifact,
    )

    full_matrix = _diagnostic(case_ids=list(REQUIRED_CASE_IDS))
    blocked = build_fooddb_live_diagnostic_stage_gate_artifact(
        live_stage="full-matrix",
        fooddb_live_diagnostic=full_matrix,
    )

    assert blocked["status"] == "blocked"
    assert "single_case_stage_gate_required_before_full_matrix" in blocked["blockers"]

    single_case = build_fooddb_live_diagnostic_stage_gate_artifact(
        live_stage="single-case",
        fooddb_live_diagnostic=_diagnostic(case_ids=[REQUIRED_CASE_IDS[0]]),
    )
    allowed = build_fooddb_live_diagnostic_stage_gate_artifact(
        live_stage="full-matrix",
        fooddb_live_diagnostic=full_matrix,
        prior_single_case_stage_gate=single_case,
    )

    assert allowed["status"] == "fooddb_live_full_matrix_probe_pass"
    assert allowed["summary"]["case_ids"] == list(REQUIRED_CASE_IDS)
    assert allowed["full_matrix_live_probe_allowed"] is True
