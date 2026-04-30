from __future__ import annotations

import importlib
import json
from pathlib import Path


def test_b2_active_runtime_integration_runner_source_avoids_legacy_truth() -> None:
    runner_path = Path("scripts/run_wave1_b2_active_runtime_integration_diagnostic.py")
    source = runner_path.read_text(encoding="utf-8")

    forbidden_markers = (
        "app.runtime.application.phase_a_context",
        "run_v2_" + "bundle1" + "_live_eval",
        "run_v2_" + "bundle2" + "_live_eval",
        "docs/" + "archive",
        "V2_EVAL_" + "BUNDLE",
        "stale " + "oracle",
    )
    for marker in forbidden_markers:
        assert marker not in source


def test_b2_active_runtime_integration_diagnostic_observes_owner_lineage(tmp_path: Path) -> None:
    module = importlib.import_module("scripts.run_wave1_b2_active_runtime_integration_diagnostic")
    output_path = tmp_path / "wave1_b2_active_runtime_integration_diagnostic.json"
    founder_output_path = tmp_path / "wave1_founder_e2e_deterministic_diagnostic.json"
    db_path = tmp_path / "wave1_b2_active_runtime_integration.sqlite3"

    report = module.run_diagnostic(
        output_path=output_path,
        founder_output_path=founder_output_path,
        db_path=db_path,
        local_date="2026-04-30",
    )

    assert output_path.exists()
    assert json.loads(output_path.read_text(encoding="utf-8")) == report
    assert report["artifact_type"] == "wave1_b2_active_runtime_integration_diagnostic"
    assert report["active_entrypoint"] == "app.composition.intake_turn_orchestrator.execute_bundle1_turn"
    assert report["active_entrypoint_verified"] is True
    assert report["provider_mode"] == "deterministic"
    assert report["live_llm_invoked"] is False
    assert report["tavily_live_invoked"] is False
    assert report["runtime_web_activation_approved"] is False
    assert report["readiness_claimed"] is False

    assert report["founder_deterministic_summary"]["pass_count"] == 7
    assert report["founder_deterministic_summary"]["fail_count"] == 0
    assert report["active_runtime_observability"]["nutrition_payload_present"] is True
    assert report["active_runtime_observability"]["web_runtime_trace_present"] is True
    assert report["active_runtime_observability"]["retrieval_intent_source_present"] is True
    assert report["active_runtime_observability"]["source_selection_object_present"] is True
    assert report["active_runtime_observability"]["packet_consumption_trace_present"] is True
    assert report["active_runtime_observability"]["state_delta_present"] is True
    assert report["active_runtime_observability"]["ledger_read_present"] is True
    assert report["active_runtime_observability"]["phase_c_trace_present"] is True
    assert report["active_runtime_observability"]["b2_final_mapping_first_class_present"] is True
    assert report["verdict"] == "diagnostic_observation"
    assert report["failure_layer"] is None
    assert report["missing_first_class_surfaces"] == []
