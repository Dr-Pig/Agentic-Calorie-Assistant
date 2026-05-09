from __future__ import annotations

from tests.long_term_context_shadow_fixture import _fixture_payload


def _review_surface_fixture() -> dict:
    fixture = _fixture_payload()
    fixture["review_actions"] = [
        {
            "action_id": "accept-golden-order",
            "target_candidate_ids": ["golden-order-morning-bar-oatmeal-latte"],
            "action_type": "accept_candidate",
            "actor": "fixture_human_reviewer",
            "rationale": "Useful repeat order for recommendation shadow tests.",
        },
        {
            "action_id": "correct-golden-order",
            "target_candidate_ids": ["golden-order-morning-bar-oatmeal-latte"],
            "action_type": "correct_candidate",
            "actor": "fixture_human_reviewer",
            "rationale": "Correction from review feedback.",
            "corrected_memory_text": (
                "User often chooses Morning Bar oatmeal; latte should be optional."
            ),
        },
        {
            "action_id": "accept-negative-preference",
            "target_candidate_ids": ["negative-preference-ingredient-cilantro"],
            "action_type": "accept_candidate",
            "actor": "fixture_human_reviewer",
            "rationale": "Explicit dislike is useful for recommendation suppression.",
        },
        {
            "action_id": "suppress-style-pattern",
            "target_candidate_ids": ["app-usage-style-pattern"],
            "action_type": "suppress_candidate",
            "actor": "fixture_human_reviewer",
            "rationale": "Do not let thin app-usage evidence shape context packs.",
        },
        {
            "action_id": "delete-bias-pattern",
            "target_candidate_ids": ["intake-estimation-bias-likely-underestimate"],
            "action_type": "delete_candidate",
            "actor": "fixture_human_reviewer",
            "rationale": "Reviewer requested lab deletion after poor attribution.",
        },
        {
            "action_id": "expire-temporary-preference",
            "target_candidate_ids": ["temporary-preference-lower-oil-dinner"],
            "action_type": "expire_candidate",
            "actor": "fixture_human_reviewer",
            "rationale": "Temporary dinner constraint passed its validity window.",
        },
    ]
    return fixture


def test_review_correction_surface_groups_state_and_chat_commands_without_activation() -> None:
    from app.memory.application.long_term_context_shadow_lab import (
        build_shadow_lab_artifacts,
    )

    artifact = build_shadow_lab_artifacts(_review_surface_fixture())[
        "memory_lab_review_loop_state"
    ]
    surface = artifact["lab_review_correction_surface"]

    assert surface["surface_type"] == "chat_first_memory_review_correction_surface"
    assert surface["source_artifact_type"] == "memory_lab_review_loop_state"
    assert surface["primary_surface"] == "chat"
    assert surface["runtime_route_mounted"] is False
    assert surface["api_route_mounted"] is False
    assert surface["product_settings_surface_added"] is False
    assert surface["runtime_effect_allowed"] is False
    assert surface["durable_memory_written"] is False
    assert surface["manager_context_injection_allowed"] is False
    assert surface["truth_owner"] == "human_reviewer"
    assert surface["deterministic_semantic_inference_allowed"] is False
    assert surface["summary"]["active_record_count"] == 2
    assert surface["summary"]["pending_candidate_count"] > 0

    groups = surface["review_state_groups"]
    assert [record["source_candidate_id"] for record in groups["active"]] == [
        "golden-order-morning-bar-oatmeal-latte",
        "negative-preference-ingredient-cilantro",
    ]
    assert groups["active"][0]["record_state"] == "corrected_shadow"
    assert groups["suppressed"][0]["source_candidate_id"] == "app-usage-style-pattern"
    assert groups["deleted"][0]["source_candidate_id"] == (
        "intake-estimation-bias-likely-underestimate"
    )
    assert groups["deleted"][0]["memory_text"] is None
    assert groups["expired"][0]["source_candidate_id"] == (
        "temporary-preference-lower-oil-dinner"
    )

    pending_ids = {
        candidate["candidate_id"] for candidate in surface["pending_candidate_cards"]
    }
    assert "golden-order-morning-bar-oatmeal-latte" not in pending_ids
    assert "app-usage-style-pattern" not in pending_ids

    command_types = {
        command["action_type"] for command in surface["available_chat_commands"]
    }
    assert {
        "accept_candidate",
        "reject_candidate",
        "correct_candidate",
        "suppress_candidate",
        "delete_candidate",
        "expire_candidate",
    }.issubset(command_types)
    assert all(
        command["creates_runtime_effect"] is False
        and command["durable_memory_write_allowed"] is False
        and command["manager_context_injection_allowed"] is False
        for command in surface["available_chat_commands"]
    )

    blocked = {
        command["command_id"]: command for command in surface["blocked_runtime_commands"]
    }
    assert blocked["promote_to_runtime_memory"]["blocked"] is True
    assert blocked["inject_manager_context"]["blocked"] is True
    assert blocked["mount_memory_settings_route"]["blocked"] is True


def test_review_correction_surface_does_not_offer_partial_state_when_blocked() -> None:
    from app.memory.application.long_term_context_shadow_lab import (
        build_shadow_lab_artifacts,
    )

    fixture = _fixture_payload()
    fixture["review_actions"] = [
        {
            "action_id": "bad-runtime-promotion",
            "target_candidate_ids": ["negative-preference-ingredient-cilantro"],
            "action_type": "promote_to_runtime_memory",
            "actor": "fixture_human_reviewer",
            "rationale": "Runtime promotion is not a lab review action.",
        }
    ]

    artifact = build_shadow_lab_artifacts(fixture)["memory_lab_review_loop_state"]
    surface = artifact["lab_review_correction_surface"]

    assert artifact["status"] == "blocked"
    assert surface["status"] == "blocked"
    assert surface["blockers"] == [
        "bad-runtime-promotion.unsupported_action_type:promote_to_runtime_memory"
    ]
    assert surface["review_state_groups"] == {
        "active": [],
        "suppressed": [],
        "deleted": [],
        "expired": [],
        "rejected": [],
    }
    assert surface["available_chat_commands"] == []
    assert surface["runtime_effect_allowed"] is False
    assert surface["durable_memory_written"] is False
