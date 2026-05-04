from __future__ import annotations

from pathlib import Path

from app.nutrition.application.websearch_manager_packet_smoke import (
    build_websearch_manager_packet_projection,
    is_compact_websearch_manager_packet,
)
from app.nutrition.application.websearch_candidate_packet_smoke import (
    build_websearch_candidate_packet_smoke,
)
from app.nutrition.application.tool_evidence_result import build_tool_evidence_result


def _tool_evidence_artifact() -> dict:
    packet_artifact = build_websearch_candidate_packet_smoke()
    packets = tuple(case["websearch_candidate_packet"] for case in packet_artifact["cases"])
    tool_result = build_tool_evidence_result(
        tool_name="search_official_nutrition",
        tool_call_id="tool-call-websearch-manager-packet",
        evidence_packets=packets,
        trace_context={
            "packet_artifact_type": packet_artifact["artifact_type"],
            "packet_claim_scope": packet_artifact["claim_scope"],
            "live_websearch_used": False,
        },
    )
    return {
        "artifact_type": "accurate_intake_websearch_tool_evidence_result_smoke",
        "tool_evidence_result": tool_result,
    }


def test_websearch_manager_packet_projection_stays_candidate_only() -> None:
    artifact = build_websearch_manager_packet_projection(tool_evidence_artifact=_tool_evidence_artifact())

    assert artifact["artifact_type"] == "accurate_intake_websearch_manager_packet_projection"
    assert artifact["claim_scope"] == "deterministic_websearch_manager_packet_projection"
    assert artifact["runtime_truth_changed"] is False
    assert artifact["live_websearch_used"] is False
    assert artifact["live_provider_used"] is False
    assert artifact["websearch_runtime_truth_allowed"] is False
    assert artifact["summary"]["case_count"] == 4
    assert artifact["summary"]["candidate_only_count"] == 4
    assert artifact["summary"]["runtime_truth_allowed_count"] == 0

    for case in artifact["cases"]:
        manager_packet = case["manager_evidence_packet"]
        assert is_compact_websearch_manager_packet(manager_packet)
        assert case["compact_manager_packet"] is True
        assert case["candidate_boundary"] == {
            "candidate_only": True,
            "runtime_truth_allowed": False,
            "snippet_truth_allowed": False,
            "requires_later_promotion_path": True,
        }
        assert manager_packet["truth_selection_forbidden"] is True
        assert manager_packet["runtime_mutation_allowed"] is False
        assert manager_packet["websearch_runtime_truth_allowed"] is False
        assert "nutrition_truth_selection" in manager_packet["manager_must_not_use_for"]


def test_websearch_manager_packet_projection_classifies_exact_and_related_candidates() -> None:
    artifact = build_websearch_manager_packet_projection(tool_evidence_artifact=_tool_evidence_artifact())
    cases = {case["case_id"]: case for case in artifact["cases"]}

    exact = cases["pkt_web_search_milksha_exact"]
    assert exact["manager_expected_behavior"] == "candidate_review_or_later_exact_card_promotion_path"
    assert exact["manager_evidence_packet"]["ambiguity_reason"] is None

    sibling = cases["pkt_web_search_milksha_sibling"]
    assert sibling["manager_expected_behavior"] == "ask_followup_or_keep_candidate_pending"
    assert sibling["manager_evidence_packet"]["ambiguity_reason"] == "same_brand_nearby_variant"
    assert "confirm_exact_menu_item_or_variant" in sibling["manager_evidence_packet"]["followup_hints"]


def test_websearch_manager_packet_projection_excludes_truth_and_backend_leakage() -> None:
    artifact = build_websearch_manager_packet_projection(tool_evidence_artifact=_tool_evidence_artifact())
    forbidden = (
        "adapter_kind",
        "external_search",
        "final_kcal",
        "kcal_range",
        "ledger_mutation_result",
        "storage_backend",
        "supabase",
    )

    for case in artifact["cases"]:
        manager_packet_text = str(case["manager_evidence_packet"])
        assert case["manager_evidence_packet"]["websearch_runtime_truth_allowed"] is False
        assert "websearch_candidate_packet" not in case
        assert "tool_evidence_result" not in case
        for token in forbidden:
            assert token not in manager_packet_text
            assert token not in str(case)
        assert "snippet" not in case["manager_evidence_packet"]
        assert "tavily_score" not in case["manager_evidence_packet"]
        assert "raw_ref" not in str(case)


def test_websearch_manager_packet_smoke_script_roundtrip(tmp_path: Path) -> None:
    from app.shared.infra.json_artifacts import read_json_artifact
    from scripts.build_accurate_intake_websearch_tool_evidence_result_smoke import (
        main as build_tool_evidence_result,
    )
    from scripts.build_accurate_intake_websearch_manager_packet_smoke import main

    tool_output = tmp_path / "websearch_tool_evidence_result.json"
    output = tmp_path / "websearch_manager_packet.json"
    assert build_tool_evidence_result(["--output", str(tool_output)]) == 0

    assert main(["--tool-evidence-result", str(tool_output), "--output", str(output)]) == 0

    artifact = read_json_artifact(output)
    assert artifact["artifact_type"] == "accurate_intake_websearch_manager_packet_projection"
    assert artifact["summary"]["case_count"] == 4
    assert artifact["summary"]["candidate_only_count"] == 4


def test_websearch_manager_packet_smoke_has_no_live_search_or_provider_imports() -> None:
    source_paths = [
        Path("app/nutrition/application/websearch_manager_packet_smoke.py"),
        Path("scripts/build_accurate_intake_websearch_manager_packet_smoke.py"),
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
