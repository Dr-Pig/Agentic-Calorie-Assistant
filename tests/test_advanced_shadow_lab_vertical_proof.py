from __future__ import annotations

from app.advanced_shadow_lab.vertical_proof import (
    build_fixture_vertical_proof_input,
    run_fixture_vertical_proof,
)


def test_fixture_vertical_proof_runs_complete_lab_loop_without_mainline_effects(
    tmp_path,
) -> None:
    payload = build_fixture_vertical_proof_input()

    artifact = run_fixture_vertical_proof(payload, artifact_root=tmp_path)

    assert artifact["artifact_type"] == "advanced_shadow_lab_vertical_proof_artifact"
    assert artifact["status"] == "pass"
    assert artifact["lab_namespace"] == "advanced_shadow_lab"
    assert artifact["stage_order"] == [
        "runtime_lab_reviewed_memory_store_write",
        "shadow_memory_context_pack",
        "runtime_lab_memory_consumer_summary_projection",
        "advanced_shadow_e2e_fixture_chain_artifact",
        "proactive_no_send_review_sink_artifact",
        "advanced_shadow_chat_ux_packet_artifact",
        "advanced_shadow_chat_first_journey_proof_artifact",
    ]
    assert "memory_like_input" not in payload
    assert "recommendation_like_candidate" not in payload
    assert [row["artifact_type"] for row in artifact["artifact_lineage"]] == artifact[
        "stage_order"
    ]
    stage_by_type = {
        stage["artifact_type"]: stage for stage in artifact["stage_artifacts"]
    }
    context_pack = stage_by_type["shadow_memory_context_pack"]
    memory_projection = stage_by_type[
        "runtime_lab_memory_consumer_summary_projection"
    ]
    fixture_chain = stage_by_type["advanced_shadow_e2e_fixture_chain_artifact"]
    terminal_sink = stage_by_type["proactive_no_send_review_sink_artifact"]
    chat_packet = stage_by_type["advanced_shadow_chat_ux_packet_artifact"]
    journey_proof = stage_by_type["advanced_shadow_chat_first_journey_proof_artifact"]

    assert context_pack["reviewed_memory_store_used"] is True
    assert "golden-order-morning-bar-oatmeal-latte" in context_pack[
        "selected_candidate_ids"
    ]
    assert memory_projection["source_context_pack_used"] is True
    assert memory_projection["reviewed_memory_store_used"] is True
    assert fixture_chain["status"] == "pass"
    assert fixture_chain["stage_artifacts"][1]["three_node_lab_bridge_used"] is True
    assert terminal_sink["status"] == "pass"
    assert terminal_sink["record_count"] == 2
    assert chat_packet["status"] == "pass"
    assert chat_packet["packet_count"] == 2
    assert journey_proof["status"] == "pass"
    assert journey_proof["scenario_ids"] == [
        "memory_guided_recommendation_chat_offer",
        "rescue_proactive_no_send_chat_candidate",
        "dismiss_snooze_undo_shadow_controls",
    ]
    scenario_by_id = {
        row["scenario_id"]: row for row in journey_proof["scenario_rows"]
    }
    memory_scenario = scenario_by_id["memory_guided_recommendation_chat_offer"]
    assert memory_scenario["lineage_candidate_ids"] == [
        "golden-order-morning-bar-oatmeal-latte"
    ]
    assert memory_scenario["recommendation_source_refs"] == [
        "memory_candidate:golden-order-morning-bar-oatmeal-latte"
    ]
    assert memory_scenario["terminal_packet_refs"] == [
        "journey:L:recommendation_offer_pending_intent_packet",
        "journey:M:memory_review_adjusted_recommendation_packet",
    ]

    rescue_scenario = scenario_by_id["rescue_proactive_no_send_chat_candidate"]
    assert rescue_scenario["terminal_record_refs"] == [
        "recommendation_prompt:dismiss",
        "rescue_nudge:snooze",
    ]
    assert rescue_scenario["source_domains_by_packet"] == {
        "recommendation_prompt:0": ["memory", "recommendation", "proactive"],
        "rescue_nudge:1": ["memory", "rescue", "proactive"],
    }

    controls = scenario_by_id["dismiss_snooze_undo_shadow_controls"][
        "control_semantics"
    ]
    assert controls == {
        "dismiss": {
            "observed": True,
            "durable_suppression_written": False,
            "semantic_effect": "hide_current_shadow_candidate_only",
        },
        "snooze": {
            "observed": True,
            "durable_snooze_written": False,
            "semantic_effect": "wait_for_next_signal_without_scheduler_delivery",
        },
        "undo": {
            "configured": True,
            "canonical_rollback_requested": False,
            "semantic_effect": "current_no_send_candidate_only",
        },
    }
    for row in journey_proof["scenario_rows"]:
        assert row["surface"] == "chat"
        assert row["chat_first"] is True
        assert row["served_to_user"] is False
        assert row["delivery_attempted"] is False
        assert row["scheduler_enqueued"] is False
        assert row["canonical_mutation_requested"] is False
        assert row["semantic_decision_inferred_by_runner"] is False
    assert journey_proof["lineage_status"] == "pass"
    assert journey_proof["new_report_family_created"] is False
    assert journey_proof["runtime_connected"] is False
    assert journey_proof["live_provider_used"] is False
    assert journey_proof["durable_product_memory_written"] is False
    assert journey_proof["manager_context_packet_changed"] is False
    assert journey_proof["user_facing_behavior_changed"] is False
    assert artifact["scope"] == {
        "user_id": "user-fixture-1",
        "workspace_id": "workspace-fixture-1",
        "project_id": "advanced-shadow-lab",
        "surface": "fixture_lab",
        "run_id": "vertical-proof-run-1",
    }
    assert artifact["lab_delivery_record"] == {
        "sink": "isolated_lab_sink",
        "delivery_mode": "record_only",
        "source_artifact_type": "proactive_no_send_review_sink_artifact",
        "record_count": 2,
        "delivered_to_production": False,
    }
    assert artifact["activation_flags"] == _false_activation_flags()
    assert artifact["non_claims"] == {
        "not_runtime_activation_evidence": True,
        "not_product_readiness_evidence": True,
        "not_user_facing_activation": True,
        "not_canonical_mutation_authority": True,
    }


