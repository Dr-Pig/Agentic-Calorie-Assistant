from __future__ import annotations

import json
from pathlib import Path

from app.composition.accurate_intake_fake_provider_context_smoke import (
    build_fake_provider_context_smoke_artifact,
)


def test_fake_provider_context_smoke_reuses_live_shape_without_live_provider() -> None:
    artifact = build_fake_provider_context_smoke_artifact()

    assert artifact["artifact_type"] == "accurate_intake_fake_provider_context_smoke"
    assert artifact["claim_scope"] == "fake_provider_context_smoke"
    assert artifact["status"] == "pass"
    assert artifact["provider_mode"] == "fake_provider_contract_test"
    assert artifact["live_provider_called"] is False
    assert artifact["live_llm_invoked"] is False
    assert artifact["web_tavily_used"] is False
    assert artifact["ready_for_live_diagnostic_decision"] is False
    assert artifact["final_semantic_decision_source"] == "fixture_manager_structured_decision"
    assert artifact["deterministic_semantic_inference_used"] is False
    assert artifact["raw_text_intent_router_used"] is False
    assert artifact["tool_loop_trace_attributable"] is True

    provider_input = artifact["provider_input_summary"]
    assert provider_input["context_policy_version_present"] is True
    assert provider_input["loaded_context_summary_present"] is True
    assert provider_input["omitted_context_summary_present"] is True
    assert provider_input["target_candidates_present"] is True
    assert provider_input["forbidden_context_excluded"] is True
    assert provider_input["manager_context_packet_schema_changed"] is False


def test_fake_provider_context_smoke_script_writes_artifact(tmp_path: Path) -> None:
    output_path = tmp_path / "fake_context_smoke.json"

    from scripts.run_accurate_intake_fake_provider_context_smoke import main

    exit_code = main(["--output", str(output_path)])

    assert exit_code == 0
    artifact = json.loads(output_path.read_text(encoding="utf-8"))
    assert artifact["status"] == "pass"
    assert artifact["live_provider_called"] is False
