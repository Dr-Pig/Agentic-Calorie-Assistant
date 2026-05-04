from __future__ import annotations

from pathlib import Path

from app.nutrition.application.websearch_candidate_packet_smoke import (
    build_websearch_candidate_packet_smoke,
)
from app.nutrition.application.websearch_manager_output_diagnostic import (
    build_fixture_websearch_manager_outputs,
    build_websearch_manager_output_diagnostic,
    evaluate_manager_output_against_websearch_packet,
)
from app.nutrition.application.websearch_manager_packet_smoke import (
    build_websearch_manager_packet_projection,
)
from app.nutrition.application.tool_evidence_result import build_tool_evidence_result


def _manager_packet_artifact() -> dict:
    packet_artifact = build_websearch_candidate_packet_smoke()
    packets = tuple(case["websearch_candidate_packet"] for case in packet_artifact["cases"])
    tool_result = build_tool_evidence_result(
        tool_name="search_official_nutrition",
        tool_call_id="tool-call-websearch-manager-output",
        evidence_packets=packets,
        trace_context={
            "packet_artifact_type": packet_artifact["artifact_type"],
            "packet_claim_scope": packet_artifact["claim_scope"],
            "live_websearch_used": False,
        },
    )
    return build_websearch_manager_packet_projection(
        tool_evidence_artifact={
            "artifact_type": "accurate_intake_websearch_tool_evidence_result_smoke",
            "tool_evidence_result": tool_result,
        }
    )


def test_websearch_manager_output_diagnostic_passes_fixture_outputs_without_mutation() -> None:
    packet_artifact = _manager_packet_artifact()
    manager_outputs = build_fixture_websearch_manager_outputs(packet_artifact=packet_artifact)

    diagnostic = build_websearch_manager_output_diagnostic(
        packet_artifact=packet_artifact,
        manager_outputs=manager_outputs,
        live_provider_used=False,
    )

    assert diagnostic["artifact_type"] == "accurate_intake_websearch_manager_output_diagnostic"
    assert diagnostic["classification"] == "deterministic_diagnostic_only"
    assert diagnostic["status"] == "pass"
    assert diagnostic["live_provider_used"] is False
    assert diagnostic["live_websearch_used"] is False
    assert diagnostic["runtime_truth_changed"] is False
    assert diagnostic["runtime_mutation_attempted"] is False
    assert diagnostic["summary"]["case_count"] == 4
    assert diagnostic["summary"]["pass_count"] == 4
    assert diagnostic["summary"]["fail_count"] == 0
    assert diagnostic["summary"]["failure_families"] == []

    for case in diagnostic["cases"]:
        assert "allowed_evidence_refs" not in case
        output = case["manager_output"]
        assert output["item_results"] == []
        assert output["semantic_decision"]["mutation_intent_candidate"] == "no_mutation"
        assert case["runtime_mutation_attempted"] is False


def test_websearch_manager_output_diagnostic_rejects_live_provider_flag() -> None:
    packet_artifact = _manager_packet_artifact()
    manager_outputs = build_fixture_websearch_manager_outputs(packet_artifact=packet_artifact)

    diagnostic = build_websearch_manager_output_diagnostic(
        packet_artifact=packet_artifact,
        manager_outputs=manager_outputs,
        live_provider_used=True,
    )

    assert diagnostic["status"] == "diagnostic_fail"
    assert diagnostic["live_provider_used"] is True
    assert "live_provider_used_in_deterministic_diagnostic" in diagnostic["summary"]["failure_families"]


def test_websearch_manager_output_diagnostic_flags_truth_and_mutation_shortcuts() -> None:
    packet_case = _manager_packet_artifact()["cases"][0]
    manager_output = {
        "manager_action": "final",
        "final_action": "commit",
        "workflow_effect": "food_log_candidate",
        "item_results": [{"food_name": "Milksha", "likely_kcal": 400}],
        "evidence_used": [packet_case["case_id"]],
        "semantic_decision": {"mutation_intent_candidate": "canonical_write"},
    }

    evaluation = evaluate_manager_output_against_websearch_packet(
        packet_case=packet_case,
        manager_output=manager_output,
    )

    assert evaluation["status"] == "fail"
    assert "websearch_truth_shortcut" in evaluation["failure_families"]
    assert "websearch_candidate_mutated_runtime" in evaluation["failure_families"]
    assert "websearch_candidate_created_item_results" in evaluation["failure_families"]
    assert evaluation["runtime_mutation_attempted"] is True
    assert evaluation["mutation_signal"] == {
        "final_action": "commit",
        "workflow_effect": "food_log_candidate",
        "mutation_intent_candidate": "canonical_write",
    }


def test_websearch_manager_output_diagnostic_flags_truth_surfaces() -> None:
    packet_case = _manager_packet_artifact()["cases"][0]
    manager_output = {
        "manager_action": "final",
        "final_action": "keep_candidate_pending",
        "workflow_effect": "source_candidate_review",
        "target_attachment": {"candidate_id": packet_case["case_id"]},
        "tool_calls": [{"name": "write_ledger"}],
        "packet_ready_anchor": {"canonical_id": "invented_exact_card"},
        "item_results": [],
        "evidence_used": [packet_case["case_id"]],
        "semantic_decision": {"mutation_intent_candidate": "no_mutation"},
    }

    evaluation = evaluate_manager_output_against_websearch_packet(
        packet_case=packet_case,
        manager_output=manager_output,
    )

    assert evaluation["status"] == "fail"
    assert "websearch_truth_shortcut" in evaluation["failure_families"]
    assert "websearch_truth_surface_leak" in evaluation["failure_families"]


