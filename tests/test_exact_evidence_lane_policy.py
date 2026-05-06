from __future__ import annotations

from pathlib import Path

from app.nutrition.application.exact_evidence_lane_policy import (
    build_exact_evidence_lane_policy_artifact,
)


def _case_by_id(artifact: dict, case_id: str) -> dict:
    return {case["case_id"]: case for case in artifact["cases"]}[case_id]


def test_exact_evidence_lane_policy_prefers_local_exact_seed_before_websearch() -> None:
    artifact = build_exact_evidence_lane_policy_artifact()
    cases = {case["case_id"]: case for case in artifact["cases"]}

    assert artifact["artifact_type"] == "accurate_intake_exact_evidence_lane_policy_v1"
    assert artifact["classification"] == "offline_exact_lane_policy_only"
    assert artifact["runtime_truth_changed"] is False
    assert artifact["live_websearch_used"] is False
    assert artifact["live_provider_used"] is False

    local = cases["local_exact_seed_preferred"]
    assert local["lane_decision"]["selected_lane"] == "local_exact_seed_support_only"
    assert local["lane_decision"]["websearch_required"] is False
    assert local["local_exact"]["defer_reason"] is None
    assert local["local_exact"]["candidate_count"] >= 1

    web = cases["websearch_candidate_review_fallback"]
    assert web["lane_decision"]["selected_lane"] == "websearch_candidate_review"
    assert web["lane_decision"]["websearch_required"] is True
    assert web["lane_decision"]["evidence_signal"] == "exact_card_candidate_review_available"
    assert web["local_exact"]["defer_reason"] == "no_exact_item_match"
    assert web["websearch_pipeline"]["extract_candidate_allowed_count"] == 1
    assert web["exact_card_staging"]["candidate_count"] == 1

    convenience = cases["convenience_store_rice_ball_review_priority"]
    assert convenience["lane_decision"]["selected_lane"] == "websearch_candidate_review"
    assert convenience["exact_card_staging"]["candidate_count"] == 1
    assert convenience["exact_card_staging"]["candidates"][0]["source_policy"]["source_class"] == (
        "official_brand_or_chain_page"
    )

    chain_restaurant = cases["chain_restaurant_menu_review_priority"]
    assert chain_restaurant["lane_decision"]["selected_lane"] == "websearch_candidate_review"
    assert chain_restaurant["exact_card_staging"]["candidate_count"] == 1
    assert chain_restaurant["exact_card_staging"]["candidates"][0]["source_policy"][
        "serving_basis_candidate"
    ] == "per_bowl"

    no_exact = cases["no_exact_evidence_available"]
    assert no_exact["lane_decision"]["selected_lane"] == "no_exact_evidence"
    assert no_exact["lane_decision"]["evidence_signal"] == "no_exact_evidence_available"
    assert no_exact["websearch_pipeline"]["extract_candidate_allowed_count"] == 0
    assert no_exact["exact_card_staging"]["candidate_count"] == 0

    same_brand_wrong_flavor = cases["same_brand_wrong_flavor_no_exact_evidence"]
    assert same_brand_wrong_flavor["lane_decision"]["selected_lane"] == "no_exact_evidence"
    assert same_brand_wrong_flavor["websearch_pipeline"]["extract_candidate_allowed_count"] == 0
    assert same_brand_wrong_flavor["exact_card_staging"]["candidate_count"] == 0

    size_unknown = cases["size_unknown_requires_followup_no_exact_evidence"]
    assert size_unknown["lane_decision"]["selected_lane"] == "no_exact_evidence"
    assert size_unknown["websearch_pipeline"]["extract_candidate_allowed_count"] == 0
    assert size_unknown["exact_card_staging"]["candidate_count"] == 0

    wrong_country = cases["wrong_country_menu_no_exact_evidence"]
    assert wrong_country["lane_decision"]["selected_lane"] == "no_exact_evidence"
    assert wrong_country["websearch_pipeline"]["extract_candidate_allowed_count"] == 0
    assert wrong_country["exact_card_staging"]["candidate_count"] == 0

    serving_not_listed = cases["serving_size_not_listed_no_exact_evidence"]
    assert serving_not_listed["lane_decision"]["selected_lane"] == "no_exact_evidence"
    assert serving_not_listed["websearch_pipeline"]["extract_candidate_allowed_count"] == 0
    assert serving_not_listed["exact_card_staging"]["candidate_count"] == 0

    wrong_brand = cases["wrong_brand_official_no_exact_evidence"]
    assert wrong_brand["lane_decision"]["selected_lane"] == "no_exact_evidence"
    assert wrong_brand["websearch_pipeline"]["extract_candidate_allowed_count"] == 0
    assert wrong_brand["exact_card_staging"]["candidate_count"] == 0


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
        for candidate in case["exact_card_staging"]["candidates"]:
            assert candidate["evidence_role"] == "exact_card_candidate"
            assert candidate["promotion_status"] == "review_candidate"
            assert candidate["promotion_allowed"] is False
            assert candidate["runtime_truth_allowed"] is False
            assert candidate["packet_ready_truth_allowed"] is False
            assert candidate["exact_card_created"] is False
            assert candidate["approval_required_before_runtime_truth"] is True


