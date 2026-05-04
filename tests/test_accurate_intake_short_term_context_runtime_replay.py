from __future__ import annotations

import json
from pathlib import Path

from app.composition.accurate_intake_short_term_context_runtime_replay import (
    build_short_term_context_runtime_replay_artifact,
)


def test_short_term_context_runtime_replay_matrix_reports_runtime_context_without_claiming_semantics() -> None:
    artifact = build_short_term_context_runtime_replay_artifact()

    assert artifact["artifact_type"] == "accurate_intake_short_term_context_runtime_replay"
    assert artifact["status"] == "runtime_replay_diagnostic_pass"
    assert artifact["scenario_count"] == 7
    assert artifact["runtime_trace_backed"] is True
    assert artifact["diagnostic_only"] is True
    assert artifact["context_engineering_fault_claimed"] is False
    assert artifact["manager_context_packet_schema_changed"] is False
    assert artifact["deterministic_semantic_inference_used"] is False
    assert artifact["raw_text_intent_router_used"] is False
    assert artifact["mutation_authority"] is False
    assert artifact["live_llm_invoked"] is False
    assert artifact["web_tavily_used"] is False
    assert artifact["fooddb_truth_updated"] is False
    assert artifact["summary"]["pending_pin_scenarios"] >= 2
    assert artifact["summary"]["target_candidate_scenarios"] >= 4
    assert artifact["summary"]["current_gap_scenarios"] == 0


def test_short_term_context_runtime_replay_scenarios_keep_target_candidates_read_only() -> None:
    artifact = build_short_term_context_runtime_replay_artifact()

    for scenario in artifact["scenarios"]:
        assert scenario["context_policy_version_present"] is True
        assert scenario["loaded_context_summary_present"] is True
        assert scenario["omitted_context_summary_present"] is True
        assert scenario["forbidden_context_detected"] is False
        assert scenario["context_packet_read_only"] is True
        assert scenario["context_packet_mutation_authority"] is False
        assert scenario["deterministic_selected_target"] is False
        assert scenario["semantic_source"] == "manager_or_fixture_structured_decision_required"
        for candidate in scenario["target_candidates"]:
            assert candidate["read_only"] is True
            assert candidate["mutation_authority"] is False
            assert "selected_target" not in candidate


def test_short_term_context_runtime_replay_keeps_back_reference_ambiguous_until_manager_decision() -> None:
    artifact = build_short_term_context_runtime_replay_artifact()
    by_id = {scenario["scenario_id"]: scenario for scenario in artifact["scenarios"]}

    assert by_id["remove_previous_item"]["runtime_attachment_reason"] == "ambiguous_back_reference_requires_manager"
    assert by_id["remove_previous_item"]["runtime_attachment_disposition"] == "answer_only"
    assert by_id["remove_previous_item"]["expected_context_posture"] == "ambiguous_until_manager_decision"
    assert by_id["remove_previous_item"]["gap_signals"] == []
    assert by_id["correct_previous_identity"]["runtime_attachment_reason"] == "ambiguous_back_reference_requires_manager"
    assert by_id["correct_previous_identity"]["runtime_attachment_disposition"] == "answer_only"
    assert by_id["correct_previous_identity"]["gap_signals"] == []
    assert by_id["remove_named_item"]["gap_signals"] == []
    assert by_id["pending_followup_answer"]["pending_followup_present"] is True
    assert by_id["long_chat_with_pinned_pending_draft"]["pending_draft_present"] is True
    assert by_id["long_chat_with_pinned_pending_draft"]["recent_chat_messages_loaded"] == 20
    assert by_id["long_chat_with_pinned_pending_draft"]["recent_chat_messages_omitted"] > 0


def test_short_term_context_runtime_replay_script_writes_artifact(tmp_path: Path, capsys) -> None:
    output_path = tmp_path / "runtime-replay.json"

    from scripts.run_accurate_intake_short_term_context_runtime_replay import main

    exit_code = main(["--output", str(output_path)])
    printed = json.loads(capsys.readouterr().out)
    artifact = json.loads(output_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert printed["status"] == artifact["status"]
    assert artifact["runtime_trace_backed"] is True
    assert artifact["status"] == "runtime_replay_diagnostic_pass"


def test_short_term_context_runtime_replay_stays_out_of_fooddb_websearch_live_and_schema_boundaries() -> None:
    paths = (
        Path("app/composition/accurate_intake_short_term_context_runtime_replay.py"),
        Path("scripts/run_accurate_intake_short_term_context_runtime_replay.py"),
    )
    source = "\n".join(path.read_text(encoding="utf-8") for path in paths)

    for forbidden in (
        "NutritionEvidenceStorePort",
        "FoodEvidenceRecord",
        "PacketReadyAnchor",
        "Tavily",
        "BuilderSpaceAdapter",
        "builderspace_adapter",
        "Kimi",
        "Grok",
    ):
        assert forbidden not in source
