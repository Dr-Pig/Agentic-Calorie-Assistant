from __future__ import annotations

import json
from pathlib import Path

from app.composition import accurate_intake_pl_ce_local_mvp_candidate_bundle as module
from app.composition.accurate_intake_pl_ce_local_mvp_candidate_bundle import (
    build_pl_ce_local_mvp_candidate_bundle_artifact,
)


REQUIRED_INPUTS = [
    "ui_same_truth_contract",
    "context_quality_pack",
    "short_term_context_runtime_replay",
    "context_coverage_matrix",
    "context_live_diagnostic_case_matrix",
    "context_conditioned_intent_wall",
    "correction_removal_fixture_flow",
    "responder_input_contract_fake_smoke",
    "fixture_packet_emulator",
    "fake_provider_tool_loop_smoke",
    "review_eval_candidate_pipeline",
    "local_operator_data_hygiene_bundle",
    "mvp_gate_summary",
]


def _valid_inputs() -> dict[str, dict[str, object]]:
    return {
        "ui_same_truth_contract": {
            "artifact_type": "accurate_intake_ui_same_truth_render_contract",
            "status": "pass",
            "frontend_semantic_owner": False,
        },
        "context_quality_pack": {
            "artifact_type": "accurate_intake_context_quality_pack",
            "status": "context_quality_diagnostic_pass",
            "context_engineering_fault_claimed": False,
            "manager_context_packet_schema_changed": False,
            "deterministic_semantic_inference_used": False,
            "raw_text_intent_router_used": False,
            "mutation_authority": False,
            "ready_for_live_diagnostic_decision": False,
        },
        "short_term_context_runtime_replay": {
            "artifact_type": "accurate_intake_short_term_context_runtime_replay",
            "status": "runtime_replay_diagnostic_pass",
            "runtime_trace_backed": True,
            "scenario_count": 7,
            "context_engineering_fault_claimed": False,
            "manager_context_packet_schema_changed": False,
            "deterministic_semantic_inference_used": False,
            "raw_text_intent_router_used": False,
            "mutation_authority": False,
            "summary": {
                "scenario_count": 7,
                "pending_pin_scenarios": 2,
                "target_candidate_scenarios": 4,
                "current_gap_scenarios": 0,
            },
        },
        "context_coverage_matrix": {
            "artifact_type": "accurate_intake_pl_ce_context_coverage_matrix",
            "status": "context_coverage_matrix_ready_for_human_review",
            "blockers": [],
            "context_engineering_fault_claimed": False,
            "manager_context_packet_schema_changed": False,
            "deterministic_selected_target": False,
            "deterministic_semantic_inference_used": False,
            "raw_text_intent_router_used": False,
            "mutation_authority": False,
            "live_websearch_used": False,
            "runtime_truth_changed": False,
            "mutation_changed": False,
            "ready_for_live_diagnostic_decision": False,
            "ready_for_fdb_integration": False,
            "summary": {
                "capability_count": 9,
                "covered_capability_count": 9,
                "known_runtime_gap_count": 0,
            },
        },
        "context_live_diagnostic_case_matrix": {
            "artifact_type": "accurate_intake_context_live_diagnostic_case_matrix",
            "status": "pass",
            "plan_only": True,
            "live_llm_invoked": False,
            "live_provider_invoked": False,
            "fooddb_used": False,
            "mutation_changed": False,
            "manager_context_packet_schema_changed": False,
            "summary": {
                "case_count": 11,
                "compound_cases": 1,
            },
        },
        "context_conditioned_intent_wall": {
            "artifact_type": "accurate_intake_context_conditioned_intent_wall",
            "status": "pass",
            "summary": {"scenario_count": 11},
            "deterministic_semantic_inference_used": False,
            "mutation_authority": False,
        },
        "correction_removal_fixture_flow": {
            "artifact_type": "accurate_intake_correction_removal_fixture_flow",
            "status": "pass",
            "summary": {"scenario_count": 5},
            "mutation_authority": False,
        },
        "responder_input_contract_fake_smoke": {
            "artifact_type": "accurate_intake_responder_input_contract_fake_smoke",
            "status": "pass",
            "summary": {"scenario_count": 5},
            "live_llm_invoked": False,
        },
        "fixture_packet_emulator": {
            "artifact_type": "accurate_intake_fixture_evidence_packet_emulator",
            "status": "fixture_packet_emulator_ready",
            "fixture_packet_truth": False,
            "fooddb_evidence_used": False,
            "websearch_evidence_used": False,
        },
        "fake_provider_tool_loop_smoke": {
            "artifact_type": "accurate_intake_fake_provider_tool_loop_smoke",
            "status": "fake_provider_tool_loop_smoke_pass",
            "evidence_packet_truth": False,
            "live_llm_invoked": False,
        },
        "review_eval_candidate_pipeline": {
            "artifact_type": "accurate_intake_review_eval_candidate_pipeline",
            "status": "review_eval_candidate_pipeline_ready",
            "review_candidate_count": 5,
            "canonical_eval_promoted": False,
            "fooddb_truth_updated": False,
        },
        "local_operator_data_hygiene_bundle": {
            "artifact_type": "accurate_intake_local_operator_data_hygiene_bundle",
            "status": "local_operator_data_hygiene_ready",
            "writes_performed": False,
            "import_allowed": False,
            "production_db_used": False,
        },
        "mvp_gate_summary": {
            "gate_id": "accurate_intake_mvp_deterministic_v1",
            "status": "pass",
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
        },
    }


