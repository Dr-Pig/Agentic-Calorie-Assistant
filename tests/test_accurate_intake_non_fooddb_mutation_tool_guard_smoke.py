from __future__ import annotations

import json
from pathlib import Path

from app.composition.accurate_intake_non_fooddb_mutation_tool_guard_smoke import (
    build_non_fooddb_mutation_tool_guard_smoke_artifact,
)


REQUIRED_CASES = [
    "body_record_weight_observation_only",
    "body_record_weight_invalid_payload_blocked",
    "calibration_preview_no_persist_default",
    "calibration_preview_persist_open_proposal_only",
    "calibration_apply_missing_stored_proposal_blocked",
    "calibration_apply_accept_stored_proposal_guarded",
    "calibration_apply_reject_stored_proposal_no_plan_ledger",
    "manual_daily_target_manager_structured_only",
    "manual_daily_target_out_of_bounds_blocked",
]


def _by_id(artifact: dict[str, object]) -> dict[str, dict[str, object]]:
    return {str(case["case_id"]): case for case in artifact["cases"]}  # type: ignore[index]


def test_non_fooddb_mutation_tool_guard_smoke_covers_guarded_mutation_and_proposal_cases() -> None:
    artifact = build_non_fooddb_mutation_tool_guard_smoke_artifact()

    assert artifact["artifact_schema_version"] == "1.0"
    assert artifact["artifact_type"] == "accurate_intake_non_fooddb_mutation_tool_guard_smoke"
    assert artifact["status"] == "non_fooddb_mutation_tool_guard_smoke_pass"
    assert artifact["fixture_manager_used"] is True
    assert artifact["semantic_owner"] == "fixture_manager_structured_decision"
    assert artifact["deterministic_selected_tool"] is False
    assert artifact["deterministic_selected_intent"] is False
    assert artifact["frontend_raw_text_semantic_router"] is False
    assert artifact["runtime_truth_changed"] is False
    assert artifact["mutation_changed"] is False
    assert artifact["manager_context_packet_schema_changed"] is False
    assert artifact["fooddb_used"] is False
    assert artifact["web_tavily_used"] is False
    assert artifact["live_llm_invoked"] is False
    assert artifact["product_readiness_claimed"] is False
    assert artifact["private_self_use_approved"] is False
    assert [case["case_id"] for case in artifact["cases"]] == REQUIRED_CASES

    for case in artifact["cases"]:  # type: ignore[index]
        assert case["raw_text_authorizes_mutation"] is False
        assert case["frontend_semantic_owner"] is False
        assert case["deterministic_role"] == "validate_guard_and_execute_existing_domain_contract"


def test_non_fooddb_mutation_tool_guard_smoke_maps_expected_guard_postures() -> None:
    cases = _by_id(build_non_fooddb_mutation_tool_guard_smoke_artifact())

    body_record = cases["body_record_weight_observation_only"]
    assert body_record["selected_tool"] == "body.record_observation"
    assert body_record["guard_posture"] == "observation_only_guarded_write"
    assert body_record["expected_effects"]["body_observation_written"] is True
    assert body_record["expected_effects"]["body_plan_mutated"] is False
    assert body_record["expected_effects"]["ledger_mutated"] is False

    preview_default = cases["calibration_preview_no_persist_default"]
    assert preview_default["selected_tool"] == "calibration.preview_proposal"
    assert preview_default["expected_effects"]["proposal_persisted"] is False
    assert preview_default["expected_effects"]["body_plan_mutated"] is False
    assert preview_default["expected_effects"]["ledger_mutated"] is False

    accept_action = cases["calibration_apply_accept_stored_proposal_guarded"]
    assert accept_action["selected_tool"] == "calibration.apply_stored_proposal_action"
    assert accept_action["stored_proposal_required"] is True
    assert accept_action["expected_effects"]["proposal_status_changed"] is True
    assert accept_action["expected_effects"]["body_plan_mutated"] is True
    assert accept_action["expected_effects"]["current_budget_refreshed"] is True

    manual_target = cases["manual_daily_target_manager_structured_only"]
    assert manual_target["selected_tool"] == "budget.set_manual_daily_target"
    assert manual_target["inventory_alignment"] == "adjacent_pending_inventory_expansion"
    assert manual_target["manager_structured_target_required"] is True
    assert manual_target["expected_effects"]["body_plan_mutated"] is True
    assert manual_target["expected_effects"]["ledger_mutated"] is True

