from __future__ import annotations

from datetime import UTC, datetime, timedelta
import json
from pathlib import Path

from app.composition.accurate_intake_pl_ce_metadata_freshness_pack import (
    build_pl_ce_metadata_freshness_pack,
)


def _fresh_timestamp() -> str:
    return datetime.now(UTC).isoformat()


def _stale_timestamp() -> str:
    return (datetime.now(UTC) - timedelta(days=8)).isoformat()


def _future_timestamp() -> str:
    return (datetime.now(UTC) + timedelta(hours=2)).isoformat()


def _fresh_evidence() -> dict[str, dict[str, object]]:
    return {
        "context_quality_pack": {
            "artifact_type": "accurate_intake_context_quality_pack",
            "artifact_schema_version": "1.0",
            "status": "context_quality_diagnostic_pass",
            "generated_at_utc": _fresh_timestamp(),
            "runtime_trace_input_used": True,
            "short_term_context_runtime_replay_checked": True,
            "context_engineering_fault_claimed": False,
            "manager_context_packet_schema_changed": False,
            "deterministic_semantic_inference_used": False,
            "raw_text_intent_router_used": False,
            "mutation_authority": False,
            "ready_for_live_diagnostic_decision": False,
            "ready_for_fdb_integration": False,
            "live_llm_invoked": False,
            "web_tavily_used": False,
            "fooddb_truth_updated": False,
            "private_self_use_approved": False,
            "product_readiness_claimed": False,
            "summary": {
                "context_replay_scenario_count": 12,
                "pending_pin_scenarios": 3,
                "manager_semantic_required_scenarios": 1,
                "short_term_runtime_replay_scenario_count": 7,
                "short_term_runtime_replay_current_gap_scenarios": 0,
                "fake_provider_handoff_scenario_count": 3,
            },
            "short_term_context_current_gap_scenarios": 0,
        },
        "product_pages_visual_qa": {
            "artifact_type": "accurate_intake_product_pages_visual_qa",
            "artifact_schema_version": "1.0",
            "status": "pass",
            "generated_at_utc": _fresh_timestamp(),
            "browser_executed": True,
            "three_distinct_pages_verified": True,
            "chat_surface_verified": True,
            "today_surface_verified": True,
            "body_surface_verified": True,
            "visible_trace_debug_terms_absent": True,
            "frontend_semantic_owner": False,
            "live_llm_invoked": False,
            "web_tavily_used": False,
            "production_db_used": False,
            "web_readiness_claimed": False,
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
        },
        "pl_ce_local_review_decision_pack": {
            "artifact_type": "accurate_intake_pl_ce_local_review_decision_pack",
            "artifact_schema_version": "1.0",
            "status": "ready_for_human_pl_ce_review",
            "generated_at_utc": _fresh_timestamp(),
            "ready_for_live_diagnostic_decision": False,
            "ready_for_fdb_integration": False,
            "live_llm_invoked": False,
            "web_tavily_used": False,
            "fooddb_truth_updated": False,
            "real_fooddb_pass_claimed": False,
            "dogfood_pass": False,
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
        },
        "ui_same_truth_render_contract": {
            "artifact_type": "accurate_intake_ui_same_truth_render_contract",
            "artifact_schema_version": "1.0",
            "status": "pass",
            "generated_at_utc": _fresh_timestamp(),
            "frontend_semantic_owner": False,
            "runtime_truth_changed": False,
            "mutation_changed": False,
            "live_llm_invoked": False,
            "web_tavily_used": False,
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
        },
    }


