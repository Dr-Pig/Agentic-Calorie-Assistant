from __future__ import annotations

from pathlib import Path


REGISTER = Path("docs/specs/WAVE_1_PHASE_B2_SEMANTIC_DECISION_REGISTER.md")


def test_b2_semantic_register_formalizes_locked_local_case_law() -> None:
    text = REGISTER.read_text(encoding="utf-8-sig")

    required_markers = (
        "homemade_food_minimum_estimability",
        "taiwan_b2_case_law_narrow_set",
        "exact_item_cards_local_diagnostic_seed_only",
        "tavily_web_candidate_evidence_only",
        "model_policy_single_profile_stability_only",
        "MS7 pearl milk tea old draft expectation is superseded",
    )
    for marker in required_markers:
        assert marker in text


def test_b2_semantic_register_does_not_promote_later_wave_semantics() -> None:
    text = REGISTER.read_text(encoding="utf-8-sig")

    forbidden_markers = (
        "rescue proposal",
        "memory write",
        "proactive nudge",
        "production exact DB accuracy",
        "shadow ready",
    )
    for marker in forbidden_markers:
        assert marker not in text