def test_non_fooddb_mutation_tool_guard_smoke_blocks_contract_drift_and_overclaims() -> None:
    artifact = build_non_fooddb_mutation_tool_guard_smoke_artifact()
    cases = list(artifact["cases"])  # type: ignore[index]

    drifted_body = dict(cases[0])
    drifted_body["raw_text_authorizes_mutation"] = True
    drifted_body["expected_effects"] = {
        **dict(drifted_body["expected_effects"]),  # type: ignore[arg-type]
        "body_plan_mutated": True,
    }
    cases[0] = drifted_body

    drifted_manual_target = dict(cases[7])
    drifted_manual_target["manager_structured_target_required"] = False
    cases[7] = drifted_manual_target

    drifted_manual_target_blocked = dict(cases[8])
    drifted_manual_target_blocked["mutation_allowed"] = True
    cases[8] = drifted_manual_target_blocked

    blocked = build_non_fooddb_mutation_tool_guard_smoke_artifact(
        cases=cases,
        overrides={
            "live_llm_invoked": True,
            "fooddb_used": True,
            "runtime_truth_changed": True,
            "manager_context_packet_schema_changed": True,
        },
    )

    assert blocked["status"] == "blocked"
    assert "body_record_weight_observation_only.raw_text_authorizes_mutation" in blocked["blockers"]
    assert "body_record_weight_observation_only.body_observation_must_not_mutate_body_plan" in blocked["blockers"]
    assert "manual_daily_target_manager_structured_only.manager_structured_target_required_missing" in blocked["blockers"]
    assert "manual_daily_target_out_of_bounds_blocked.manual_daily_target_blocked_case_must_not_allow_mutation" in blocked["blockers"]
    assert "live_llm_invoked" in blocked["blockers"]
    assert "fooddb_used" in blocked["blockers"]
    assert "runtime_truth_changed" in blocked["blockers"]
    assert "manager_context_packet_schema_changed" in blocked["blockers"]


def test_non_fooddb_mutation_tool_guard_smoke_blocks_post_validation_override_bypass() -> None:
    artifact = build_non_fooddb_mutation_tool_guard_smoke_artifact(
        overrides={"cases": [], "summary": {"case_count": 0}}
    )

    assert artifact["status"] == "blocked"
    assert "missing_case:body_record_weight_observation_only" in artifact["blockers"]


def test_non_fooddb_mutation_tool_guard_smoke_cli_writes_artifact(tmp_path: Path) -> None:
    from scripts.build_accurate_intake_non_fooddb_mutation_tool_guard_smoke import main

    output_path = tmp_path / "non-fooddb-mutation-tool-guard-smoke.json"
    exit_code = main(["--output", str(output_path)])
    artifact = json.loads(output_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert artifact["status"] == "non_fooddb_mutation_tool_guard_smoke_pass"
    assert artifact["summary"]["case_count"] == len(REQUIRED_CASES)


def test_non_fooddb_mutation_tool_guard_smoke_stays_out_of_forbidden_boundaries() -> None:
    for path in (
        Path("app/composition/accurate_intake_non_fooddb_mutation_tool_guard_smoke.py"),
        Path("scripts/build_accurate_intake_non_fooddb_mutation_tool_guard_smoke.py"),
    ):
        source = path.read_text(encoding="utf-8")
        for fragment in (
            "NutritionEvidenceStorePort",
            "FoodEvidenceRecord",
            "PacketReadyAnchor",
            "TavilyClient",
            "builderspace_adapter",
            "manager_context_packet_v1 =",
            "deterministic_selected_tool = True",
            "deterministic_selected_intent = True",
            "record_budget_adjustment_to_canonical(",
        ):
            assert fragment not in source
