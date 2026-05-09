from __future__ import annotations

from app.advanced_shadow_lab.vertical_proof import (
    build_fixture_vertical_proof_input,
    run_fixture_vertical_proof,
)


def test_fixture_vertical_proof_runs_complete_lab_loop_without_mainline_effects() -> None:
    payload = build_fixture_vertical_proof_input()

    artifact = run_fixture_vertical_proof(payload)

    assert artifact["artifact_type"] == "advanced_shadow_lab_vertical_proof_artifact"
    assert artifact["status"] == "pass"
    assert artifact["lab_namespace"] == "advanced_shadow_lab"
    assert artifact["stage_order"] == [
        "memory_like_input",
        "recommendation_like_candidate",
        "rescue_like_candidate",
        "proactive_like_decision",
        "lab_delivery_record",
    ]
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
        "candidate_id": "proactive-fixture-1",
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
