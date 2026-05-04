from __future__ import annotations

import json
from pathlib import Path

from scripts.build_accurate_intake_pl_ce_local_review_decision_pack import (
    build_pl_ce_local_review_decision_pack,
)


def _write(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _required_payloads() -> dict[str, dict[str, object]]:
    return {
        "browser_shell_smoke": {"status": "pass", "browser_executed": True},
        "browser_fixture_dogfood": {
            "status": "browser_fixture_pass",
            "fixture_evidence_used": True,
            "real_fooddb_pass_claimed": False,
            "dogfood_pass": False,
        },
        "browser_realistic_dogfood": {
            "status": "browser_diagnostic_pass_with_fixture_evidence_gap",
            "fixture_evidence_used": True,
            "real_fooddb_pass_claimed": False,
            "dogfood_pass": False,
        },
        "fixture_full_product_loop_e2e": {
            "status": "fixture_product_loop_e2e_diagnostic_pass",
            "fixture_evidence_used": True,
            "fooddb_evidence_used": False,
            "websearch_evidence_used": False,
        },
        "pl_ce_review_bundle": {
            "status": "product_loop_context_diagnostic_ready_for_human_review",
            "ready_for_fdb_integration": False,
        },
        "context_review": {"status": "generated", "manager_context_packet_schema_changed": False},
        "context_target_candidate_eval": {
            "status": "generated",
            "deterministic_selected_target": False,
        },
        "context_replay_pack": {
            "status": "generated",
            "deterministic_semantic_inference_used": False,
            "mutation_authority": False,
        },
        "context_window_diagnostic": {
            "status": "generated",
            "long_term_memory_used": False,
            "proactive_or_rescue_used": False,
        },
        "context_quality_pack": {
            "status": "context_quality_diagnostic_pass",
            "runtime_trace_input_used": True,
            "ready_for_live_diagnostic_decision": False,
        },
        "fixture_evidence_packet_emulator": {
            "status": "fixture_packet_emulator_ready",
            "fixture_packet_truth": False,
            "fooddb_evidence_used": False,
            "websearch_evidence_used": False,
        },
        "fake_provider_tool_loop_smoke": {
            "status": "fake_provider_tool_loop_smoke_pass",
            "live_llm_invoked": False,
            "evidence_packet_truth": False,
        },
        "review_eval_candidate_pipeline": {
            "status": "review_eval_candidate_pipeline_ready",
            "canonical_eval_promoted": False,
            "fooddb_truth_updated": False,
        },
        "local_operator_data_hygiene_bundle": {
            "status": "local_operator_data_hygiene_ready",
            "writes_performed": False,
            "import_allowed": False,
            "production_db_used": False,
        },
        "mvp_gate": {"status": "pass"},
    }


def test_pl_ce_local_review_evidence_manifest_reads_required_artifact_paths(tmp_path: Path) -> None:
    from scripts.build_accurate_intake_pl_ce_local_review_evidence_manifest import (
        DEFAULT_EVIDENCE_PATHS,
        build_pl_ce_local_review_evidence_manifest,
    )

    artifact_dir = tmp_path / "artifacts"
    for group_id, payload in _required_payloads().items():
        _write(artifact_dir / f"{group_id}.json", payload)
    path_overrides = {
        group_id: artifact_dir / f"{group_id}.json"
        for group_id in DEFAULT_EVIDENCE_PATHS
    }

    manifest = build_pl_ce_local_review_evidence_manifest(path_overrides=path_overrides)
    decision_pack = build_pl_ce_local_review_decision_pack(manifest)

    assert manifest["_manifest_metadata"]["artifact_type"] == "accurate_intake_pl_ce_local_review_evidence_manifest"
    assert manifest["_manifest_metadata"]["status"] == "complete"
    assert manifest["_manifest_metadata"]["missing_evidence"] == []
    assert manifest["_manifest_metadata"]["live_llm_invoked"] is False
    assert manifest["_manifest_metadata"]["web_tavily_used"] is False
    assert decision_pack["status"] == "ready_for_human_pl_ce_review"


def test_pl_ce_local_review_evidence_manifest_marks_missing_inputs_without_autofix(tmp_path: Path) -> None:
    from scripts.build_accurate_intake_pl_ce_local_review_evidence_manifest import (
        DEFAULT_EVIDENCE_PATHS,
        build_pl_ce_local_review_evidence_manifest,
    )

    artifact_dir = tmp_path / "artifacts"
    payloads = _required_payloads()
    payloads.pop("fake_provider_tool_loop_smoke")
    for group_id, payload in payloads.items():
        _write(artifact_dir / f"{group_id}.json", payload)
    path_overrides = {
        group_id: artifact_dir / f"{group_id}.json"
        for group_id in DEFAULT_EVIDENCE_PATHS
    }

    manifest = build_pl_ce_local_review_evidence_manifest(path_overrides=path_overrides)
    decision_pack = build_pl_ce_local_review_decision_pack(manifest)

    assert manifest["_manifest_metadata"]["status"] == "blocked_missing_evidence"
    assert manifest["_manifest_metadata"]["missing_evidence"] == ["fake_provider_tool_loop_smoke"]
    assert manifest["fake_provider_tool_loop_smoke"]["status"] == "missing"
    assert manifest["fake_provider_tool_loop_smoke"]["autofix_attempted"] is False
    assert decision_pack["status"] == "blocked"
    assert "fake_provider_tool_loop_smoke" in decision_pack["missing_evidence"]


def test_pl_ce_local_review_evidence_manifest_cli_writes_decision_pack_input(
    tmp_path: Path,
    capsys,
) -> None:
    from scripts import build_accurate_intake_pl_ce_local_review_evidence_manifest as module

    artifact_dir = tmp_path / "artifacts"
    for group_id, payload in _required_payloads().items():
        _write(artifact_dir / f"{group_id}.json", payload)
    output_path = tmp_path / "manifest.json"
    args = ["--output", str(output_path)]
    for group_id in module.DEFAULT_EVIDENCE_PATHS:
        args.extend(["--artifact", f"{group_id}={artifact_dir / f'{group_id}.json'}"])

    exit_code = module.main(args)
    printed = json.loads(capsys.readouterr().out)
    manifest = json.loads(output_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert printed["status"] == "complete"
    assert manifest["_manifest_metadata"]["status"] == "complete"
    assert build_pl_ce_local_review_decision_pack(manifest)["status"] == "ready_for_human_pl_ce_review"


def test_pl_ce_local_review_evidence_manifest_script_stays_out_of_live_and_fooddb_boundaries() -> None:
    source = Path("scripts/build_accurate_intake_pl_ce_local_review_evidence_manifest.py").read_text(
        encoding="utf-8"
    )

    for fragment in (
        "NutritionEvidenceStorePort",
        "FoodEvidenceRecord",
        "PacketReadyAnchor",
        "TavilyClient",
        "BuilderSpaceAdapter",
        "builderspace_adapter",
        "kimi",
        "grok",
    ):
        assert fragment not in source
