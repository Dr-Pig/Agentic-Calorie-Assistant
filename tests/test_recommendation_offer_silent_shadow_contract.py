from __future__ import annotations

from app.recommendation.application.offer_silent_shadow_contract import (
    build_recommendation_offer_silent_shadow_contract_artifact,
)


REQUIRED_CASES = [
    "high_quality_prepared_candidate_activation_candidate",
    "uncertain_valid_candidate_offer_only",
    "generic_or_missing_candidate_silent",
    "negative_or_over_budget_candidate_silent",
    "live_search_and_ranking_blocked",
]


def _by_id(artifact: dict[str, object]) -> dict[str, dict[str, object]]:
    return {str(case["case_id"]): case for case in artifact["cases"]}  # type: ignore[index]


def test_offer_silent_contract_is_no_runtime_shadow_only() -> None:
    artifact = build_recommendation_offer_silent_shadow_contract_artifact()

    assert artifact["artifact_type"] == "accurate_intake_recommendation_offer_silent_shadow_contract"
    assert artifact["status"] == "pass"
    assert artifact["owner"] == "app/recommendation"
    assert artifact["consumer"] == "future recommendation/proactive activation slices"
    assert artifact["retirement_trigger"] == "approved recommendation_runtime_activation_plan"
    assert artifact["local_only"] is True
    assert artifact["diagnostic_only"] is True
    assert artifact["shadow_only"] is True
    assert artifact["runtime_connected"] is False
    assert artifact["recommendation_served"] is False
    assert artifact["proactive_sent"] is False
    assert artifact["live_search_used"] is False
    assert artifact["ranking_llm_invoked"] is False
    assert artifact["intake_handoff_created"] is False
    assert artifact["mutation_changed"] is False
    assert [case["case_id"] for case in artifact["cases"]] == REQUIRED_CASES


def test_high_quality_candidate_is_activation_candidate_but_not_served() -> None:
    case = _by_id(build_recommendation_offer_silent_shadow_contract_artifact())[
        "high_quality_prepared_candidate_activation_candidate"
    ]

    assert case["quality_tier"] == "high"
    assert case["quality_gate_passed"] is True
    assert case["proactive_intensity"] == "primary_plus_backup"
    assert case["presentation_posture"] == "activation_candidate"
    assert case["recommendation_served"] is False
    assert case["intake_handoff_created"] is False


def test_uncertain_valid_candidate_is_offer_only() -> None:
    case = _by_id(build_recommendation_offer_silent_shadow_contract_artifact())[
        "uncertain_valid_candidate_offer_only"
    ]

    assert case["quality_tier"] == "medium"
    assert case["quality_gate_passed"] is True
    assert case["proactive_intensity"] == "offer"
    assert case["presentation_posture"] == "low_friction_offer_only"
    assert case["proactive_sent"] is False


def test_generic_missing_negative_or_over_budget_candidates_go_silent() -> None:
    cases = _by_id(build_recommendation_offer_silent_shadow_contract_artifact())

    generic = cases["generic_or_missing_candidate_silent"]
    assert generic["presentation_posture"] == "silent"
    assert "generic_evidence_not_proactive" in generic["disqualifier_flags"]
    assert "missing_kcal_estimate" in generic["secondary_disqualifier_flags"]

    blocked = cases["negative_or_over_budget_candidate_silent"]
    assert blocked["presentation_posture"] == "silent"
    assert "negative_preference" in blocked["disqualifier_flags"]
    assert "budget_mismatch" in blocked["secondary_disqualifier_flags"]


def test_live_search_and_ranking_llm_remain_blocked() -> None:
    case = _by_id(build_recommendation_offer_silent_shadow_contract_artifact())[
        "live_search_and_ranking_blocked"
    ]

    assert case["live_search_used"] is False
    assert case["ranking_llm_invoked"] is False
    assert case["candidate_generation_stage"] == "prepared_candidate_only"
    assert case["serving_stage"] == "not_connected"


def test_offer_silent_validator_rejects_runtime_or_serving_drift() -> None:
    from app.recommendation.application import offer_silent_shadow_contract as module

    artifact = build_recommendation_offer_silent_shadow_contract_artifact()
    cases = list(artifact["cases"])  # type: ignore[index]
    cases[0] = {
        **dict(cases[0]),
        "recommendation_served": True,
        "live_search_used": True,
        "intake_handoff_created": True,
    }

    blockers = module._validate_cases(cases)

    assert "high_quality_prepared_candidate_activation_candidate.recommendation_served" in blockers
    assert "high_quality_prepared_candidate_activation_candidate.live_search_used" in blockers
    assert "high_quality_prepared_candidate_activation_candidate.intake_handoff_created" in blockers
