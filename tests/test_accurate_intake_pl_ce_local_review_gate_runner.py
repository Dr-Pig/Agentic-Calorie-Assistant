from __future__ import annotations

import ast
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _write(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _required_payloads() -> dict[str, dict[str, object]]:
    return {
        "browser_shell_smoke": {
            "artifact_type": "accurate_intake_browser_shell_smoke",
            "status": "pass",
            "browser_executed": True,
            "live_llm_invoked": False,
            "web_tavily_used": False,
        },
        "browser_fixture_dogfood": {
            "artifact_type": "accurate_intake_browser_one_day_fixture_dogfood",
            "status": "browser_fixture_pass",
            "fixture_evidence_used": True,
            "fooddb_evidence_used": False,
            "real_fooddb_pass_claimed": False,
            "dogfood_pass": False,
        },
        "browser_realistic_dogfood": {
            "artifact_type": "accurate_intake_browser_realistic_web_dogfood_v2",
            "status": "browser_diagnostic_pass_with_fixture_evidence_gap",
            "fixture_evidence_used": True,
            "fooddb_evidence_used": False,
            "real_fooddb_pass_claimed": False,
            "dogfood_pass": False,
        },
        "fixture_full_product_loop_e2e": {
            "artifact_type": "accurate_intake_fixture_full_product_loop_e2e",
            "status": "fixture_product_loop_e2e_diagnostic_pass",
            "fixture_evidence_used": True,
            "fooddb_evidence_used": False,
            "websearch_evidence_used": False,
            "real_fooddb_pass_claimed": False,
            "dogfood_pass": False,
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
        },
        "pl_ce_review_bundle": {
            "artifact_type": "accurate_intake_product_loop_review_bundle_v1",
            "status": "product_loop_context_diagnostic_ready_for_human_review",
            "ready_for_fdb_integration": False,
            "real_fooddb_pass_claimed": False,
        },
        "context_review": {
            "artifact_type": "accurate_intake_context_review_artifact",
            "status": "generated",
            "context_engineering_fault_claimed": False,
        },
        "context_target_candidate_eval": {
            "artifact_type": "accurate_intake_context_target_candidate_eval",
            "status": "generated",
            "deterministic_selected_target": False,
        },
        "context_replay_pack": {
            "artifact_type": "accurate_intake_context_replay_pack",
            "status": "generated",
            "deterministic_semantic_inference_used": False,
            "raw_text_intent_router_used": False,
            "mutation_authority": False,
            "manager_context_packet_schema_changed": False,
        },
        "context_window_diagnostic": {
            "artifact_type": "accurate_intake_context_window_diagnostic",
            "status": "generated",
            "long_term_memory_used": False,
            "proactive_or_rescue_used": False,
        },
        "context_quality_pack": {
            "artifact_type": "accurate_intake_context_quality_pack",
            "status": "context_quality_diagnostic_pass",
            "context_engineering_fault_claimed": False,
            "manager_context_packet_schema_changed": False,
            "deterministic_semantic_inference_used": False,
            "mutation_authority": False,
            "ready_for_live_diagnostic_decision": False,
        },
        "fixture_evidence_packet_emulator": {
            "artifact_type": "accurate_intake_fixture_evidence_packet_emulator",
            "status": "fixture_packet_emulator_ready",
            "fixture_evidence_used": True,
            "fixture_packet_truth": False,
            "fooddb_evidence_used": False,
            "websearch_evidence_used": False,
            "web_tavily_used": False,
            "ready_for_fdb_integration": False,
        },
        "fake_provider_tool_loop_smoke": {
            "artifact_type": "accurate_intake_fake_provider_tool_loop_smoke",
            "status": "fake_provider_tool_loop_smoke_pass",
            "provider_mode": "fake_provider_contract_test",
            "final_semantic_decision_source": "fixture_manager_structured_decision",
            "deterministic_semantic_inference_used": False,
            "raw_text_intent_router_used": False,
            "mutation_authority": False,
            "live_llm_invoked": False,
            "web_tavily_used": False,
            "evidence_packet_truth": False,
            "ready_for_live_diagnostic_decision": False,
        },
        "review_eval_candidate_pipeline": {
            "artifact_type": "accurate_intake_review_eval_candidate_pipeline",
            "status": "review_eval_candidate_pipeline_ready",
            "raw_traces_review_input_only": True,
            "canonical_eval_promoted": False,
            "fooddb_truth_updated": False,
            "ready_for_live_diagnostic_decision": False,
        },
        "local_operator_data_hygiene_bundle": {
            "artifact_type": "accurate_intake_local_operator_data_hygiene_bundle",
            "status": "local_operator_data_hygiene_ready",
            "local_only": True,
            "contains_personal_diet_logs": True,
            "do_not_commit": True,
            "writes_performed": False,
            "import_allowed": False,
            "production_db_used": False,
            "fooddb_truth_updated": False,
        },
        "mvp_gate": {"status": "pass"},
    }


def _artifact_args(artifact_dir: Path, groups: tuple[str, ...]) -> list[str]:
    args: list[str] = []
    for group_id in groups:
        args.extend(["--artifact", f"{group_id}={artifact_dir / f'{group_id}.json'}"])
    return args


def test_pl_ce_local_review_gate_runner_writes_manifest_and_decision_pack(
    tmp_path: Path,
    capsys,
) -> None:
    from scripts.build_accurate_intake_pl_ce_local_review_decision_pack import (
        REQUIRED_PL_CE_LOCAL_REVIEW_EVIDENCE,
    )
    from scripts.run_accurate_intake_pl_ce_local_review_gate import main

    artifact_dir = tmp_path / "artifacts"
    for group_id, payload in _required_payloads().items():
        _write(artifact_dir / f"{group_id}.json", payload)
    manifest_output = tmp_path / "manifest.json"
    decision_output = tmp_path / "decision.json"

    exit_code = main(
        [
            "--manifest-output",
            str(manifest_output),
            "--decision-output",
            str(decision_output),
            *_artifact_args(artifact_dir, REQUIRED_PL_CE_LOCAL_REVIEW_EVIDENCE),
        ]
    )
    printed = json.loads(capsys.readouterr().out)
    manifest = json.loads(manifest_output.read_text(encoding="utf-8"))
    decision = json.loads(decision_output.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert printed["manifest_status"] == "complete"
    assert printed["decision_status"] == "ready_for_human_pl_ce_review"
    assert manifest["_manifest_metadata"]["status"] == "complete"
    assert decision["status"] == "ready_for_human_pl_ce_review"
    assert decision["ready_for_live_diagnostic_decision"] is False
    assert decision["ready_for_fdb_integration"] is False


def test_pl_ce_local_review_gate_runner_blocks_missing_artifact_without_autofix(
    tmp_path: Path,
    capsys,
) -> None:
    from scripts.build_accurate_intake_pl_ce_local_review_decision_pack import (
        REQUIRED_PL_CE_LOCAL_REVIEW_EVIDENCE,
    )
    from scripts.run_accurate_intake_pl_ce_local_review_gate import main

    artifact_dir = tmp_path / "artifacts"
    payloads = _required_payloads()
    payloads.pop("fake_provider_tool_loop_smoke")
    for group_id, payload in payloads.items():
        _write(artifact_dir / f"{group_id}.json", payload)
    manifest_output = tmp_path / "manifest.json"
    decision_output = tmp_path / "decision.json"

    exit_code = main(
        [
            "--manifest-output",
            str(manifest_output),
            "--decision-output",
            str(decision_output),
            *_artifact_args(artifact_dir, REQUIRED_PL_CE_LOCAL_REVIEW_EVIDENCE),
        ]
    )
    printed = json.loads(capsys.readouterr().out)
    manifest = json.loads(manifest_output.read_text(encoding="utf-8"))
    decision = json.loads(decision_output.read_text(encoding="utf-8"))

    assert exit_code == 1
    assert printed["manifest_status"] == "blocked_missing_evidence"
    assert printed["decision_status"] == "blocked"
    assert printed["missing_evidence"] == ["fake_provider_tool_loop_smoke"]
    assert manifest["fake_provider_tool_loop_smoke"]["autofix_attempted"] is False
    assert decision["status"] == "blocked"
    assert "fake_provider_tool_loop_smoke" in decision["missing_evidence"]


def test_pl_ce_local_review_gate_runner_blocks_unsafe_flags(tmp_path: Path, capsys) -> None:
    from scripts.build_accurate_intake_pl_ce_local_review_decision_pack import (
        REQUIRED_PL_CE_LOCAL_REVIEW_EVIDENCE,
    )
    from scripts.run_accurate_intake_pl_ce_local_review_gate import main

    artifact_dir = tmp_path / "artifacts"
    payloads = _required_payloads()
    payloads["fake_provider_tool_loop_smoke"]["live_llm_invoked"] = True
    for group_id, payload in payloads.items():
        _write(artifact_dir / f"{group_id}.json", payload)
    manifest_output = tmp_path / "manifest.json"
    decision_output = tmp_path / "decision.json"

    exit_code = main(
        [
            "--manifest-output",
            str(manifest_output),
            "--decision-output",
            str(decision_output),
            *_artifact_args(artifact_dir, REQUIRED_PL_CE_LOCAL_REVIEW_EVIDENCE),
        ]
    )
    printed = json.loads(capsys.readouterr().out)
    decision = json.loads(decision_output.read_text(encoding="utf-8"))

    assert exit_code == 1
    assert printed["decision_status"] == "blocked"
    assert "fake_provider_tool_loop_smoke_live_llm_invoked" in printed["blockers"]
    assert "fake_provider_tool_loop_smoke_live_llm_invoked" in decision["blockers"]
    assert decision["live_llm_invoked"] is False


def test_pl_ce_local_review_gate_runner_rejects_bad_artifact_overrides_with_argparse_error(
    capsys,
) -> None:
    from scripts.run_accurate_intake_pl_ce_local_review_gate import main

    with pytest.raises(SystemExit) as missing_equals:
        main(["--artifact", "not_a_pair"])
    first_error = capsys.readouterr().err

    with pytest.raises(SystemExit) as unknown_group:
        main(["--artifact", "unknown_group=artifact.json"])
    second_error = capsys.readouterr().err

    assert missing_equals.value.code == 2
    assert unknown_group.value.code == 2
    assert "--artifact must be group_id=path" in first_error
    assert "Unknown PL+CE evidence group" in second_error


def test_pl_ce_local_review_gate_runner_stays_out_of_live_fooddb_and_websearch_boundaries() -> None:
    source = Path("scripts/run_accurate_intake_pl_ce_local_review_gate.py").read_text(
        encoding="utf-8"
    )
    tree = ast.parse(source)
    imported_modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_modules.add(node.module)

    for fragment in (
        "NutritionEvidenceStorePort",
        "FoodEvidenceRecord",
        "PacketReadyAnchor",
        "TavilyClient",
        "BuilderSpaceAdapter",
        "builderspace_adapter",
        "Food Evidence promotion policy",
    ):
        assert fragment not in source
    for forbidden_import in (
        "requests",
        "httpx",
        "urllib",
        "openai",
        "app.providers",
    ):
        assert forbidden_import not in imported_modules
