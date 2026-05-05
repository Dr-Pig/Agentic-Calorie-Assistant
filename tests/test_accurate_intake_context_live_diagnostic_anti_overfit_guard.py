from __future__ import annotations

import json
from pathlib import Path

from app.composition.accurate_intake_context_live_diagnostic_case_matrix import (
    build_context_live_diagnostic_case_matrix_artifact,
)
from app.composition.accurate_intake_context_live_diagnostic_anti_overfit_guard import (
    build_context_live_diagnostic_anti_overfit_guard_artifact,
)


def test_context_live_anti_overfit_guard_accepts_fixed_plan_only_matrix() -> None:
    guard = build_context_live_diagnostic_anti_overfit_guard_artifact(
        build_context_live_diagnostic_case_matrix_artifact()
    )

    assert guard["artifact_type"] == "accurate_intake_context_live_diagnostic_anti_overfit_guard"
    assert guard["status"] == "pass"
    assert guard["diagnostic_only"] is True
    assert guard["plan_only"] is True
    assert guard["live_llm_invoked"] is False
    assert guard["live_provider_invoked"] is False
    assert guard["fooddb_used"] is False
    assert guard["mutation_changed"] is False
    assert guard["manager_context_packet_schema_changed"] is False
    assert guard["product_readiness_claimed"] is False
    assert guard["private_self_use_approved"] is False
    assert guard["blockers"] == []
    assert guard["summary"]["fixed_case_matrix_used"] is True
    assert guard["summary"]["case_count"] >= 11
    assert guard["summary"]["compound_cases"] >= 1
    assert guard["summary"]["ambiguity_cases"] >= 1
    assert guard["summary"]["pending_pin_cases"] >= 1
    assert guard["summary"]["target_candidate_cases"] >= 1
    assert guard["summary"]["distinct_intent_count"] >= 8
    assert guard["summary"]["distinct_workflow_effect_count"] >= 8


def test_context_live_anti_overfit_guard_blocks_ad_hoc_or_easy_case_selection() -> None:
    matrix = build_context_live_diagnostic_case_matrix_artifact()
    matrix["cases"] = matrix["cases"][:1]
    matrix["summary"] = {"case_count": 1, "compound_cases": 0, "ambiguity_cases": 0}

    guard = build_context_live_diagnostic_anti_overfit_guard_artifact(matrix)

    assert guard["status"] == "blocked"
    assert "fixed_case_matrix_mismatch" in guard["blockers"]
    assert "case_count_too_low" in guard["blockers"]
    assert "compound_case_missing" in guard["blockers"]
    assert "ambiguity_case_missing" in guard["blockers"]
    assert "intent_diversity_too_low" in guard["blockers"]
    assert "workflow_effect_diversity_too_low" in guard["blockers"]


def test_context_live_anti_overfit_guard_blocks_homogeneous_case_selection() -> None:
    matrix = build_context_live_diagnostic_case_matrix_artifact()
    for case in matrix["cases"]:
        case["expected_manager_intent"] = "general_chat"
        case["expected_workflow_effect"] = "no_mutation"

    guard = build_context_live_diagnostic_anti_overfit_guard_artifact(matrix)

    assert guard["status"] == "blocked"
    assert "intent_diversity_too_low" in guard["blockers"]
    assert "workflow_effect_diversity_too_low" in guard["blockers"]


def test_context_live_anti_overfit_guard_blocks_live_or_fooddb_overclaims() -> None:
    matrix = build_context_live_diagnostic_case_matrix_artifact()
    matrix.update(
        {
            "plan_only": False,
            "live_llm_invoked": True,
            "live_provider_invoked": True,
            "live_provider_approved": True,
            "fooddb_used": True,
            "mutation_changed": True,
            "manager_context_packet_schema_changed": True,
            "product_readiness_claimed": True,
        }
    )

    guard = build_context_live_diagnostic_anti_overfit_guard_artifact(matrix)

    assert guard["status"] == "blocked"
    assert "matrix_not_plan_only" in guard["blockers"]
    assert "matrix_live_llm_invoked" in guard["blockers"]
    assert "matrix_live_provider_invoked" in guard["blockers"]
    assert "matrix_live_provider_approved" in guard["blockers"]
    assert "matrix_fooddb_used" in guard["blockers"]
    assert "matrix_mutation_changed" in guard["blockers"]
    assert "matrix_manager_context_packet_schema_changed" in guard["blockers"]
    assert "matrix_product_readiness_claimed" in guard["blockers"]


def test_context_live_anti_overfit_guard_cli_writes_artifact(tmp_path: Path) -> None:
    matrix_path = tmp_path / "matrix.json"
    output_path = tmp_path / "guard.json"
    matrix_path.write_text(
        json.dumps(build_context_live_diagnostic_case_matrix_artifact(), ensure_ascii=False),
        encoding="utf-8",
    )

    from scripts.build_accurate_intake_context_live_diagnostic_anti_overfit_guard import main

    exit_code = main(["--matrix-json", str(matrix_path), "--output", str(output_path)])

    assert exit_code == 0
    guard = json.loads(output_path.read_text(encoding="utf-8"))
    assert guard["status"] == "pass"


def test_context_live_anti_overfit_guard_stays_out_of_forbidden_boundaries() -> None:
    source_paths = [
        Path("app/composition/accurate_intake_context_live_diagnostic_anti_overfit_guard.py"),
        Path("scripts/build_accurate_intake_context_live_diagnostic_anti_overfit_guard.py"),
    ]
    forbidden = [
        "NutritionEvidenceStorePort",
        "FoodEvidenceRecord",
        "PacketReadyAnchor",
        "Tavily",
        "Kimi",
        "GrokFast",
        "live_provider_invoked = True",
        "fooddb_used = True",
        "ready_for_live_diagnostic_decision = True",
        "manager_context_packet_schema_changed = True",
    ]
    for path in source_paths:
        source = path.read_text(encoding="utf-8")
        for fragment in forbidden:
            assert fragment not in source
