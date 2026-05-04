from __future__ import annotations

from tests.long_term_context_shadow_fixture import _fixture_payload


def test_menu_highlight_shadow_eval_uses_memory_without_serving_recommendation() -> (
    None
):
    from app.memory.application.long_term_context_shadow_lab import (
        build_shadow_lab_artifacts,
    )

    artifact = build_shadow_lab_artifacts(_fixture_payload())[
        "menu_highlight_shadow_eval"
    ]

    assert artifact["artifact_type"] == "menu_highlight_shadow_eval"
    assert artifact["active_menu_scan_runtime_used"] is False
    assert artifact["ui_highlight_rendered"] is False
    assert artifact["recommendation_served"] is False
    assert artifact["proactive_sent"] is False
    assert artifact["runtime_effect_allowed"] is False
    assert artifact["surface_policy"] == {
        "only_when_user_opens_or_provides_menu": True,
        "background_push_allowed": False,
        "current_surface_only": True,
    }

    highlights = {item["menu_item_name"]: item for item in artifact["menu_highlights"]}
    assert highlights["oatmeal with latte"]["highlight_status"] == (
        "eligible_positive_highlight"
    )
    assert (
        "golden-order-morning-bar-oatmeal-latte"
        in highlights["oatmeal with latte"]["source_candidate_ids"]
    )
    assert highlights["cilantro chicken bowl"]["highlight_status"] == (
        "suppressed_by_negative_preference"
    )
    assert highlights["cilantro chicken bowl"]["annoyance_policy"] == (
        "never_push_only_show_when_menu_is_active"
    )


def test_menu_highlight_context_is_declared_as_product_capability_context() -> None:
    from app.memory.application.long_term_context_shadow_lab import (
        build_shadow_lab_artifacts,
    )

    artifact = build_shadow_lab_artifacts(_fixture_payload())[
        "product_capability_context_map"
    ]

    domains = {
        domain["context_domain_id"]: domain for domain in artifact["context_domains"]
    }
    assert domains["menu_highlight_context"]["primary_consumers"] == [
        "recommendation",
        "intake_clarification",
        "chat_context",
    ]

    recommendation = next(
        consumer
        for consumer in artifact["consumer_contracts"]
        if consumer["consumer_id"] == "recommendation"
    )
    assert "menu_highlight_context" in recommendation["uses_context_domains"]

    by_family = {
        family["family_id"]: family for family in artifact["capability_families"]
    }
    assert "menu_highlight_context" in by_family["F6"]["context_domain_ids"]

    reducer = build_shadow_lab_artifacts(_fixture_payload())["review_queue_reducer"]
    deferred = {
        item["mechanism_id"]: item for item in reducer["deferred_mechanism_reviews"]
    }
    assert deferred["live_menu_scan_runtime"]["current_shadow_coverage"] == (
        "menu_highlight_shadow_eval"
    )
