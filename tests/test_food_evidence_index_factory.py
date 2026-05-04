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
