from __future__ import annotations

from pathlib import Path

from app.nutrition.application.websearch_manager_contract_probe import (
    build_fixture_websearch_manager_contract_probe_cases,
    build_websearch_manager_contract_probe,
)


def test_websearch_manager_contract_probe_localizes_intent_alias_gap() -> None:
    artifact = build_websearch_manager_contract_probe()

    assert artifact["artifact_type"] == "accurate_intake_websearch_manager_contract_probe"
    assert artifact["classification"] == "deterministic_contract_probe_only"
    assert artifact["status"] == "diagnostic_fail"
    assert artifact["live_provider_used"] is False
    assert artifact["live_websearch_used"] is False
    assert artifact["manager_contract_changed"] is False
    assert artifact["prompt_changed"] is False
    assert artifact["schema_changed"] is False
    assert artifact["summary"]["case_count"] == 2
    assert artifact["summary"]["websearch_expansion_allowed"] is False
    assert artifact["summary"]["next_recommended_slice"] == "narrow_prompt_schema_intent_alias_probe"
    assert "manager_output_contract_violation" in artifact["summary"]["failure_families"]
    assert "manager_intent_alias_gap" in artifact["summary"]["failure_families"]
    assert "intent_type_present_intent_missing" in artifact["summary"]["repair_hypotheses"]

    for case in artifact["cases"]:
        assert case["missing_required_fields"] == ["intent"]
        assert "intent_type_present_intent_missing" in case["shape_patterns"]
        assert "candidate_only_target_attachment_present" in case["shape_patterns"]
        assert case["raw_manager_output_included"] is False
        assert case["provider_trace_included"] is False


def test_websearch_manager_contract_probe_does_not_persist_raw_candidate_payload() -> None:
    artifact = build_websearch_manager_contract_probe()
    serialized = str(artifact)

    assert "source_url" not in serialized
    assert "Milksha pearl black tea latte" not in serialized
    assert "Starbucks iced latte large" not in serialized
    assert "observed_manager_output" not in serialized
    assert "candidate_packet_id" not in serialized


def test_websearch_manager_contract_probe_passes_when_required_intent_exists() -> None:
    case = build_fixture_websearch_manager_contract_probe_cases()[0]
    observed = dict(case["observed_manager_output"])
    observed["intent"] = observed["intent_type"]
    observed["target_attachment"] = {}
    observed["evidence_posture"] = "candidate_only"
    observed["workflow_effect"] = "answer_only"
    observed["final_action"] = "answer_only"
    observed["semantic_decision"] = {
        "current_turn_intent": "log_food_item",
        "target_attachment_resolution": "none",
        "evidence_requirement": "none",
        "final_action_candidate": "answer_only",
        "followup_posture": "none",
        "mutation_intent_candidate": "no_mutation",
    }
    case["observed_manager_output"] = observed

    artifact = build_websearch_manager_contract_probe(cases=[case])

    assert artifact["status"] == "pass"
    assert artifact["summary"]["failure_families"] == []
    assert artifact["summary"]["next_recommended_slice"] == "inspect_websearch_manager_contract_failures"


def test_websearch_manager_contract_probe_script_roundtrip(tmp_path: Path) -> None:
    from app.shared.infra.json_artifacts import read_json_artifact
    from scripts.build_accurate_intake_websearch_manager_contract_probe import main

    output = tmp_path / "contract_probe.json"

    assert main(["--output", str(output)]) == 0

    artifact = read_json_artifact(output)
    assert artifact["artifact_type"] == "accurate_intake_websearch_manager_contract_probe"
    assert artifact["summary"]["next_recommended_slice"] == "narrow_prompt_schema_intent_alias_probe"


def test_websearch_manager_contract_probe_has_no_live_or_websearch_imports() -> None:
    source_paths = [
        Path("app/nutrition/application/websearch_manager_contract_probe.py"),
        Path("scripts/build_accurate_intake_websearch_manager_contract_probe.py"),
    ]
    forbidden = [
        "BuilderSpaceAdapter",
        "Tavily",
        "tavily",
        "requests.",
        "httpx.",
        "allow_live",
        "Kimi",
        "kimi-k2.5",
    ]
    for path in source_paths:
        source = path.read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in source
