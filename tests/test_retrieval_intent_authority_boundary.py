from __future__ import annotations

from app.nutrition.application.retrieval_intent import (
    RAW_TEXT_RETRIEVAL_INTENT_POLICY,
    build_retrieval_intent,
)


def test_raw_text_retrieval_intent_is_explicitly_diagnostic_only() -> None:
    intent = build_retrieval_intent("我喝了珍珠奶茶")

    assert intent.retrieval_goal == "generic_anchor_lookup"
    assert RAW_TEXT_RETRIEVAL_INTENT_POLICY == {
        "semantic_authority_source": "deterministic_raw_text_hint_only",
        "user_intent_owner": "manager_llm",
        "workflow_owner": "manager_llm",
        "mutation_owner": "runtime_guard",
        "allowed_uses": [
            "retrieval_candidate_recall",
            "source_selection_hint",
            "diagnostic_fixture_seed",
        ],
        "forbidden_uses": [
            "user_intent_classification",
            "workflow_effect_decision",
            "final_action_selection",
            "mutation_authority",
        ],
    }
