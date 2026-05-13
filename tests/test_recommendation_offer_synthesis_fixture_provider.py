from __future__ import annotations

from app.advanced_shadow_lab.product_lab_fixture_inputs import (
    build_product_lab_fixture_inputs,
)
from app.advanced_shadow_lab.product_lab_memory import (
    empty_product_lab_memory_context_pack,
)
from app.advanced_shadow_lab.product_lab_recommendation_candidates import (
    build_candidate_retrieval_guard_scoring,
)
from app.recommendation.application.offer_synthesis_fixture_provider import (
    FixtureRecommendationOfferSynthesisProvider,
)


def test_offer_synthesis_fixture_provider_owns_llm_offer_node_contract() -> None:
    retrieval = _retrieval()

    offer = FixtureRecommendationOfferSynthesisProvider(
        model_profile="strict_reasoner_or_response_writer_model"
    ).synthesize(retrieval_guard_scoring=retrieval)

    assert offer["node"] == "offer_synthesis"
    assert offer["owner"] == "llm_fixture_provider"
    assert offer["model_profile"] == "strict_reasoner_or_response_writer_model"
    assert offer["input_contract"] == {
        "allowed_pool_trace_required": True,
        "may_retrieve_candidates": False,
        "may_apply_hard_blockers": False,
        "may_mutate_canonical_truth": False,
        "raw_transcript_allowed": False,
    }
    assert offer["selected_primary"]["candidate_id"] == "golden-1"
    assert offer["ranking_result"]["selected_primary"] == "golden-1"
    assert offer["recommendation_response_result"]["response_packet_owner"] == (
        "offer_synthesis"
    )
    assert offer["ux_packet"]["chat_first"] is True
    assert offer["blockers"] == []


def test_offer_synthesis_fixture_provider_omits_when_no_qualified_candidate() -> None:
    offer = FixtureRecommendationOfferSynthesisProvider(
        model_profile="strict_reasoner_or_response_writer_model"
    ).synthesize(
        retrieval_guard_scoring={
            "qualified_candidates": [],
            "allowed_pool_trace": {
                "artifact_type": "recommendation_allowed_pool_trace",
                "raw_transcript_included": False,
            },
        }
    )

    assert offer["status"] == "omitted"
    assert offer["offer_model_invoked"] is False
    assert offer["no_qualified_candidate"] is True
    assert offer["input_contract"]["allowed_pool_trace_required"] is True
    assert offer["blockers"] == []


def test_product_lab_provider_delegates_offer_synthesis_to_application_provider() -> None:
    from app.advanced_shadow_lab.product_lab_recommendation_provider import (
        FixtureProductLabRecommendationProvider,
    )

    offer = FixtureProductLabRecommendationProvider().synthesize_offer(
        retrieval_guard_scoring=_retrieval()
    )

    assert offer["provider_module"] == (
        "app.recommendation.application.offer_synthesis_fixture_provider"
    )
    assert offer["input_contract"]["may_apply_hard_blockers"] is False


def test_recommendation_train_records_pr10_completion_and_next_active_slice() -> None:
    import yaml

    with open(
        "docs/quality/advanced_product_lab_recommendation_pr_train.yaml",
        encoding="utf-8-sig",
    ) as handle:
        plan = yaml.safe_load(handle)

    assert plan["dynamic_remaining_pr_count"] <= 14
    assert plan["last_completed_pr_number"] >= 10
    assert plan["active_pr_number"] is None or plan["active_pr_number"] >= 11
    assert {
        "pr_number": 10,
        "pull_request": "local_logical_slice",
        "merge_commit": "working_branch_uncommitted",
        "result": "recommendation_offer_synthesis_fixture_provider_completed_locally",
    } in plan["last_merge_evidence"]["completed_prs"]


def _retrieval() -> dict[str, object]:
    return build_candidate_retrieval_guard_scoring(
        planning={
            "candidate_spec": {
                "budget_posture": {"remaining_kcal": 700, "max_candidate_kcal": 700},
                "pre_meal_planning": {},
                "swap_suggestion": {},
            }
        },
        fixture_inputs=build_product_lab_fixture_inputs(),
        memory_context_pack=empty_product_lab_memory_context_pack(
            session_id="rec-session",
            turn_id="t10",
        ),
    )
