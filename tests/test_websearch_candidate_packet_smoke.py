from __future__ import annotations

from pathlib import Path

from app.nutrition.application.websearch_candidate_packet_smoke import (
    WEBSEARCH_TRUTH_FIELD_DENYLIST,
    build_websearch_candidate_packet_smoke,
    derive_websearch_candidate_boundary,
)


def _case_by_id(artifact: dict, case_id: str) -> dict:
    return {case["case_id"]: case for case in artifact["cases"]}[case_id]


def test_websearch_candidate_packet_smoke_is_candidate_only_even_for_exact_support() -> None:
    artifact = build_websearch_candidate_packet_smoke()

    assert artifact["artifact_type"] == "accurate_intake_websearch_candidate_packet_smoke"
    assert artifact["claim_scope"] == "deterministic_websearch_candidate_packet_boundary"
    assert artifact["live_websearch_used"] is False
    assert artifact["live_provider_used"] is False
    assert artifact["runtime_truth_changed"] is False
    assert artifact["websearch_runtime_truth_allowed"] is False
    assert artifact["summary"]["case_count"] == 4

    exact = _case_by_id(artifact, "official_exact_candidate")
    packet = exact["websearch_candidate_packet"]
    assert packet["packet_type"] == "SearchCandidatePacket"
    assert packet["truth_level"] == "candidate"
    assert packet["source_type"] == "web_search"
    assert WEBSEARCH_TRUTH_FIELD_DENYLIST.isdisjoint(packet)
    assert packet["match_type"] == "exact"
    assert exact["hard_recheck"]["supports_exact_claim"] is True
    assert exact["candidate_boundary"] == {
        "candidate_only": True,
        "runtime_truth_allowed": False,
        "snippet_truth_allowed": False,
        "requires_later_promotion_path": True,
        "truth_field_violations": [],
    }
    assert all(case["candidate_boundary"]["runtime_truth_allowed"] is False for case in artifact["cases"])
    assert all(case["candidate_boundary"]["snippet_truth_allowed"] is False for case in artifact["cases"])


def test_websearch_candidate_packet_smoke_reports_rejected_risks_without_promotion() -> None:
    artifact = build_websearch_candidate_packet_smoke()

    sibling = _case_by_id(artifact, "same_brand_sibling_candidate")
    assert sibling["websearch_candidate_packet"]["match_type"] == "related"
    assert "sibling_variant" in sibling["hard_recheck"]["hard_recheck_risks"]
    assert sibling["candidate_boundary"]["runtime_truth_allowed"] is False

    third_party = _case_by_id(artifact, "third_party_weak_candidate")
    assert third_party["websearch_candidate_packet"]["source_quality_label"] == "third_party"
    assert third_party["hard_recheck"]["supports_exact_claim"] is False
    assert third_party["candidate_boundary"]["runtime_truth_allowed"] is False


def test_websearch_candidate_packet_smoke_boundary_is_derived_from_packet_fields() -> None:
    artifact = build_websearch_candidate_packet_smoke()
    exact = _case_by_id(artifact, "official_exact_candidate")

    packet = dict(exact["websearch_candidate_packet"])
    packet["truth_level"] = "final"
    boundary = derive_websearch_candidate_boundary(packet)
    assert boundary["candidate_only"] is False

    packet = dict(exact["websearch_candidate_packet"])
    packet["final_truth"] = {"kcal": 400}
    boundary = derive_websearch_candidate_boundary(packet)
    assert boundary["candidate_only"] is False
    assert "final_truth" in boundary["truth_field_violations"]


def test_websearch_candidate_packet_smoke_script_roundtrip(tmp_path: Path) -> None:
    from app.shared.infra.json_artifacts import read_json_artifact
    from scripts.build_accurate_intake_websearch_candidate_packet_smoke import main

    output = tmp_path / "websearch_candidate_packet_smoke.json"

    assert main(["--output", str(output)]) == 0

    artifact = read_json_artifact(output)
    assert artifact["artifact_type"] == "accurate_intake_websearch_candidate_packet_smoke"
    assert artifact["summary"]["candidate_only_count"] == 4
    assert artifact["summary"]["runtime_truth_allowed_count"] == 0


def test_websearch_candidate_packet_smoke_has_no_live_search_or_provider_imports() -> None:
    source_paths = [
        Path("app/nutrition/application/websearch_candidate_packet_smoke.py"),
        Path("scripts/build_accurate_intake_websearch_candidate_packet_smoke.py"),
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
