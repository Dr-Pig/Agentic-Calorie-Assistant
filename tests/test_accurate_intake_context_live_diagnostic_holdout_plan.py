from __future__ import annotations

import json
from pathlib import Path

from app.composition.accurate_intake_context_live_diagnostic_anti_overfit_guard import (
    build_context_live_diagnostic_anti_overfit_guard_artifact,
)
from app.composition.accurate_intake_context_live_diagnostic_case_matrix import (
    REQUIRED_CASE_IDS,
    build_context_live_diagnostic_case_matrix_artifact,
)
from app.composition.accurate_intake_context_live_diagnostic_holdout_plan import (
    build_context_live_diagnostic_holdout_plan_artifact,
)


def _valid_artifact() -> dict:
    matrix = build_context_live_diagnostic_case_matrix_artifact()
    anti_overfit = build_context_live_diagnostic_anti_overfit_guard_artifact(matrix)
    return build_context_live_diagnostic_holdout_plan_artifact(
        context_live_diagnostic_case_matrix=matrix,
        context_live_diagnostic_anti_overfit_guard=anti_overfit,
    )


def test_context_live_holdout_plan_requires_full_withheld_case_matrix_before_live_probe() -> None:
    artifact = _valid_artifact()

    assert artifact["artifact_type"] == "accurate_intake_context_live_diagnostic_holdout_plan"
    assert artifact["status"] == "pass"
    assert artifact["diagnostic_only"] is True
    assert artifact["fixture_only"] is True
    assert artifact["plan_only"] is True
    assert artifact["fixed_case_matrix_used"] is True
    assert artifact["holdout_variants_withheld_from_default_live_prompt"] is True
    assert artifact["ad_hoc_live_case_selection_allowed"] is False
    assert artifact["provider_optimized_case_selection_allowed"] is False
    assert artifact["blocked_if_single_case_only"] is True
    assert artifact["semantic_owner"] == "future_live_manager_provider_when_human_approved"
    assert artifact["deterministic_role"] == "validate_case_selection_not_select_intent"
    assert artifact["live_llm_invoked"] is False
    assert artifact["live_provider_invoked"] is False
    assert artifact["fooddb_used"] is False
    assert artifact["web_tavily_used"] is False
    assert artifact["runtime_truth_changed"] is False
    assert artifact["mutation_changed"] is False
    assert artifact["manager_context_packet_schema_changed"] is False
    assert "product_readiness_claimed" not in artifact
    assert "private_self_use_approved" not in artifact
    assert artifact["blockers"] == []
    assert artifact["summary"]["case_ids"] == list(REQUIRED_CASE_IDS)
    assert artifact["summary"]["withheld_holdout_variant_count"] >= len(REQUIRED_CASE_IDS) * 2
    assert artifact["summary"]["cases_with_holdouts"] == len(REQUIRED_CASE_IDS)


def test_context_live_holdout_plan_blocks_ad_hoc_single_case_selection() -> None:
    matrix = build_context_live_diagnostic_case_matrix_artifact()
    matrix["cases"] = matrix["cases"][:1]
    matrix["summary"] = {"case_count": 1, "compound_cases": 0, "ambiguity_cases": 0}
    anti_overfit = build_context_live_diagnostic_anti_overfit_guard_artifact(matrix)

    artifact = build_context_live_diagnostic_holdout_plan_artifact(
        context_live_diagnostic_case_matrix=matrix,
        context_live_diagnostic_anti_overfit_guard=anti_overfit,
    )

    assert artifact["status"] == "blocked"
    assert "matrix.fixed_case_order_mismatch" in artifact["blockers"]
    assert "anti_overfit_guard.status_not_pass" in artifact["blockers"]
    assert "anti_overfit_guard.holdout_variant_count_too_low" in artifact["blockers"]


def test_context_live_holdout_plan_blocks_missing_or_repeated_holdouts() -> None:
    matrix = build_context_live_diagnostic_case_matrix_artifact()
    matrix["cases"][0]["holdout_utterance_variants"] = []
    matrix["cases"][1]["holdout_utterance_variants"] = [
        matrix["cases"][1]["utterance"],
        "different holdout",
    ]
    anti_overfit = build_context_live_diagnostic_anti_overfit_guard_artifact(matrix)

    artifact = build_context_live_diagnostic_holdout_plan_artifact(
        context_live_diagnostic_case_matrix=matrix,
        context_live_diagnostic_anti_overfit_guard=anti_overfit,
    )

    assert artifact["status"] == "blocked"
    assert "context_live_001_general_chat_no_mutation.holdout_variants_too_low" in artifact["blockers"]
    assert "context_live_002_simple_food_log_candidate.holdout_repeats_primary_utterance" in artifact["blockers"]


def test_context_live_holdout_plan_blocks_live_fooddb_or_readiness_overclaims() -> None:
    matrix = build_context_live_diagnostic_case_matrix_artifact()
    anti_overfit = build_context_live_diagnostic_anti_overfit_guard_artifact(matrix)
    matrix["live_provider_invoked"] = True
    matrix["fooddb_used"] = True
    anti_overfit["product_readiness_claimed"] = True

    artifact = build_context_live_diagnostic_holdout_plan_artifact(
        context_live_diagnostic_case_matrix=matrix,
        context_live_diagnostic_anti_overfit_guard=anti_overfit,
    )

    assert artifact["status"] == "blocked"
    assert "matrix.live_provider_invoked" in artifact["blockers"]
    assert "matrix.fooddb_used" in artifact["blockers"]
    assert "anti_overfit_guard.product_readiness_claimed" in artifact["blockers"]


def test_context_live_holdout_plan_cli_writes_artifact(tmp_path: Path) -> None:
    matrix = build_context_live_diagnostic_case_matrix_artifact()
    anti_overfit = build_context_live_diagnostic_anti_overfit_guard_artifact(matrix)
    matrix_path = tmp_path / "matrix.json"
    anti_path = tmp_path / "anti.json"
    output_path = tmp_path / "holdout.json"
    matrix_path.write_text(json.dumps(matrix, ensure_ascii=False), encoding="utf-8")
    anti_path.write_text(json.dumps(anti_overfit, ensure_ascii=False), encoding="utf-8")

    from scripts.build_accurate_intake_context_live_diagnostic_holdout_plan import main

    exit_code = main(
        [
            "--matrix-json",
            str(matrix_path),
            "--anti-overfit-json",
            str(anti_path),
            "--output",
            str(output_path),
        ]
    )

    artifact = json.loads(output_path.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert artifact["status"] == "pass"


def test_context_live_holdout_plan_is_not_on_required_merge_path() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "product-pages-browser-e2e" in workflow
    assert "build_accurate_intake_context_live_diagnostic_holdout_plan.py" not in workflow
    assert "accurate_intake_context_live_diagnostic_holdout_plan_ci.json" not in workflow


def test_context_live_holdout_plan_source_stays_out_of_forbidden_boundaries() -> None:
    source_paths = [
        Path("app/composition/accurate_intake_context_live_diagnostic_holdout_plan.py"),
        Path("scripts/build_accurate_intake_context_live_diagnostic_holdout_plan.py"),
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