def test_websearch_manager_output_diagnostic_flags_invented_evidence_refs() -> None:
    packet_case = _manager_packet_artifact()["cases"][0]
    manager_output = {
        "manager_action": "final",
        "final_action": "keep_candidate_pending",
        "workflow_effect": "source_candidate_review",
        "item_results": [],
        "evidence_used": ["invented_websearch_source"],
        "semantic_decision": {"mutation_intent_candidate": "no_mutation"},
    }

    evaluation = evaluate_manager_output_against_websearch_packet(
        packet_case=packet_case,
        manager_output=manager_output,
    )

    assert evaluation["status"] == "fail"
    assert "invented_websearch_evidence_reference" in evaluation["failure_families"]


def test_websearch_manager_output_diagnostic_rejects_substring_evidence_refs() -> None:
    packet_case = _manager_packet_artifact()["cases"][0]
    manager_output = {
        "manager_action": "final",
        "final_action": "no_commit",
        "workflow_effect": "source_candidate_review",
        "item_results": [],
        "answer_contract": {
            "source_candidate_refs": [f"{packet_case['case_id']} plus invented source and kcal truth"]
        },
        "semantic_decision": {"mutation_intent_candidate": "no_mutation"},
    }

    evaluation = evaluate_manager_output_against_websearch_packet(
        packet_case=packet_case,
        manager_output=manager_output,
    )

    assert evaluation["status"] == "fail"
    assert "invented_websearch_evidence_reference" in evaluation["failure_families"]


def test_websearch_manager_output_diagnostic_requires_packet_evidence_use() -> None:
    packet_case = _manager_packet_artifact()["cases"][0]
    manager_output = {
        "manager_action": "final",
        "final_action": "no_commit",
        "workflow_effect": "source_candidate_review",
        "item_results": [],
        "answer_contract": {"source_candidate_refs": []},
        "semantic_decision": {"mutation_intent_candidate": "no_mutation"},
    }

    evaluation = evaluate_manager_output_against_websearch_packet(
        packet_case=packet_case,
        manager_output=manager_output,
    )

    assert evaluation["status"] == "fail"
    assert "websearch_candidate_not_used" in evaluation["failure_families"]


def test_websearch_manager_output_diagnostic_treats_no_commit_as_non_mutating() -> None:
    packet_case = _manager_packet_artifact()["cases"][0]
    manager_output = {
        "manager_action": "final",
        "final_action": "no_commit",
        "workflow_effect": "no_commit",
        "item_results": [],
        "answer_contract": {"source_candidate_refs": [packet_case["case_id"]]},
        "semantic_decision": {"mutation_intent_candidate": "no_mutation"},
    }

    evaluation = evaluate_manager_output_against_websearch_packet(
        packet_case=packet_case,
        manager_output=manager_output,
    )

    assert evaluation["runtime_mutation_attempted"] is False
    assert "websearch_candidate_mutated_runtime" not in evaluation["failure_families"]


def test_websearch_manager_output_diagnostic_requires_followup_for_related_candidate() -> None:
    packet_artifact = _manager_packet_artifact()
    related = {
        case["case_id"]: case for case in packet_artifact["cases"]
    }["pkt_web_search_milksha_sibling"]
    manager_output = {
        "manager_action": "final",
        "final_action": "ask_followup",
        "workflow_effect": "source_candidate_review",
        "item_results": [],
        "answer_contract": {"source_candidate_refs": [related["case_id"]]},
        "semantic_decision": {"mutation_intent_candidate": "no_mutation"},
    }

    evaluation = evaluate_manager_output_against_websearch_packet(
        packet_case=related,
        manager_output=manager_output,
    )

    assert evaluation["status"] == "pass"

    manager_output["final_action"] = "commit"
    evaluation = evaluate_manager_output_against_websearch_packet(
        packet_case=related,
        manager_output=manager_output,
    )
    assert evaluation["status"] == "fail"
    assert "websearch_ambiguous_candidate_missing_followup" in evaluation["failure_families"]


def test_websearch_manager_output_diagnostic_script_roundtrip(tmp_path: Path) -> None:
    from app.shared.infra.json_artifacts import read_json_artifact
    from scripts.build_accurate_intake_websearch_manager_packet_smoke import (
        main as build_manager_packet_smoke,
    )
    from scripts.build_accurate_intake_websearch_manager_output_diagnostic import main

    packet_output = tmp_path / "websearch_manager_packet.json"
    output = tmp_path / "websearch_manager_output.json"
    assert build_manager_packet_smoke(["--output", str(packet_output)]) == 0

    assert main(["--manager-packet-artifact", str(packet_output), "--output", str(output)]) == 0

    artifact = read_json_artifact(output)
    assert artifact["artifact_type"] == "accurate_intake_websearch_manager_output_diagnostic"
    assert artifact["status"] == "pass"
    assert artifact["summary"]["pass_count"] == 4


def test_websearch_manager_output_diagnostic_has_no_live_search_or_provider_imports() -> None:
    source_paths = [
        Path("app/nutrition/application/websearch_manager_output_diagnostic.py"),
        Path("scripts/build_accurate_intake_websearch_manager_output_diagnostic.py"),
    ]
    forbidden = [
        "BuilderSpaceAdapter",
        "Tavily",
        "requests.",
        "httpx.",
        "run_live",
        "allow_live",
    ]

    for path in source_paths:
        source = path.read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in source
