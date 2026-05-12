from __future__ import annotations

from app.nutrition.infrastructure.small_anchor_store_loader import (
    load_small_anchor_seed_records,
)


def test_small_anchor_loader_includes_runtime_batch_files() -> None:
    records = load_small_anchor_seed_records()
    by_id = {str(record.get("anchor_id")): record for record in records}

    assert by_id["stable_base_beef_noodle"]["runtime_truth_allowed"] is True
    assert by_id["generic_meal_hawaiian_pizza_slice"]["runtime_truth_allowed"] is True
    assert by_id["generic_meal_hawaiian_pizza_slice"]["source_refs"][0][
        "runtime_role"
    ] == "source_evidence_only"
    assert by_id["dessert_grass_jelly_bowl"].get("macro_visibility_candidate") is None