def test_fixture_vertical_proof_blocks_missing_scope_before_building_outputs() -> None:
    payload = build_fixture_vertical_proof_input()
    payload["scope"].pop("workspace_id")

    artifact = run_fixture_vertical_proof(payload)

    assert artifact["status"] == "blocked"
    assert artifact["blockers"] == ["scope.workspace_id_missing"]
    assert artifact["stage_order"] == []
    assert artifact["stage_artifacts"] == []
    assert artifact["artifact_lineage"] == []
    assert artifact["lab_delivery_record"] is None
    assert artifact["activation_flags"] == _false_activation_flags()


def test_fixture_vertical_proof_blocks_attempted_runtime_or_mutation_effects() -> None:
    payload = build_fixture_vertical_proof_input()
    payload["requested_effects"] = {
        "mainline_runtime_connected": True,
        "production_scheduler_delivery_allowed": True,
        "canonical_product_mutation_allowed": True,
    }

    artifact = run_fixture_vertical_proof(payload)

    assert artifact["status"] == "blocked"
    assert artifact["blockers"] == [
        "requested_effects.mainline_runtime_connected_not_allowed",
        "requested_effects.production_scheduler_delivery_allowed_not_allowed",
        "requested_effects.canonical_product_mutation_allowed_not_allowed",
    ]
    assert artifact["lab_delivery_record"] is None
    assert artifact["activation_flags"] == _false_activation_flags()


def _false_activation_flags() -> dict[str, bool]:
    return {
        "mainline_runtime_connected": False,
        "mainline_route_or_api_mount_allowed": False,
        "production_scheduler_delivery_allowed": False,
        "production_db_migration_allowed": False,
        "canonical_product_mutation_allowed": False,
        "durable_product_memory_written": False,
        "manager_context_packet_changed": False,
        "user_facing_behavior_changed": False,
        "live_provider_used": False,
        "product_readiness_claimed": False,
    }