def test_pl_ce_local_mvp_candidate_bundle_is_human_review_candidate_only() -> None:
    artifact = build_pl_ce_local_mvp_candidate_bundle_artifact(_valid_inputs())

    assert artifact["artifact_type"] == "accurate_intake_pl_ce_local_mvp_candidate_bundle"
    assert artifact["status"] == "pl_ce_local_mvp_candidate_ready_for_human_review"
    assert artifact["activation_gate_status"] == "blocked_pending_human_and_browser_activation"
    assert artifact["required_inputs"] == REQUIRED_INPUTS
    assert artifact["aggregate_only"] is True
    assert artifact["self_generated_evidence_used"] is False
    assert artifact["local_only"] is True
    assert artifact["diagnostic_only"] is True
    assert artifact["fixture_only"] is True
    assert artifact["ready_for_live_diagnostic_decision"] is False
    assert artifact["ready_for_fdb_integration"] is False
    assert artifact["browser_gate_policy"]["local_mvp_candidate_bundle"]["blocked_browser_is_not_pass"] is True  # type: ignore[index]
    assert artifact["browser_gate_policy"]["activation_gate"]["browser_executed_required"] is True  # type: ignore[index]
    assert artifact["live_llm_invoked"] is False
    assert artifact["web_tavily_used"] is False
    assert artifact["fooddb_evidence_used"] is False
    assert artifact["real_fooddb_pass_claimed"] is False
    assert artifact["dogfood_pass"] is False
    assert artifact["product_readiness_claimed"] is False
    assert artifact["private_self_use_approved"] is False
    assert artifact["blockers"] == []


def test_pl_ce_local_mvp_candidate_bundle_includes_new_context_and_responder_slices() -> None:
    artifact = build_pl_ce_local_mvp_candidate_bundle_artifact(_valid_inputs())
    included = artifact["included_artifact_statuses"]

    assert included["short_term_context_runtime_replay"]["status"] == "runtime_replay_diagnostic_pass"  # type: ignore[index]
    assert included["context_coverage_matrix"]["status"] == "context_coverage_matrix_ready_for_human_review"  # type: ignore[index]
    assert included["context_live_diagnostic_case_matrix"]["status"] == "pass"  # type: ignore[index]
    assert included["context_conditioned_intent_wall"]["status"] == "pass"  # type: ignore[index]
    assert included["correction_removal_fixture_flow"]["status"] == "pass"  # type: ignore[index]
    assert included["responder_input_contract_fake_smoke"]["status"] == "pass"  # type: ignore[index]
    assert artifact["summary"]["context_wall_scenarios"] >= 11
    assert artifact["summary"]["short_term_runtime_replay_scenarios"] >= 7
    assert artifact["summary"]["short_term_runtime_replay_current_gap_count"] == 0
    assert artifact["summary"]["context_covered_capabilities"] >= 9
    assert artifact["summary"]["context_known_runtime_gap_count"] == 0
    assert artifact["summary"]["context_live_case_matrix_cases"] >= 11
    assert artifact["summary"]["context_live_case_matrix_compound_cases"] >= 1
    assert artifact["summary"]["correction_removal_scenarios"] == 5
    assert artifact["summary"]["responder_fake_smoke_scenarios"] == 5
    assert artifact["summary"]["review_candidate_count"] >= 5


