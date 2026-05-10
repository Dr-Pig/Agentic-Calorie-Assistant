from __future__ import annotations

from tests.test_advanced_shadow_lab_shadow_comparison import _fixture_chain


EXPECTED_CASE_IDS = [
    "F",
    "F2",
    "I",
    "L",
    "M",
    "N",
]
EXPECTED_JOURNEY_NAMES = {
    "F": "same_day_rescue_after_overshoot",
    "F2": "planned_event_rescue_before_large_meal",
    "I": "calibration_proposal_from_body_trend",
    "L": "contextual_recommendation_to_pending_meal_intent",
    "M": "preference_memory_affects_recommendation",
    "N": "proactive_chat_first_no_send_intervention",
}


def test_paired_fixture_cases_cover_standard_surfaces_without_semantic_claims() -> None:
    from app.advanced_shadow_lab.paired_fixture_cases import (
        build_paired_fixture_case_artifacts,
    )

    artifact = build_paired_fixture_case_artifacts(
        fixture_chain_artifact=_fixture_chain(),
    )

    assert artifact["artifact_type"] == "advanced_shadow_paired_fixture_cases"
    assert artifact["status"] == "pass"
    assert artifact["new_report_family_created"] is False
    assert artifact["semantic_truth_owner"] == "source_artifacts_not_pairing_generator"
    assert artifact["claim_boundary"] == "non_claim"
    assert artifact["case_ids"] == EXPECTED_CASE_IDS
    assert [case["case_id"] for case in artifact["baseline_case_artifacts"]] == (
        EXPECTED_CASE_IDS
    )
    assert [case["case_id"] for case in artifact["advanced_case_artifacts"]] == (
        EXPECTED_CASE_IDS
    )
    for case in [*artifact["baseline_case_artifacts"], *artifact["advanced_case_artifacts"]]:
        assert case["status"] == "pass"
        assert case["journey_id"] == case["case_id"]
        assert case["journey_name"] == EXPECTED_JOURNEY_NAMES[case["journey_id"]]
        assert case["source_artifact_refs"]
        assert case["runtime_connected"] is False
        assert case["delivery_attempted"] is False
        assert case["recommendation_served"] is False
        assert case["rescue_committed"] is False
        assert case["proposal_committed"] is False
        assert case["mutation_changed"] is False
        assert case["user_facing_behavior_changed"] is False
        assert case["product_readiness_claimed"] is False
        assert case["semantic_decision_inferred_by_runner"] is False


def test_paired_fixture_cases_cover_all_mapped_ux_journeys_in_comparison() -> None:
    from app.advanced_shadow_lab.paired_fixture_cases import (
        build_paired_fixture_case_artifacts,
    )
    from app.advanced_shadow_lab.shadow_comparison import (
        build_advanced_shadow_comparison_artifact,
    )
    from tests.test_advanced_shadow_lab_shadow_comparison import (
        _dogfood_replay,
        _live_diagnostic,
        _proactive_live_diagnostic,
        _rescue_live_diagnostic,
    )

    pairs = build_paired_fixture_case_artifacts(fixture_chain_artifact=_fixture_chain())
    comparison = build_advanced_shadow_comparison_artifact(
        fixture_chain_artifact=_fixture_chain(),
        dogfood_replay_artifact=_dogfood_replay(),
        recommendation_copy_live_diagnostic_artifact=_live_diagnostic(),
        rescue_copy_live_diagnostic_artifact=_rescue_live_diagnostic(),
        proactive_copy_live_diagnostic_artifact=_proactive_live_diagnostic(),
        baseline_case_artifacts=pairs["baseline_case_artifacts"],
        advanced_case_artifacts=pairs["advanced_case_artifacts"],
    )

    assert comparison["status"] == "pass"
    assert comparison["pairing_summary"] == {
        "status": "pairable",
        "baseline_case_count": 6,
        "advanced_case_count": 6,
        "paired_case_count": 6,
        "schema_gaps": [],
        "activation_violations": [],
    }
    assert [row["case_id"] for row in comparison["paired_case_rows"]] == (
        EXPECTED_CASE_IDS
    )


def test_paired_fixture_cases_block_activation_drift_before_pairing() -> None:
    from app.advanced_shadow_lab.paired_fixture_cases import (
        build_paired_fixture_case_artifacts,
    )

    fixture = _fixture_chain()
    fixture["delivery_attempted"] = True

    artifact = build_paired_fixture_case_artifacts(fixture_chain_artifact=fixture)

    assert artifact["status"] == "blocked"
    assert artifact["baseline_case_artifacts"] == []
    assert artifact["advanced_case_artifacts"] == []
    assert artifact["blockers"] == [
        "fixture_chain.delivery_attempted",
    ]
