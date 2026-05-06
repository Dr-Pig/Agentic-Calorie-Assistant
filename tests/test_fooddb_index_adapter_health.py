from __future__ import annotations

from pathlib import Path
from typing import Any

from app.nutrition.application.food_evidence_index_port import FoodEvidenceIndexPort
from app.nutrition.application.fooddb_index_adapter_health import (
    DEFAULT_ADAPTER_HEALTH_SEARCH_CASES,
    build_fooddb_index_adapter_health,
)
from app.nutrition.application.fooddb_retrieval_policy import IndexedFoodRecord
from app.nutrition.infrastructure.local_food_evidence_index import (
    LocalSmallAnchorFoodEvidenceIndex,
)
from app.nutrition.infrastructure.sqlite_food_evidence_index import (
    SQLiteFtsFoodEvidenceIndex,
)
from app.nutrition.infrastructure.supabase_food_evidence_index import (
    SupabaseRowsFoodEvidenceIndex,
)


SMALL_ANCHOR_STORE = Path("app/knowledge/small_anchor_store_tw.json")


def _local_index() -> LocalSmallAnchorFoodEvidenceIndex:
    return LocalSmallAnchorFoodEvidenceIndex.from_path(SMALL_ANCHOR_STORE)


def _sqlite_index(tmp_path: Path) -> SQLiteFtsFoodEvidenceIndex:
    return SQLiteFtsFoodEvidenceIndex.rebuild_from_records(
        tmp_path / "food_evidence.sqlite",
        _local_index().load_records(),
    )


class _FakeIndex:
    def __init__(
        self,
        records: tuple[IndexedFoodRecord, ...],
        *,
        runtime_truth_boundary: str | None = "adapter_returns_indexed_records_not_truth_decisions",
    ) -> None:
        self._records = records
        self._runtime_truth_boundary = runtime_truth_boundary

    def load_records(self) -> tuple[IndexedFoodRecord, ...]:
        return self._records

    def describe_index(self) -> dict[str, Any]:
        metadata = {
            "adapter_type": "fake_test_index",
            "record_contract": "IndexedFoodRecord",
            "runtime_record_count": len(
                [
                    record
                    for record in self._records
                    if record.runtime_role == "common_serving_anchor"
                ]
            ),
            "semantic_record_count": len(
                [
                    record
                    for record in self._records
                    if record.runtime_role == "basket_family_semantic_only"
                ]
            ),
            "forbidden_policy_dependencies": [
                "sqlite_file_path",
                "supabase_client",
                "webshell",
                "manager_context_packet",
            ],
        }
        if self._runtime_truth_boundary is not None:
            metadata["runtime_truth_boundary"] = self._runtime_truth_boundary
        return metadata


def _indexed_record(**overrides: Any) -> IndexedFoodRecord:
    base = {
        "anchor_id": "test_anchor",
        "canonical_name": "Test Anchor",
        "aliases": ("test",),
        "dish_type": "test",
        "runtime_truth_allowed": True,
        "runtime_role": "common_serving_anchor",
        "kcal_point": 100,
        "kcal_range": (90, 110),
        "serving_basis": "common_serving",
        "portion_basis": {"amount": 1, "unit": "serving"},
        "followup_hints": (),
        "major_modifiers": (),
        "runtime_usage_boundary": "single_item_or_listed_component",
        "source_provenance": {"source_class": "internal_seed"},
        "approval_metadata": {"approval_mode": "batch_policy_approved"},
    }
    base.update(overrides)
    return IndexedFoodRecord(**base)