def test_exact_evidence_lane_builds_websearch_exact_card_staging_candidate() -> None:
    artifact = build_exact_evidence_lane_policy_artifact()
    web = _case_by_id(artifact, "websearch_candidate_review_fallback")
    candidate = web["exact_card_staging"]["candidates"][0]

    assert candidate["canonical_name"] == "Milksha pearl black tea latte"
    assert candidate["source_url"] == "https://milksha.example/menu/pearl-black-tea-latte"
    assert candidate["source_policy"]["license_status"] == "public_menu_page"
    assert candidate["source_policy"]["robots_status"] == "allowed"
    assert candidate["source_policy"]["identity_confidence"] == "high"
    assert candidate["source_policy"]["serving_basis_candidate"] == "per_cup"
    assert candidate["source_policy"]["nutrition_fields_present"] == ["kcal"]
    assert candidate["approval_metadata"] == {
        "approval_mode": "none",
        "approval_scope": "review_candidate_only",
        "policy_version": "exact_evidence_lane_policy_v1",
        "runtime_truth_allowed": False,
    }
    assert "kcal_point" not in candidate
    assert "kcal_range" not in candidate

    convenience = _case_by_id(artifact, "convenience_store_rice_ball_review_priority")
    convenience_candidate = convenience["exact_card_staging"]["candidates"][0]
    assert convenience_candidate["canonical_name"] == "7-Eleven salmon rice ball"
    assert convenience_candidate["source_policy"]["serving_basis_candidate"] == "per_piece"

    chain_restaurant = _case_by_id(artifact, "chain_restaurant_menu_review_priority")
    chain_candidate = chain_restaurant["exact_card_staging"]["candidates"][0]
    assert chain_candidate["canonical_name"] == "Matsuya gyudon large"
    assert chain_candidate["source_policy"]["serving_basis_candidate"] == "per_bowl"


def test_exact_evidence_lane_uses_evidence_signals_not_manager_oracles() -> None:
    artifact = build_exact_evidence_lane_policy_artifact()

    for case in artifact["cases"]:
        assert "manager_expected_behavior" not in case["lane_decision"]
        assert "evidence_signal" in case["lane_decision"]
    assert not _contains_key(artifact, "manager_signal")
    assert not _contains_key(artifact, "manager_expected_behavior")
    assert "candidate_review_no_commit" not in str(artifact)
    assert "ask_followup" not in str(artifact)
    assert "source_not_sufficient" not in str(artifact)


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


def _contains_key(value: object, key: str) -> bool:
    if isinstance(value, dict):
        return key in value or any(_contains_key(child, key) for child in value.values())
    if isinstance(value, list):
        return any(_contains_key(item, key) for item in value)
    return False
