from __future__ import annotations

from pathlib import Path

from app.nutrition.application.fooddb_index_adapter_health import (
    DEFAULT_ADAPTER_HEALTH_SEARCH_CASES,
    build_fooddb_index_adapter_health,
)
from app.nutrition.infrastructure.local_food_evidence_index import (
    LocalSmallAnchorFoodEvidenceIndex,
)
from app.nutrition.infrastructure.sqlite_food_evidence_index import (
    SQLiteFtsFoodEvidenceIndex,
)


SMALL_ANCHOR_STORE = Path("app/knowledge/small_anchor_store_tw.json")


def _local_index() -> LocalSmallAnchorFoodEvidenceIndex:
    return LocalSmallAnchorFoodEvidenceIndex.from_path(SMALL_ANCHOR_STORE)


def _sqlite_index(tmp_path: Path) -> SQLiteFtsFoodEvidenceIndex:
    return SQLiteFtsFoodEvidenceIndex.rebuild_from_records(
        tmp_path / "food_evidence.sqlite",
        _local_index().load_records(),
    )


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
