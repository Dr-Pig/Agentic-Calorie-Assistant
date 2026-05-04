from __future__ import annotations

from tests.long_term_context_shadow_fixture import _fixture_payload


def test_context_signal_lifecycle_shadow_eval_connects_sources_to_product_value() -> (
    None
):
    from app.memory.application.long_term_context_shadow_lab import (
        build_shadow_lab_artifacts,
    )

    artifacts = build_shadow_lab_artifacts(_fixture_payload())
    artifact = artifacts["context_signal_lifecycle_shadow_eval"]

    assert artifact["artifact_type"] == "context_signal_lifecycle_shadow_eval"
    assert artifact["runtime_effect_allowed"] is False
    assert artifact["durable_memory_written"] is False
    assert artifact["manager_context_injected"] is False
    assert artifact["runtime_integration_complete"] is False
    assert artifact["shadow_evaluator_complete"] is True

    candidate_ids = {
        candidate["candidate_id"]
        for candidate in artifacts["long_term_memory_candidate_review"]["candidates"]
    }
    lifecycle_ids = {
        record["candidate_id"] for record in artifact["candidate_lifecycle_records"]
    }
    assert lifecycle_ids == candidate_ids

    for record in artifact["candidate_lifecycle_records"]:
        assert record["source_trace_ids"]
        assert record["source_object_refs_required"] is True
        assert record["runtime_effect_allowed"] is False
        assert record["promotion_blockers"]
        assert record["selected_context_pack_ids"] or record["deferred_reason"]
        assert record["review_artifact_key"] == "context_value_review_queue"

    by_candidate = {
        record["candidate_id"]: record
        for record in artifact["candidate_lifecycle_records"]
    }
    assert (
        "recommendation"
        in by_candidate["golden-order-morning-bar-oatmeal-latte"][
            "selected_context_pack_ids"
        ]
    )
    assert (
        "intake_chat_context"
        in by_candidate[
            next(
                candidate_id
                for candidate_id in candidate_ids
                if candidate_id.startswith("user-language-")
            )
        ]["selected_context_pack_ids"]
    )
    assert (
        by_candidate["conversation-recall-context-summary"]["context_ingress_mode"]
        == "future_tool_mediated_recall"
    )

    source_routes = {
        route["source_signal_id"]: route for route in artifact["source_signal_routes"]
    }
    assert "menu_scan_context" in source_routes
    assert "weekly_highlight_shadow_candidates" in source_routes
    assert source_routes["menu_scan_context"]["runtime_source_used"] is False
    assert (
        source_routes["weekly_highlight_shadow_candidates"]["narrative_generated"]
        is False
    )
    assert (
        artifact["completion_summary"]["all_candidates_have_pack_or_deferred_reason"]
        is True
    )