def test_pl_ce_local_mvp_candidate_bundle_blocks_overclaim_inputs() -> None:
    inputs = _valid_inputs()
    inputs["responder_input_contract_fake_smoke"]["live_llm_invoked"] = True
    inputs["correction_removal_fixture_flow"]["mutation_authority"] = True
    inputs["context_coverage_matrix"]["ready_for_live_diagnostic_decision"] = "ready"
    inputs["context_coverage_matrix"]["context_engineering_fault_claimed"] = True
    inputs["context_coverage_matrix"]["live_websearch_used"] = True
    inputs["context_coverage_matrix"]["deterministic_selected_target"] = True

    artifact = build_pl_ce_local_mvp_candidate_bundle_artifact(inputs)

    assert artifact["status"] == "blocked"
    assert "responder_input_contract_fake_smoke.live_llm_invoked" in artifact["blockers"]
    assert "correction_removal_fixture_flow.mutation_authority" in artifact["blockers"]
    assert "context_coverage_matrix.ready_for_live_diagnostic_decision" in artifact["blockers"]
    assert "context_coverage_matrix.context_engineering_fault_claimed" in artifact["blockers"]
    assert "context_coverage_matrix.live_websearch_used" in artifact["blockers"]
    assert "context_coverage_matrix.deterministic_selected_target" in artifact["blockers"]
    assert artifact["ready_for_live_diagnostic_decision"] is False
    assert artifact["ready_for_fdb_integration"] is False


def test_pl_ce_local_mvp_candidate_bundle_blocks_upstream_blockers() -> None:
    inputs = _valid_inputs()
    inputs["context_coverage_matrix"]["blockers"] = ["coverage.semantic_owner_boundary.missing_fake_provider"]

    artifact = build_pl_ce_local_mvp_candidate_bundle_artifact(inputs)

    assert artifact["status"] == "blocked"
    assert "context_coverage_matrix.upstream_blockers_present" in artifact["blockers"]


def test_pl_ce_local_mvp_candidate_bundle_blocks_missing_runtime_replay() -> None:
    inputs = _valid_inputs()
    inputs["short_term_context_runtime_replay"] = {"status": "missing"}

    artifact = build_pl_ce_local_mvp_candidate_bundle_artifact(inputs)

    assert artifact["status"] == "blocked"
    assert "short_term_context_runtime_replay.unexpected_status:missing" in artifact["blockers"]
    assert (
        "short_term_context_runtime_replay.unexpected_artifact_type:None"
        in artifact["blockers"]
    )


def test_pl_ce_local_mvp_candidate_bundle_blocks_runtime_replay_without_trace_or_coverage() -> None:
    inputs = _valid_inputs()
    inputs["short_term_context_runtime_replay"]["runtime_trace_backed"] = False
    inputs["short_term_context_runtime_replay"]["scenario_count"] = 3
    inputs["short_term_context_runtime_replay"]["summary"]["current_gap_scenarios"] = 1  # type: ignore[index]

    artifact = build_pl_ce_local_mvp_candidate_bundle_artifact(inputs)

    assert artifact["status"] == "blocked"
    assert "short_term_context_runtime_replay.runtime_trace_backed_not_true" in artifact["blockers"]
    assert "short_term_context_runtime_replay.scenario_count_too_low" in artifact["blockers"]
    assert (
        "short_term_context_runtime_replay.current_gap_scenarios_present"
        in artifact["blockers"]
    )


def test_pl_ce_local_mvp_candidate_bundle_blocks_missing_required_input() -> None:
    inputs = _valid_inputs()
    inputs["context_coverage_matrix"] = {"status": "missing"}

    artifact = build_pl_ce_local_mvp_candidate_bundle_artifact(inputs)

    assert artifact["status"] == "blocked"
    assert "context_coverage_matrix.unexpected_status:missing" in artifact["blockers"]


