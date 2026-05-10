from __future__ import annotations

from pathlib import Path

from app.nutrition.application.food_evidence_index_port import FoodEvidenceIndexPort
from app.nutrition.application.fooddb_retrieval_policy import retrieve_fooddb_candidates
from app.nutrition.infrastructure.local_food_evidence_index import (
    LocalSmallAnchorFoodEvidenceIndex,
)
from app.nutrition.infrastructure.sqlite_food_evidence_index import (
    SQLiteFtsFoodEvidenceIndex,
)


SMALL_ANCHOR_STORE = Path("app/knowledge/small_anchor_store_tw.json")


def _local_records():
    return LocalSmallAnchorFoodEvidenceIndex.from_path(SMALL_ANCHOR_STORE).load_records()


def test_sqlite_fts_index_implements_port_and_preserves_indexed_records(tmp_path: Path) -> None:
    records = _local_records()
    db_path = tmp_path / "food_evidence.sqlite"

    index = SQLiteFtsFoodEvidenceIndex.rebuild_from_records(db_path, records)

    assert isinstance(index, FoodEvidenceIndexPort)
    assert index.load_records() == records


def test_sqlite_fts_index_reports_adapter_metadata_without_policy_leakage(tmp_path: Path) -> None:
    index = SQLiteFtsFoodEvidenceIndex.rebuild_from_records(tmp_path / "food.sqlite", _local_records())

    metadata = index.describe_index()

    assert metadata["adapter_type"] == "sqlite_fts_food_evidence_index"
    assert metadata["record_contract"] == "IndexedFoodRecord"
    assert metadata["runtime_record_count"] == 59
    assert metadata["semantic_record_count"] >= 1
    assert metadata["fts_table"] == "food_evidence_fts"
    assert metadata["future_backends"] == ["supabase"]
    assert metadata["forbidden_policy_dependencies"] == [
        "supabase_client",
        "webshell",
        "manager_context_packet",
    ]


def test_sqlite_fts_search_returns_port_records_for_retrieval_policy(tmp_path: Path) -> None:
    index = SQLiteFtsFoodEvidenceIndex.rebuild_from_records(tmp_path / "food.sqlite", _local_records())

    records = index.search_records("boba")
    result = retrieve_fooddb_candidates("boba", retrieval_records=records)

    assert records
    assert result["accepted_candidates"][0]["anchor_id"] == "custom_drink_boba_milk_tea"


def test_sqlite_fts_search_handles_operator_like_text_as_plain_terms(tmp_path: Path) -> None:
    index = SQLiteFtsFoodEvidenceIndex.rebuild_from_records(tmp_path / "food.sqlite", _local_records())

    records = index.search_records('" OR food_evidence_fts MATCH *')

    assert isinstance(records, tuple)


def test_sqlite_fts_search_closes_file_handles_after_use(tmp_path: Path) -> None:
    db_path = tmp_path / "food.sqlite"
    index = SQLiteFtsFoodEvidenceIndex.rebuild_from_records(db_path, _local_records())

    index.search_records("boba")
    db_path.unlink()

    assert not db_path.exists()


def test_sqlite_fts_search_clamps_limit_bounds(tmp_path: Path) -> None:
    index = SQLiteFtsFoodEvidenceIndex.rebuild_from_records(tmp_path / "food.sqlite", _local_records())

    one = index.search_records("boba", limit=1)
    zero = index.search_records("boba", limit=0)
    negative = index.search_records("boba", limit=-1)
    huge = index.search_records("boba", limit=10_000)

    assert len(one) == 1
    assert len(zero) == 1
    assert len(negative) == 1
    assert len(huge) <= SQLiteFtsFoodEvidenceIndex.MAX_SEARCH_LIMIT
