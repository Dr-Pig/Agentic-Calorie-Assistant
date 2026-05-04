from __future__ import annotations

import json
from pathlib import Path

from app.composition.accurate_intake_fake_provider_context_smoke import (
    build_fake_provider_context_smoke_artifact,
)
from app.composition.accurate_intake_fake_provider_tool_loop_smoke import (
    build_fake_provider_tool_loop_smoke_artifact,
)
from app.composition.accurate_intake_fixture_evidence_packet_emulator import (
    build_fixture_evidence_packet_emulator_artifact,
)
from scripts import run_accurate_intake_fake_provider_tool_loop_smoke as module


def test_fake_provider_tool_loop_smoke_combines_context_and_fixture_evidence_packets() -> None:
    artifact = build_fake_provider_tool_loop_smoke_artifact(
        context_smoke=build_fake_provider_context_smoke_artifact(),
        fixture_packet_emulator=build_fixture_evidence_packet_emulator_artifact(),
    )

    assert artifact["artifact_type"] == "accurate_intake_fake_provider_tool_loop_smoke"
    assert artifact["status"] == "fake_provider_tool_loop_smoke_pass"
    assert artifact["provider_mode"] == "fake_provider_contract_test"
    assert artifact["provider_input_summary"]["context_policy_version_present"] is True
    assert artifact["provider_input_summary"]["fixture_evidence_packets_present"] is True
    assert artifact["provider_input_summary"]["forbidden_context_excluded"] is True
    assert artifact["tool_loop_trace_attributable"] is True
    assert artifact["final_semantic_decision_source"] == "fixture_manager_structured_decision"
    assert artifact["deterministic_semantic_inference_used"] is False
    assert artifact["raw_text_intent_router_used"] is False
    assert artifact["mutation_authority"] is False
    assert artifact["live_llm_invoked"] is False
    assert artifact["web_tavily_used"] is False
    assert artifact["evidence_packet_truth"] is False
    assert artifact["ready_for_live_diagnostic_decision"] is False


def test_fake_provider_tool_loop_smoke_rejects_missing_manager_consumable_fixture_packet() -> None:
    packet_emulator = build_fixture_evidence_packet_emulator_artifact(
        overrides={
            "approved_common_serving_anchor_fixture": {"manager_consumable": False},
            "approved_exact_card_fixture": {"manager_consumable": False},
            "missing_evidence": {"manager_consumable": False},
            "ambiguous_candidates": {"manager_consumable": False},
        }
    )

    artifact = build_fake_provider_tool_loop_smoke_artifact(
        context_smoke=build_fake_provider_context_smoke_artifact(),
        fixture_packet_emulator=packet_emulator,
    )

    assert artifact["status"] == "fail"
    assert "fixture_packet_emulator.no_manager_consumable_packets" in artifact["blockers"]


def test_fake_provider_tool_loop_smoke_rejects_live_or_truth_overclaims() -> None:
    context_smoke = build_fake_provider_context_smoke_artifact()
    context_smoke["live_llm_invoked"] = True
    packet_emulator = build_fixture_evidence_packet_emulator_artifact()
    packet_emulator["fixture_packet_truth"] = True

    artifact = build_fake_provider_tool_loop_smoke_artifact(
        context_smoke=context_smoke,
        fixture_packet_emulator=packet_emulator,
    )

    assert artifact["status"] == "fail"
    assert "context_smoke.live_llm_invoked" in artifact["blockers"]
    assert "fixture_packet_emulator.fixture_packet_truth" in artifact["blockers"]


def test_fake_provider_tool_loop_smoke_cli_writes_artifact(tmp_path: Path, capsys) -> None:
    output_path = tmp_path / "fake-tool-loop.json"

    exit_code = module.main(["--output", str(output_path)])
    printed = json.loads(capsys.readouterr().out)
    artifact = json.loads(output_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert artifact == printed
    assert artifact["status"] == "fake_provider_tool_loop_smoke_pass"


def test_fake_provider_tool_loop_smoke_script_stays_out_of_fooddb_websearch_and_live_boundaries() -> None:
    source = Path("scripts/run_accurate_intake_fake_provider_tool_loop_smoke.py").read_text(encoding="utf-8")

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