def test_pl_ce_local_mvp_candidate_bundle_blocks_missing_context_live_case_matrix() -> None:
    inputs = _valid_inputs()
    inputs["context_live_diagnostic_case_matrix"] = {"status": "missing"}

    artifact = build_pl_ce_local_mvp_candidate_bundle_artifact(inputs)

    assert artifact["status"] == "blocked"
    assert (
        "context_live_diagnostic_case_matrix.unexpected_status:missing"
        in artifact["blockers"]
    )


def test_pl_ce_local_mvp_candidate_bundle_blocks_context_live_matrix_overclaims() -> None:
    inputs = _valid_inputs()
    inputs["context_live_diagnostic_case_matrix"]["plan_only"] = False
    inputs["context_live_diagnostic_case_matrix"]["live_provider_invoked"] = True
    inputs["context_live_diagnostic_case_matrix"]["fooddb_used"] = True

    artifact = build_pl_ce_local_mvp_candidate_bundle_artifact(inputs)

    assert artifact["status"] == "blocked"
    assert "context_live_diagnostic_case_matrix.plan_only_not_true" in artifact["blockers"]
    assert "context_live_diagnostic_case_matrix.live_provider_invoked" in artifact["blockers"]
    assert "context_live_diagnostic_case_matrix.fooddb_used" in artifact["blockers"]


def test_pl_ce_local_mvp_candidate_bundle_allows_context_matrix_known_runtime_gaps() -> None:
    inputs = _valid_inputs()
    inputs["context_coverage_matrix"] = {
        **inputs["context_coverage_matrix"],
        "status": "context_coverage_matrix_ready_with_known_runtime_gaps",
        "summary": {
            "capability_count": 9,
            "covered_capability_count": 9,
            "known_runtime_gap_count": 1,
        },
        "known_runtime_gap_signals": ["runtime_back_reference_heuristic_attached_target"],
    }

    artifact = build_pl_ce_local_mvp_candidate_bundle_artifact(inputs)

    assert artifact["status"] == "pl_ce_local_mvp_candidate_ready_for_human_review"
    assert artifact["summary"]["context_known_runtime_gap_count"] == 1
    assert artifact["context_engineering_fault_claimed"] is False


def test_pl_ce_local_mvp_candidate_bundle_blocks_swapped_artifact_identity() -> None:
    inputs = _valid_inputs()
    inputs["ui_same_truth_contract"] = {
        **inputs["ui_same_truth_contract"],
        "artifact_type": "accurate_intake_context_quality_pack",
    }
    inputs["mvp_gate_summary"] = {
        **inputs["mvp_gate_summary"],
        "gate_id": "wrong_gate",
    }

    artifact = build_pl_ce_local_mvp_candidate_bundle_artifact(inputs)

    assert artifact["status"] == "blocked"
    assert "ui_same_truth_contract.unexpected_artifact_type:accurate_intake_context_quality_pack" in artifact["blockers"]
    assert "mvp_gate_summary.unexpected_gate_id:wrong_gate" in artifact["blockers"]


def test_pl_ce_local_mvp_candidate_bundle_records_blocked_browser_as_activation_gap() -> None:
    payloads = _valid_inputs()
    payloads["optional_browser_evidence"] = {
        "status": "blocked",
        "browser_executed": False,
    }
    blockers, activation_gap_signals = module._validate_input_artifacts(payloads)

    assert blockers == []
    assert (
        "optional_browser_evidence.browser_execution_blocked_for_activation"
        in activation_gap_signals
    )


