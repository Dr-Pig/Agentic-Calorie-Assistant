from __future__ import annotations

from pathlib import Path

from app.nutrition.application.exact_evidence_lane_policy import (
    build_exact_evidence_lane_policy_artifact,
)


def _case_by_id(artifact: dict, case_id: str) -> dict:
    return {case["case_id"]: case for case in artifact["cases"]}[case_id]


def test_exact_evidence_lane_policy_prefers_local_exact_seed_before_websearch() -> None:
    artifact = build_exact_evidence_lane_policy_artifact()

    assert artifact["artifact_type"] == "accurate_intake_exact_evidence_lane_policy_v1"
    assert artifact["classification"] == "offline_exact_lane_policy_only"
    assert artifact["runtime_truth_changed"] is False
    assert artifact["live_websearch_used"] is False
    assert artifact["live_provider_used"] is False

    local = _case_by_id(artifact, "local_exact_seed_preferred")
    assert local["lane_decision"]["selected_lane"] == "local_exact_seed_support_only"
    assert local["lane_decision"]["websearch_required"] is False
    assert local["local_exact"]["defer_reason"] is None
    assert local["local_exact"]["candidate_count"] >= 1

    web = _case_by_id(artifact, "websearch_candidate_review_fallback")
    assert web["lane_decision"]["selected_lane"] == "websearch_candidate_review"
    assert web["lane_decision"]["websearch_required"] is True
    assert web["local_exact"]["defer_reason"] == "no_exact_item_match"
    assert web["websearch_pipeline"]["extract_candidate_allowed_count"] == 1

    no_exact = _case_by_id(artifact, "no_exact_evidence_available")
    assert no_exact["lane_decision"]["selected_lane"] == "no_exact_evidence"
    assert no_exact["lane_decision"]["manager_expected_behavior"] == "ask_followup_or_generic_path"
    assert no_exact["websearch_pipeline"]["extract_candidate_allowed_count"] == 0


def test_exact_evidence_lane_policy_keeps_every_lane_support_only() -> None:
    artifact = build_exact_evidence_lane_policy_artifact()

    for case in artifact["cases"]:
        assert case["runtime_truth_allowed"] is False
        assert case["packet_ready_truth_allowed"] is False
        assert case["runtime_mutation_allowed"] is False
        assert case["live_websearch_used"] is False
        for candidate in case["local_exact"]["candidates"]:
            assert candidate["support_only"] is True
        for classification in case["websearch_pipeline"]["candidate_classifications"]:
            assert classification["runtime_truth_allowed"] is False
            assert classification["packet_ready_truth_allowed"] is False


def test_exact_evidence_lane_policy_script_roundtrip(tmp_path: Path) -> None:
    from app.shared.infra.json_artifacts import read_json_artifact
    from scripts.build_accurate_intake_exact_evidence_lane_policy import main

    output = tmp_path / "exact_evidence_lane_policy.json"

    assert main(["--output", str(output)]) == 0

    artifact = read_json_artifact(output)
    assert artifact["artifact_type"] == "accurate_intake_exact_evidence_lane_policy_v1"
    assert artifact["summary"]["local_exact_preferred_count"] >= 1


def test_exact_evidence_lane_policy_has_no_live_or_shared_contract_imports() -> None:
    source_paths = [
        Path("app/nutrition/application/exact_evidence_lane_policy.py"),
        Path("scripts/build_accurate_intake_exact_evidence_lane_policy.py"),
    ]
    forbidden = [
        "BuilderSpaceAdapter",
        "Tavily",
        "allow_live",
        "run_live",
        "ManagerContextPacket",
        "NutritionEvidenceStorePort",
    ]

    for path in source_paths:
        source = path.read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in source
