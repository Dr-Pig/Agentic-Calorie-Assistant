from __future__ import annotations

from pathlib import Path

from app.composition.food_evidence_index_composition import (
    FoodEvidenceIndexCompositionConfig,
    build_food_evidence_index,
    build_retriever_backend_availability,
)
from app.nutrition.application.food_evidence_index_port import FoodEvidenceIndexPort
from app.nutrition.application.food_evidence_retriever_router import (
    build_food_evidence_retriever_route_plan,
)
from app.nutrition.application.retrieval_intent import RetrievalIntent


SMALL_ANCHOR_STORE = Path("app/knowledge/small_anchor_store_tw.json")


def test_composition_builds_local_json_port_by_default() -> None:
    index = build_food_evidence_index(
        FoodEvidenceIndexCompositionConfig(
            backend="local_json",
            small_anchor_store_path=SMALL_ANCHOR_STORE,
        )
    )

    assert isinstance(index, FoodEvidenceIndexPort)
    assert index.describe_index()["adapter_type"] == "local_small_anchor_json"


def test_composition_builds_sqlite_fts_port_from_small_anchor_source(tmp_path: Path) -> None:
    index = build_food_evidence_index(
        FoodEvidenceIndexCompositionConfig(
            backend="sqlite_fts",
            small_anchor_store_path=SMALL_ANCHOR_STORE,
            sqlite_db_path=tmp_path / "food.sqlite",
        )
    )

    assert isinstance(index, FoodEvidenceIndexPort)
    assert index.describe_index()["adapter_type"] == "sqlite_fts_food_evidence_index"
    assert len(index.load_records()) == 55


def test_composition_builds_supabase_row_port_without_live_supabase() -> None:
    index = build_food_evidence_index(
        FoodEvidenceIndexCompositionConfig(
            backend="supabase_rows",
            small_anchor_store_path=SMALL_ANCHOR_STORE,
            supabase_rows=(
                {
                    "anchor_id": "single_item_tea_egg",
                    "canonical_name": "Tea egg",
                    "aliases": ["tea egg"],
                    "dish_type": "single_item",
                    "runtime_truth_allowed": True,
                    "runtime_role": "common_serving_anchor",
                    "kcal_point": 80,
                    "kcal_range": [70, 90],
                    "serving_basis": "common_serving",
                    "portion_basis": {"portion_unit": "egg", "portion_quantity": 1},
                    "runtime_usage_boundary": "single_item",
                    "source_provenance": {"source_id": "test_supabase_fixture"},
                    "approval_metadata": {
                        "approval_mode": "internal_seed_batch_approved"
                    },
                },
            ),
        )
    )

    assert isinstance(index, FoodEvidenceIndexPort)
    assert index.describe_index()["adapter_type"] == "supabase_rows_food_evidence_index"
    assert index.describe_index()["row_shape_policy"]["network_io_allowed"] is False
    assert len(index.load_records()) == 1


def test_composition_availability_drives_router_without_backend_leakage(tmp_path: Path) -> None:
    config = FoodEvidenceIndexCompositionConfig(
        backend="sqlite_fts",
        small_anchor_store_path=SMALL_ANCHOR_STORE,
        sqlite_db_path=tmp_path / "food.sqlite",
        websearch_candidate_lane=True,
    )

    availability = build_retriever_backend_availability(config)
    plan = build_food_evidence_retriever_route_plan(
        RetrievalIntent(
            base_dish="pearl black tea latte",
            aliases=["Milksha pearl black tea latte"],
            brand_hint="Milksha",
            size_hint="large",
            modifier_hints=[],
            listed_items=[],
            retrieval_goal="exact_brand_lookup",
        ),
        availability=availability,
    )

    assert plan.primary_backend == "sqlite_fts_index"
    assert plan.backend_sequence == (
        "sqlite_fts_index",
        "local_fooddb_index",
        "websearch_candidate_lane",
    )
    assert plan.websearch_runtime_truth_allowed is False


def test_composition_availability_can_route_supabase_before_local_fallback() -> None:
    config = FoodEvidenceIndexCompositionConfig(
        backend="supabase_rows",
        small_anchor_store_path=SMALL_ANCHOR_STORE,
        websearch_candidate_lane=False,
        supabase_rows=(
            {
                "anchor_id": "single_item_tea_egg",
                "canonical_name": "Tea egg",
                "aliases": ["tea egg"],
                "dish_type": "single_item",
                "runtime_truth_allowed": True,
                "runtime_role": "common_serving_anchor",
                "kcal_point": 80,
                "kcal_range": [70, 90],
                "serving_basis": "common_serving",
                "portion_basis": {"portion_unit": "egg", "portion_quantity": 1},
                "runtime_usage_boundary": "single_item",
                "source_provenance": {"source_id": "test_supabase_fixture"},
                "approval_metadata": {"approval_mode": "internal_seed_batch_approved"},
            },
        ),
    )

    availability = build_retriever_backend_availability(config)
    plan = build_food_evidence_retriever_route_plan(
        RetrievalIntent(
            base_dish="tea egg",
            aliases=["tea egg"],
            brand_hint=None,
            size_hint=None,
            modifier_hints=[],
            listed_items=[],
            retrieval_goal="generic_anchor_lookup",
        ),
        availability=availability,
    )

    assert availability.supabase_index is True
    assert plan.primary_backend == "supabase_index"
    assert plan.backend_sequence == ("supabase_index", "local_fooddb_index")
    assert plan.runtime_truth_source == "approved_fooddb_only"


def test_composition_availability_falls_back_when_supabase_rows_are_empty() -> None:
    config = FoodEvidenceIndexCompositionConfig(
        backend="supabase_rows",
        small_anchor_store_path=SMALL_ANCHOR_STORE,
        supabase_rows=(),
    )

    availability = build_retriever_backend_availability(config)
    plan = build_food_evidence_retriever_route_plan(
        RetrievalIntent(
            base_dish="tea egg",
            aliases=["tea egg"],
            brand_hint=None,
            size_hint=None,
            modifier_hints=[],
            listed_items=[],
            retrieval_goal="generic_anchor_lookup",
        ),
        availability=availability,
    )

    assert availability.supabase_index is False
    assert plan.primary_backend == "local_fooddb_index"


def test_composition_availability_falls_back_when_supabase_runtime_record_is_incomplete() -> None:
    config = FoodEvidenceIndexCompositionConfig(
        backend="supabase_rows",
        small_anchor_store_path=SMALL_ANCHOR_STORE,
        supabase_rows=(
            {
                "anchor_id": "incomplete_anchor",
                "canonical_name": "Incomplete Anchor",
                "aliases": ["incomplete"],
                "dish_type": "single_item",
                "runtime_truth_allowed": True,
                "runtime_role": "common_serving_anchor",
            },
        ),
    )

    availability = build_retriever_backend_availability(config)
    plan = build_food_evidence_retriever_route_plan(
        RetrievalIntent(
            base_dish="incomplete",
            aliases=["incomplete"],
            brand_hint=None,
            size_hint=None,
            modifier_hints=[],
            listed_items=[],
            retrieval_goal="generic_anchor_lookup",
        ),
        availability=availability,
    )

    assert availability.supabase_index is False
    assert plan.primary_backend == "local_fooddb_index"
