from __future__ import annotations

from tests.test_advanced_shadow_lab_shadow_comparison import _fixture_chain


EXPECTED_CASE_IDS = [
    "recommendation_prompt_fixture_case",
    "rescue_nudge_fixture_case",
    "proactive_no_send_review_fixture_case",
    "chat_ux_packet_fixture_case",
]


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
        assert case["runtime_connected"] is False
        assert case["delivery_attempted"] is False
        assert case["recommendation_served"] is False
        assert case["rescue_committed"] is False
        assert case["proposal_committed"] is False
        assert case["mutation_changed"] is False
        assert case["user_facing_behavior_changed"] is False
        assert case["product_readiness_claimed"] is False
        assert case["semantic_decision_inferred_by_runner"] is False


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