def test_fooddb_index_adapter_health_proves_local_and_sqlite_contract_parity(
    tmp_path: Path,
) -> None:
    artifact = build_fooddb_index_adapter_health(
        local_index=_local_index(),
        sqlite_index=_sqlite_index(tmp_path),
    )

    assert artifact["artifact_type"] == "accurate_intake_fooddb_index_adapter_health_v1"
    assert artifact["classification"] == "deterministic_adapter_health_only"
    assert artifact["status"] == "pass"
    assert artifact["runtime_truth_changed"] is False
    assert artifact["mutation_changed"] is False
    assert artifact["manager_context_changed"] is False
    assert artifact["packetizer_format_changed"] is False
    assert artifact["live_provider_used"] is False
    assert artifact["readiness_claimed"] is False
    assert artifact["summary"]["local_record_count"] == artifact["summary"]["sqlite_record_count"]
    assert artifact["summary"]["record_contract_parity"] is True
    assert artifact["summary"]["runtime_boundary_passed"] is True
    assert artifact["summary"]["search_case_fail_count"] == 0
    assert artifact["next_required_slice"] == "grokfast_fooddb_diagnostic_preflight"


def test_fooddb_index_adapter_health_checks_search_cases_without_runtime_decision(
    tmp_path: Path,
) -> None:
    artifact = build_fooddb_index_adapter_health(
        local_index=_local_index(),
        sqlite_index=_sqlite_index(tmp_path),
    )
    cases = {case["case_id"]: case for case in artifact["search_cases"]}

    assert set(cases) == {case.case_id for case in DEFAULT_ADAPTER_HEALTH_SEARCH_CASES}
    assert cases["boba_alias"]["status"] == "pass"
    assert cases["boba_alias"]["top_anchor_id"] == "custom_drink_boba_milk_tea"
    assert cases["chicken_bento_alias"]["top_anchor_id"] == "generic_meal_chicken_bento"
    assert cases["kelp_component"]["top_anchor_id"] == "listed_item_kelp"
    for case in cases.values():
        assert case["runtime_mutation_allowed"] is False
        assert case["truth_selection_forbidden"] is True


def test_fooddb_index_adapter_health_fails_closed_on_record_drift(tmp_path: Path) -> None:
    sqlite_index = SQLiteFtsFoodEvidenceIndex.rebuild_from_records(
        tmp_path / "food_evidence.sqlite",
        _local_index().load_records()[:-1],
    )

    artifact = build_fooddb_index_adapter_health(
        local_index=_local_index(),
        sqlite_index=sqlite_index,
    )

    assert artifact["status"] == "blocked"
    assert "indexed_record_contract_drift" in artifact["blockers"]
    assert artifact["next_required_slice"] == "inspect_fooddb_index_adapter_health_blockers"


def test_fooddb_index_adapter_health_exposes_supabase_adapter_contract_without_using_supabase(
    tmp_path: Path,
) -> None:
    artifact = build_fooddb_index_adapter_health(
        local_index=_local_index(),
        sqlite_index=_sqlite_index(tmp_path),
    )

    supabase = artifact["future_backend_contracts"]["supabase"]
    assert supabase["status"] == "contract_only_not_connected"
    assert supabase["runtime_dependency_allowed"] is False
    assert supabase["manager_visible"] is False
    assert supabase["required_output_contract"] == "IndexedFoodRecord"
    assert "canonical_name" in supabase["minimum_columns"]
    assert "kcal_range" in supabase["minimum_columns"]
    assert "source_provenance" in supabase["minimum_columns"]


def test_fooddb_index_adapter_health_accepts_offline_supabase_row_adapter(
    tmp_path: Path,
) -> None:
    row = {
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
    }

    artifact = build_fooddb_index_adapter_health(
        local_index=_local_index(),
        sqlite_index=_sqlite_index(tmp_path),
        supabase_index=SupabaseRowsFoodEvidenceIndex.from_rows((row,)),
    )

    assert artifact["status"] == "pass"
    assert artifact["summary"]["supabase_record_count"] == 1
    assert artifact["summary"]["supabase_adapter_type"] == "supabase_rows_food_evidence_index"
    assert artifact["adapter_metadata"]["supabase"]["mapping_status"] == "pass"
    assert artifact["future_backend_contracts"]["supabase"]["status"] == (
        "offline_row_adapter_contract_available"
    )


