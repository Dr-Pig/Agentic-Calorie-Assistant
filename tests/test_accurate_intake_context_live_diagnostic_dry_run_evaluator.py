from __future__ import annotations

import json
from pathlib import Path

from app.composition.accurate_intake_context_live_diagnostic_case_matrix import (
    REQUIRED_CASE_IDS,
    build_context_live_diagnostic_case_matrix_artifact,
)
from app.composition.accurate_intake_context_live_diagnostic_dry_run_evaluator import (
    build_context_live_diagnostic_dry_run_evaluator_artifact,
)


def test_context_live_dry_run_evaluator_passes_fixed_fixture_matrix_without_live_calls() -> None:
    artifact = build_context_live_diagnostic_dry_run_evaluator_artifact(
        build_context_live_diagnostic_case_matrix_artifact()
    )

    assert artifact["artifact_type"] == "accurate_intake_context_live_diagnostic_dry_run_evaluator"
    assert artifact["status"] == "pass"
    assert artifact["diagnostic_only"] is True
    assert artifact["fixture_only"] is True
    assert artifact["plan_only"] is True
    assert artifact["fixed_case_matrix_used"] is True
    assert artifact["semantic_owner"] == "fixture_manager_structured_decision"
    assert artifact["deterministic_selected_intent"] is False
    assert artifact["deterministic_selected_target"] is False
    assert artifact["deterministic_semantic_inference_used"] is False
    assert artifact["raw_text_intent_router_used"] is False
    assert artifact["live_llm_invoked"] is False
    assert artifact["live_provider_invoked"] is False
    assert artifact["fooddb_used"] is False
    assert artifact["web_tavily_used"] is False
    assert artifact["mutation_changed"] is False
    assert artifact["manager_context_packet_schema_changed"] is False
    assert artifact["product_readiness_claimed"] is False
    assert artifact["private_self_use_approved"] is False
    assert artifact["blockers"] == []
    assert artifact["summary"]["case_count"] == len(REQUIRED_CASE_IDS)
    assert artifact["summary"]["evaluated_case_count"] == len(REQUIRED_CASE_IDS)
    assert artifact["summary"]["blocked_case_count"] == 0
    assert artifact["summary"]["target_candidate_cases"] >= 1
    assert artifact["summary"]["pending_pin_cases"] >= 1
    assert artifact["summary"]["ambiguity_cases"] >= 1


def test_context_live_dry_run_evaluator_rejects_wrong_fixture_intent_and_missing_context() -> None:
    matrix = build_context_live_diagnostic_case_matrix_artifact()
    case = matrix["cases"][3]
    outputs = [
        {
            "case_id": row["case_id"],
            "semantic_source": "fixture_manager_structured_decision",
            "manager_intent": row["expected_manager_intent"],
            "workflow_effect": row["expected_workflow_effect"],
            "context_fields_seen": row["expected_context_fields"],
            "target_candidates_seen": row["target_candidates_expected"],
            "pending_pin_seen": row["pending_pin_expected"],
            "ambiguity_preserved": row["ambiguity_expected"],
            "mutation_allowed": False,
            "forbidden_events": [],
            "live_llm_invoked": False,
            "live_provider_invoked": False,
            "fooddb_used": False,
            "web_tavily_used": False,
            "runtime_truth_changed": False,
            "mutation_changed": False,
            "manager_context_packet_schema_changed": False,
        }
        for row in matrix["cases"]
    ]
    outputs[3]["manager_intent"] = "general_chat"
    outputs[3]["context_fields_seen"] = ["context_policy_version"]
    outputs[3]["target_candidates_seen"] = False
    outputs[3]["forbidden_events"] = ["delete_without_manager_decision"]

    artifact = build_context_live_diagnostic_dry_run_evaluator_artifact(
        matrix,
        fixture_outputs=outputs,
    )

    assert artifact["status"] == "blocked"
    case_id = str(case["case_id"])
    assert f"{case_id}.manager_intent_mismatch" in artifact["blockers"]
    assert f"{case_id}.missing_context_field:target_candidates" in artifact["blockers"]
    assert f"{case_id}.target_candidates_missing" in artifact["blockers"]
    assert f"{case_id}.forbidden_event:delete_without_manager_decision" in artifact["blockers"]


def test_context_live_dry_run_evaluator_blocks_ad_hoc_case_matrix() -> None:
    matrix = build_context_live_diagnostic_case_matrix_artifact()
    matrix["cases"][0]["case_id"] = "ad_hoc_easy_case"

    artifact = build_context_live_diagnostic_dry_run_evaluator_artifact(matrix)

    assert artifact["status"] == "blocked"
    assert "matrix.fixed_case_order_mismatch" in artifact["blockers"]
    assert "ad_hoc_easy_case.manager_intent_mismatch" not in artifact["blockers"]


def test_context_live_dry_run_evaluator_cli_writes_artifact(tmp_path: Path) -> None:
    output_path = tmp_path / "dry-run.json"

    from scripts.build_accurate_intake_context_live_diagnostic_dry_run_evaluator import main

    assert main(["--output", str(output_path)]) == 0
    artifact = json.loads(output_path.read_text(encoding="utf-8"))

    assert artifact["status"] == "pass"
    assert artifact["summary"]["case_count"] == len(REQUIRED_CASE_IDS)


def test_context_live_dry_run_evaluator_source_stays_out_of_forbidden_boundaries() -> None:
    source_paths = [
        Path("app/composition/accurate_intake_context_live_diagnostic_dry_run_evaluator.py"),
        Path("scripts/build_accurate_intake_context_live_diagnostic_dry_run_evaluator.py"),
    ]
    forbidden = [
        "NutritionEvidenceStorePort",
        "FoodEvidenceRecord",
        "PacketReadyAnchor",
        "TavilyClient",
        "BuilderSpaceAdapter",
        "builderspace_adapter",
        "live_llm_invoked = True",
        "live_provider_invoked = True",
        "fooddb_used = True",
        "manager_context_packet_schema_changed = True",
    ]

    for path in source_paths:
        source = path.read_text(encoding="utf-8")
        for fragment in forbidden:
            assert fragment not in source