def _write(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def test_pl_ce_metadata_freshness_pack_accepts_current_local_diagnostic_metadata() -> None:
    pack = build_pl_ce_metadata_freshness_pack(evidence=_fresh_evidence())

    assert pack["artifact_type"] == "accurate_intake_pl_ce_metadata_freshness_pack"
    assert pack["status"] == "metadata_freshness_ready_for_pl_ce_local_review"
    assert pack["diagnostic_only"] is True
    assert pack["source_status_only"] is True
    assert pack["ready_for_live_diagnostic_decision"] is False
    assert pack["ready_for_fdb_integration"] is False
    assert pack["live_llm_invoked"] is False
    assert pack["web_tavily_used"] is False
    assert pack["fooddb_truth_updated"] is False
    assert pack["real_fooddb_pass_claimed"] is False
    assert pack["dogfood_pass"] is False
    assert pack["product_readiness_claimed"] is False
    assert pack["private_self_use_approved"] is False
    assert pack["summary"]["context_replay_scenario_count"] == 12
    assert pack["summary"]["short_term_context_current_gap_scenarios"] == 0
    assert pack["fresh_artifact_count"] == pack["required_artifact_count"]
    assert pack["blockers"] == []


def test_pl_ce_metadata_freshness_pack_blocks_missing_artifacts_without_autofix() -> None:
    evidence = _fresh_evidence()
    evidence.pop("product_pages_visual_qa")

    pack = build_pl_ce_metadata_freshness_pack(evidence=evidence)

    assert pack["status"] == "blocked"
    assert pack["autofix_attempted"] is False
    assert pack["missing_artifacts"] == ["product_pages_visual_qa"]
    assert "product_pages_visual_qa.missing" in pack["blockers"]
    assert pack["ready_for_live_diagnostic_decision"] is False
    assert pack["ready_for_fdb_integration"] is False


def test_pl_ce_metadata_freshness_pack_blocks_stale_or_identityless_metadata() -> None:
    evidence = _fresh_evidence()
    evidence["context_quality_pack"]["generated_at_utc"] = _stale_timestamp()
    evidence["ui_same_truth_render_contract"].pop("artifact_schema_version")

    pack = build_pl_ce_metadata_freshness_pack(evidence=evidence, max_age_hours=24)

    assert pack["status"] == "blocked"
    assert "context_quality_pack.stale_metadata" in pack["blockers"]
    assert "ui_same_truth_render_contract.missing_artifact_schema_version" in pack["blockers"]
    assert "context_quality_pack" in pack["stale_artifacts"]
    assert "ui_same_truth_render_contract" in pack["invalid_metadata"]


def test_pl_ce_metadata_freshness_pack_blocks_future_metadata_timestamp() -> None:
    evidence = _fresh_evidence()
    evidence["product_pages_visual_qa"]["generated_at_utc"] = _future_timestamp()

    pack = build_pl_ce_metadata_freshness_pack(evidence=evidence, max_age_hours=24)

    assert pack["status"] == "blocked"
    assert "product_pages_visual_qa.future_generated_at_utc" in pack["blockers"]
    assert pack["input_statuses"]["product_pages_visual_qa"]["freshness_status"] == "future"


def test_pl_ce_metadata_freshness_pack_blocks_context_regression_thresholds() -> None:
    evidence = _fresh_evidence()
    evidence["context_quality_pack"]["summary"] = {
        "context_replay_scenario_count": 7,
        "pending_pin_scenarios": 2,
        "manager_semantic_required_scenarios": 0,
        "short_term_runtime_replay_scenario_count": 4,
        "short_term_runtime_replay_current_gap_scenarios": 0,
        "fake_provider_handoff_scenario_count": 1,
    }
    evidence["context_quality_pack"]["short_term_context_current_gap_scenarios"] = 1

    pack = build_pl_ce_metadata_freshness_pack(evidence=evidence)

    assert pack["status"] == "blocked"
    assert "context_quality_pack.context_replay_scenario_count_too_low" in pack["blockers"]
    assert "context_quality_pack.pending_pin_scenarios_too_low" in pack["blockers"]
    assert "context_quality_pack.manager_semantic_required_scenarios_missing" in pack["blockers"]
    assert "context_quality_pack.short_term_runtime_replay_scenario_count_too_low" in pack["blockers"]
    assert "context_quality_pack.short_term_context_current_gap_scenarios_present" in pack["blockers"]
    assert "context_quality_pack.fake_provider_handoff_scenario_count_too_low" in pack["blockers"]


def test_pl_ce_metadata_freshness_pack_blocks_readiness_and_live_overclaims() -> None:
    evidence = _fresh_evidence()
    evidence["pl_ce_local_review_decision_pack"]["ready_for_live_diagnostic_decision"] = "true"
    evidence["product_pages_visual_qa"]["product_readiness_claimed"] = 1
    evidence["ui_same_truth_render_contract"]["frontend_semantic_owner"] = "yes"

    pack = build_pl_ce_metadata_freshness_pack(evidence=evidence)

    assert pack["status"] == "blocked"
    assert "pl_ce_local_review_decision_pack.ready_for_live_diagnostic_decision" in pack["blockers"]
    assert "product_pages_visual_qa.product_readiness_claimed" in pack["blockers"]
    assert "ui_same_truth_render_contract.frontend_semantic_owner" in pack["blockers"]
    assert pack["ready_for_live_diagnostic_decision"] is False
    assert pack["product_readiness_claimed"] is False


def test_pl_ce_metadata_freshness_pack_cli_writes_output(tmp_path: Path, capsys) -> None:
    from scripts import build_accurate_intake_pl_ce_metadata_freshness_pack as module

    artifact_dir = tmp_path / "artifacts"
    for group_id, payload in _fresh_evidence().items():
        _write(artifact_dir / f"{group_id}.json", payload)
    output_path = tmp_path / "metadata-freshness.json"
    args = ["--output", str(output_path), "--max-age-hours", "24"]
    for group_id in module.DEFAULT_EVIDENCE_PATHS:
        args.extend(["--artifact", f"{group_id}={artifact_dir / f'{group_id}.json'}"])

    exit_code = module.main(args)
    printed = json.loads(capsys.readouterr().out)
    pack = json.loads(output_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert printed["status"] == "metadata_freshness_ready_for_pl_ce_local_review"
    assert printed["fresh_artifact_count"] == 4
    assert pack["status"] == "metadata_freshness_ready_for_pl_ce_local_review"
    assert pack["ready_for_fdb_integration"] is False


def test_pl_ce_metadata_freshness_pack_cli_reports_missing_artifacts_as_not_present(
    tmp_path: Path,
    capsys,
) -> None:
    from scripts import build_accurate_intake_pl_ce_metadata_freshness_pack as module

    artifact_dir = tmp_path / "missing-artifacts"
    output_path = tmp_path / "metadata-freshness.json"
    args = ["--output", str(output_path)]
    for group_id in module.DEFAULT_EVIDENCE_PATHS:
        args.extend(["--artifact", f"{group_id}={artifact_dir / f'{group_id}.json'}"])

    exit_code = module.main(args)
    printed = json.loads(capsys.readouterr().out)
    pack = json.loads(output_path.read_text(encoding="utf-8"))

    assert exit_code == 1
    assert printed["status"] == "blocked"
    assert pack["missing_artifacts"] == list(module.DEFAULT_EVIDENCE_PATHS)
    assert pack["input_statuses"]["context_quality_pack"]["present"] is False
    assert pack["autofix_attempted"] is False


def test_pl_ce_metadata_freshness_pack_cli_blocks_invalid_artifact_file(
    tmp_path: Path,
    capsys,
) -> None:
    from scripts import build_accurate_intake_pl_ce_metadata_freshness_pack as module

    artifact_dir = tmp_path / "artifacts"
    for group_id, payload in _fresh_evidence().items():
        _write(artifact_dir / f"{group_id}.json", payload)
    (artifact_dir / "context_quality_pack.json").write_text("{not-json", encoding="utf-8")
    output_path = tmp_path / "metadata-freshness.json"
    args = ["--output", str(output_path)]
    for group_id in module.DEFAULT_EVIDENCE_PATHS:
        args.extend(["--artifact", f"{group_id}={artifact_dir / f'{group_id}.json'}"])

    exit_code = module.main(args)
    printed = json.loads(capsys.readouterr().out)
    pack = json.loads(output_path.read_text(encoding="utf-8"))

    assert exit_code == 1
    assert printed["status"] == "blocked"
    assert "context_quality_pack.invalid_artifact_file" in pack["blockers"]
    assert pack["invalid_metadata"] == ["context_quality_pack"]
    assert pack["input_statuses"]["context_quality_pack"]["present"] is True
    assert pack["input_statuses"]["context_quality_pack"]["status"] == "invalid"


def test_pl_ce_metadata_freshness_pack_cli_rejects_bad_artifact_override_without_traceback(
    capsys,
) -> None:
    from scripts import build_accurate_intake_pl_ce_metadata_freshness_pack as module

    exit_code = None
    try:
        module.main(["--artifact", "not-a-pair"])
    except SystemExit as exc:
        exit_code = exc.code

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "--artifact must be group_id=path" in captured.err
    assert "Traceback" not in captured.err


def test_pl_ce_metadata_freshness_pack_source_stays_out_of_fooddb_websearch_live_boundaries() -> None:
    source_paths = [
        Path("app/composition/accurate_intake_pl_ce_metadata_freshness_pack.py"),
        Path("scripts/build_accurate_intake_pl_ce_metadata_freshness_pack.py"),
    ]
    forbidden = [
        "requests",
        "httpx",
        "urllib",
        "openai",
        "app.providers",
        "TavilyClient",
        "NutritionEvidenceStorePort",
        "FoodEvidenceRecord",
        "PacketReadyAnchor",
        "FoodEvidencePromotion",
        "app.memory",
        "runtime_truth_allowed = True",
    ]

    combined_source = "\n".join(path.read_text(encoding="utf-8") for path in source_paths)
    for fragment in forbidden:
        assert fragment not in combined_source


def test_ci_runs_pl_ce_metadata_freshness_pack_test() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
    manifest = json.loads(
        Path("docs/quality/accurate_intake_mvp_gate_manifest.json").read_text(encoding="utf-8")
    )

    assert "python scripts/verify_accurate_intake_mvp.py --python python" in workflow
    assert "test_accurate_intake_pl_ce_metadata_freshness_pack.py" not in workflow
    groups = {group["group_id"]: group for group in manifest["required_groups"]}
    assert groups["pl_ce_metadata_freshness_pack_contract"]["pytest"] == [
        "tests/test_accurate_intake_pl_ce_metadata_freshness_pack.py"
    ]
