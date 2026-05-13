from __future__ import annotations

from app.shared.contracts.reusable_meal_entity import (
    ReusableMealVersion,
    UserFoodEntity,
    build_reusable_meal_entity_contract,
)


def test_reusable_meal_entity_contract_declares_shared_truth_owner() -> None:
    artifact = build_reusable_meal_entity_contract()

    assert artifact["artifact_type"] == "shared_reusable_meal_entity_contract"
    assert artifact["status"] == "pass"
    assert artifact["truth_owner"] == "reusable_meal_entity"
    assert artifact["memory_is_not_truth_owner"] is True
    assert artifact["durable_write_enabled"] is False


def test_user_food_entity_tracks_versioned_reusable_meal_truth() -> None:
    version = ReusableMealVersion(
        version_id="rmv-1",
        normalized_signature="mom-fried-rice-egg-standard",
        source_kind="mom_bought",
        ingredient_profile=["fried_rice", "egg"],
        portion_profile={"bowl_size": "standard"},
        estimate_posture="reuse_anchored",
        source_refs=["meal_thread:mt-1", "message:turn-1"],
    )
    entity = UserFoodEntity(
        entity_id="ufe-1",
        user_id="u-1",
        workspace_id="w-1",
        display_name="Mom fried rice",
        status="confirmed",
        current_version_id="rmv-1",
        version_history=[version],
        correction_count=1,
        last_confirmed_at="2026-05-13T09:00:00Z",
    )

    assert entity.current_version_id == "rmv-1"
    assert entity.version_history[0].estimate_posture == "reuse_anchored"
    assert entity.version_history[0].source_refs == [
        "meal_thread:mt-1",
        "message:turn-1",
    ]
    assert entity.drift_status == "stable"


def test_reusable_meal_entity_supports_superseding_version_history() -> None:
    previous = ReusableMealVersion(
        version_id="rmv-1",
        normalized_signature="hotpot-standard",
        source_kind="custom_combo",
        ingredient_profile=["broth", "beef", "cabbage"],
        portion_profile={"size": "large"},
        estimate_posture="reuse_exact",
        source_refs=["meal_thread:mt-2"],
    )
    latest = ReusableMealVersion(
        version_id="rmv-2",
        normalized_signature="hotpot-standard-v2",
        source_kind="custom_combo",
        ingredient_profile=["broth", "beef", "cabbage", "tofu"],
        portion_profile={"size": "large"},
        estimate_posture="re_estimate_required",
        source_refs=["meal_thread:mt-3"],
        supersedes_version_id="rmv-1",
    )

    entity = UserFoodEntity(
        entity_id="ufe-2",
        user_id="u-1",
        workspace_id="w-1",
        display_name="Hotpot set",
        status="superseded",
        current_version_id="rmv-2",
        version_history=[previous, latest],
        drift_status="reestimate_required",
    )

    assert entity.version_history[1].supersedes_version_id == "rmv-1"
    assert entity.drift_status == "reestimate_required"