def test_fooddb_index_adapter_health_blocks_empty_supabase_row_adapter(
    tmp_path: Path,
) -> None:
    artifact = build_fooddb_index_adapter_health(
        local_index=_local_index(),
        sqlite_index=_sqlite_index(tmp_path),
        supabase_index=SupabaseRowsFoodEvidenceIndex.from_rows(()),
    )

    assert artifact["status"] == "blocked"
    assert "supabase_index_no_mapped_records" in artifact["blockers"]
    assert artifact["summary"]["supabase_record_count"] == 0


def test_fooddb_index_adapter_health_blocks_source_only_runtime_truth_leak() -> None:
    unsafe = _indexed_record(
        anchor_id="tfda_source_evidence",
        runtime_role="source_evidence_only",
        runtime_truth_allowed=True,
        serving_basis="per_100g",
    )
    index: FoodEvidenceIndexPort = _FakeIndex((unsafe,))

    artifact = build_fooddb_index_adapter_health(
        local_index=index,
        sqlite_index=index,
        search_cases=(),
    )

    assert artifact["status"] == "blocked"
    assert artifact["summary"]["runtime_boundary_passed"] is False
    assert artifact["summary"]["record_boundary_passed"] is False
    assert artifact["summary"]["adapter_metadata_boundary_passed"] is True
    assert (
        "local:tfda_source_evidence:runtime_truth_allowed_forbidden_role:source_evidence_only"
        in artifact["blockers"]
    )
    assert (
        "sqlite:tfda_source_evidence:runtime_truth_allowed_forbidden_role:source_evidence_only"
        in artifact["blockers"]
    )


def test_fooddb_index_adapter_health_blocks_incomplete_runtime_anchor() -> None:
    incomplete = _indexed_record(
        anchor_id="incomplete_anchor",
        kcal_range=None,
        approval_metadata={},
    )
    index: FoodEvidenceIndexPort = _FakeIndex((incomplete,))

    artifact = build_fooddb_index_adapter_health(
        local_index=index,
        sqlite_index=index,
        search_cases=(),
    )

    assert artifact["status"] == "blocked"
    assert artifact["summary"]["record_boundary_passed"] is False
    assert artifact["summary"]["adapter_metadata_boundary_passed"] is True
    assert "local:incomplete_anchor:missing_kcal_range" in artifact["blockers"]
    assert "local:incomplete_anchor:missing_approval_metadata" in artifact["blockers"]
    assert "sqlite:incomplete_anchor:missing_kcal_range" in artifact["blockers"]
    assert "sqlite:incomplete_anchor:missing_approval_metadata" in artifact["blockers"]


def test_fooddb_index_adapter_health_blocks_missing_runtime_boundary_metadata() -> None:
    index: FoodEvidenceIndexPort = _FakeIndex(
        (_indexed_record(),),
        runtime_truth_boundary=None,
    )

    artifact = build_fooddb_index_adapter_health(
        local_index=index,
        sqlite_index=index,
        search_cases=(),
    )

    assert artifact["status"] == "blocked"
    assert artifact["summary"]["record_boundary_passed"] is True
    assert artifact["summary"]["adapter_metadata_boundary_passed"] is False
    assert artifact["summary"]["runtime_boundary_passed"] is False
    assert "local_index_runtime_truth_boundary_missing" in artifact["blockers"]
    assert "sqlite_index_runtime_truth_boundary_missing" in artifact["blockers"]


def test_fooddb_index_adapter_health_script_roundtrip(tmp_path: Path) -> None:
    from app.shared.infra.json_artifacts import read_json_artifact
    from scripts.build_accurate_intake_fooddb_index_adapter_health import main

    output = tmp_path / "adapter_health.json"
    sqlite_db = tmp_path / "food.sqlite"

    assert (
        main(
            [
                "--small-anchor-store",
                str(SMALL_ANCHOR_STORE),
                "--sqlite-db",
                str(sqlite_db),
                "--output",
                str(output),
            ]
        )
        == 0
    )

    artifact = read_json_artifact(output)
    assert artifact["artifact_type"] == "accurate_intake_fooddb_index_adapter_health_v1"
    assert artifact["status"] == "pass"
    assert sqlite_db.exists()