def test_pl_ce_local_mvp_candidate_bundle_cli_writes_artifact_from_existing_artifacts(
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "pl_ce_local_mvp_candidate_bundle.json"
    args = ["--output", str(output_path)]
    for group_id, payload in _valid_inputs().items():
        artifact_path = tmp_path / f"{group_id}.json"
        artifact_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        args.extend(["--artifact", f"{group_id}={artifact_path}"])

    from scripts.build_accurate_intake_pl_ce_local_mvp_candidate_bundle import main

    exit_code = main(args)

    assert exit_code == 0
    artifact = json.loads(output_path.read_text(encoding="utf-8"))
    assert artifact["status"] == "pl_ce_local_mvp_candidate_ready_for_human_review"
    assert artifact["included_artifact_statuses"]["mvp_gate_summary"]["source_artifact_path"]


def test_pl_ce_local_mvp_candidate_bundle_cli_blocks_missing_artifact(tmp_path: Path) -> None:
    output_path = tmp_path / "pl_ce_local_mvp_candidate_bundle.json"
    from scripts.build_accurate_intake_pl_ce_local_mvp_candidate_bundle import main

    exit_code = main(
        [
            "--artifact",
            f"context_conditioned_intent_wall={tmp_path / 'missing.json'}",
            "--output",
            str(output_path),
        ]
    )

    assert exit_code == 1
    artifact = json.loads(output_path.read_text(encoding="utf-8"))
    assert artifact["status"] == "blocked"
    assert "context_conditioned_intent_wall.unexpected_status:missing" in artifact["blockers"]


def test_pl_ce_local_mvp_candidate_bundle_cli_rejects_unknown_artifact_group(
    tmp_path: Path,
    capsys,
) -> None:
    output_path = tmp_path / "pl_ce_local_mvp_candidate_bundle.json"
    from scripts.build_accurate_intake_pl_ce_local_mvp_candidate_bundle import main

    exit_code = main(
        [
            "--artifact",
            f"ui_same_truth_contract_typo={tmp_path / 'ui.json'}",
            "--output",
            str(output_path),
        ]
    )
    printed = json.loads(capsys.readouterr().out)

    assert exit_code == 2
    assert printed["status"] == "invalid_arguments"
    assert printed["unknown_artifact_groups"] == ["ui_same_truth_contract_typo"]
    assert not output_path.exists()


def test_pl_ce_local_mvp_candidate_bundle_stays_out_of_forbidden_boundaries() -> None:
    source_paths = [
        Path("app/composition/accurate_intake_pl_ce_local_mvp_candidate_bundle.py"),
        Path("scripts/build_accurate_intake_pl_ce_local_mvp_candidate_bundle.py"),
    ]
    forbidden = [
        "NutritionEvidenceStorePort",
        "FoodEvidenceRecord",
        "PacketReadyAnchor",
        "tavily_adapter",
        "Tavily",
        "Kimi",
        "GrokFast",
        "live_llm_invoked = True",
        "web_tavily_used = True",
        "ready_for_live_diagnostic_decision = True",
        "ready_for_fdb_integration = True",
        "live_provider_invoked = True",
        "fooddb_used = True",
    ]
    for path in source_paths:
        source = path.read_text(encoding="utf-8")
        for fragment in forbidden:
            assert fragment not in source


def test_ci_runs_pl_ce_local_mvp_candidate_bundle() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "test_accurate_intake_pl_ce_local_mvp_candidate_bundle.py" in workflow
    assert "build_accurate_intake_pl_ce_local_mvp_candidate_bundle.py" in workflow
    assert "accurate_intake_pl_ce_local_mvp_candidate_bundle_ci.json" in workflow
    assert "accurate_intake_pl_ce_context_coverage_matrix_ci.json" in workflow
    assert "accurate_intake_short_term_context_runtime_replay_ci.json" in workflow
    assert (
        "--artifact short_term_context_runtime_replay=artifacts/accurate_intake_short_term_context_runtime_replay_ci.json"
        in workflow
    )
    assert "--artifact context_coverage_matrix=artifacts/accurate_intake_pl_ce_context_coverage_matrix_ci.json" in workflow
    assert "accurate_intake_context_live_diagnostic_case_matrix_ci.json" in workflow
    assert (
        "--artifact context_live_diagnostic_case_matrix=artifacts/accurate_intake_context_live_diagnostic_case_matrix_ci.json"
        in workflow
    )
    assert "accurate-intake-pl-ce-local-mvp-candidate-bundle-report" in workflow
    assert "accurate_intake_ui_same_truth_render_contract_ci.json" in workflow
    assert "plce_candidate_fixture_smoke.sqlite3" in workflow
