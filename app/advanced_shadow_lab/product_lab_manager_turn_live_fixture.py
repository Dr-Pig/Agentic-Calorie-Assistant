from __future__ import annotations

from pathlib import Path

from app.advanced_shadow_lab.product_lab_fixture_inputs import (
    build_product_lab_fixture_inputs,
)
from app.advanced_shadow_lab.product_lab_memory_store import ProductLabMemoryStore
from app.advanced_shadow_lab.product_lab_runtime import run_advanced_product_lab_turn


def build_manager_turn_live_runtime_artifact(artifact_root: Path) -> dict[str, object]:
    return run_advanced_product_lab_turn(
        lab_mode="isolated_advanced_product_lab",
        turn={
            "session_id": "lab-session-1",
            "turn_id": "lab-turn-1",
            "user_id": "user-1",
            "workspace_id": "ws-1",
            "surface": "chat",
            "user_utterance": "fixture text is not provider input",
            "semantic_intent_fixture": "repeat_meal_rescue_shadow",
        },
        fixture_inputs={
            **build_product_lab_fixture_inputs(),
            "user_id": "user-1",
            "workspace_id": "ws-1",
            "surface": "chat",
            "reusable_meal_intake_signal": {
                "normalized_signature": "mom_fried_rice",
                "explicit_same_as_before": True,
                "repetition_count": 4,
            },
            "reusable_meal_entities": [_reusable_meal_entity()],
        },
        manager_tool_store=_seed_store(artifact_root),
    )


def _seed_store(artifact_root: Path) -> ProductLabMemoryStore:
    store = ProductLabMemoryStore(artifact_root / "manager-turn-memory-store")
    write = store.write_memory_events(
        session_id="lab-session-1",
        turn_id="seed-turn",
        events=[
            {
                "memory_id": "reusable-meal-hint-1",
                "memory_type": "pattern_memory",
                "summary": "Mom fried rice often maps to reusable meal ufe-fried-rice.",
                "review_status": "accepted_lab",
                "source_object_refs": ["meal_thread:mt-101"],
                "intended_consumers": ["reusable_meal", "rescue"],
            }
        ],
    )
    if write["status"] != "pass":
        raise RuntimeError(f"manager_turn_live_fixture_seed_failed:{write['blockers']}")
    return store


def _reusable_meal_entity() -> dict[str, object]:
    return {
        "entity_id": "ufe-fried-rice",
        "user_id": "user-1",
        "workspace_id": "ws-1",
        "display_name": "Mom fried rice",
        "status": "confirmed",
        "review_required": False,
        "current_version_id": "v1",
        "correction_count": 0,
        "drift_status": "stable",
        "version_history": [
            {
                "version_id": "v1",
                "normalized_signature": "mom_fried_rice",
                "source_kind": "mom_bought",
                "ingredient_profile": ["rice", "egg", "pork"],
                "portion_profile": {"serving": "large_plate"},
                "estimate_posture": "reuse_anchored",
                "source_refs": ["meal_thread:mt-101", "memory_record:reusable-meal-hint-1"],
            }
        ],
    }


__all__ = ["build_manager_turn_live_runtime_artifact"]
