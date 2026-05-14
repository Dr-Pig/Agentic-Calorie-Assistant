from __future__ import annotations

from app.nutrition.infrastructure.small_anchor_store_loader import (
    load_small_anchor_seed_records,
)
from app.nutrition.application.retrieval_intent import build_retrieval_intent
from app.nutrition.application.small_anchor_store import lookup_anchor_candidates


class _DuplicateAnchorStore:
    def load_small_anchor_records(self) -> list[dict[str, object]]:
        return [
            {
                "record_kind": "generic_anchor",
                "anchor_id": "first_ramen_anchor",
                "canonical_name": "拉麵",
                "aliases": ["ramen"],
                "dish_type": "noodle",
                "baseline_kcal_range": [650, 950],
                "baseline_likely_kcal": 800,
                "followup_hints": ["ask_noodle_portion"],
            },
            {
                "record_kind": "generic_anchor",
                "anchor_id": "second_ramen_anchor",
                "canonical_name": "拉麵",
                "aliases": ["ramen bowl"],
                "dish_type": "noodle",
                "baseline_kcal_range": [700, 1000],
                "baseline_likely_kcal": 850,
                "followup_hints": ["ask_noodle_portion"],
            },
        ]

    def load_exact_item_card_records(self) -> list[dict[str, object]]:
        return []


def test_small_anchor_loader_includes_runtime_batch_files() -> None:
    records = load_small_anchor_seed_records()
    by_id = {str(record.get("anchor_id")): record for record in records}

    assert by_id["stable_base_beef_noodle"]["runtime_truth_allowed"] is True
    assert by_id["generic_meal_hawaiian_pizza_slice"]["runtime_truth_allowed"] is True
    assert by_id["generic_meal_hawaiian_pizza_slice"]["source_refs"][0][
        "runtime_role"
    ] == "source_evidence_only"
    assert by_id["listed_item_chicken_nugget"]["composition_posture"] == "listed_item_component"
    assert by_id["listed_item_chicken_nugget"]["runtime_usage_boundary"] == "listed_component_only"
    assert by_id["dessert_grass_jelly_bowl"].get("macro_visibility_candidate") is None


def test_anchor_lookup_dedupes_same_canonical_across_seed_sources() -> None:
    result = lookup_anchor_candidates(
        build_retrieval_intent("我吃了拉麵"),
        evidence_store=_DuplicateAnchorStore(),
        limit=4,
    )

    assert [candidate.canonical_name for candidate in result.candidates] == ["拉麵"]
