from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from app.nutrition.application.fooddb_index_backend_parity import (
    build_fooddb_index_backend_parity,
)
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
    local = _local_index()
    return SQLiteFtsFoodEvidenceIndex.rebuild_from_records(
        tmp_path / "food_evidence.sqlite",
        local.load_records(),
    )


def _supabase_index() -> SupabaseRowsFoodEvidenceIndex:
    return SupabaseRowsFoodEvidenceIndex.from_rows(
        tuple(asdict(record) for record in _local_index().load_records())
    )


def test_fooddb_index_backend_parity_passes_for_local_sqlite_and_supabase_rows(
    tmp_path: Path,
) -> None:
    artifact = build_fooddb_index_backend_parity(
        local_index=_local_index(),
        sqlite_index=_sqlite_index(tmp_path),
        supabase_index=_supabase_index(),
    )

    assert artifact["artifact_type"] == "accurate_intake_fooddb_index_backend_parity_v1"
    assert artifact["classification"] == "deterministic_backend_parity_only"
    assert artifact["status"] == "pass"
    assert artifact["runtime_truth_changed"] is False
    assert artifact["mutation_changed"] is False
    assert artifact["manager_context_changed"] is False
    assert artifact["packetizer_format_changed"] is False
    assert artifact["live_provider_used"] is False
    assert artifact["live_websearch_used"] is False
    assert artifact["readiness_claimed"] is False
    assert artifact["summary"]["backend_labels"] == [
        "local_json",
        "sqlite_fts",
        "supabase_rows",
    ]
    assert artifact["summary"]["fail_count"] == 0
    assert artifact["next_required_slice"] == "grokfast_fooddb_diagnostic_preflight"


def test_fooddb_index_backend_parity_hides_backend_from_manager_visible_tool_result(
    tmp_path: Path,
) -> None:
    artifact = build_fooddb_index_backend_parity(
        local_index=_local_index(),
        sqlite_index=_sqlite_index(tmp_path),
        supabase_index=_supabase_index(),
    )

    for case in artifact["cases"]:
        assert case["checks"]["manager_visible_boundary"] is True
        for backend in case["backend_results"]:
            assert backend["tool_result_runtime_mutation_allowed"] is False
            assert backend["tool_result_source_implementation_visible"] is False
            assert backend["manager_visible_boundary_passed"] is True


def test_fooddb_index_backend_parity_blocks_backend_drift(tmp_path: Path) -> None:
    rows = tuple(
        asdict(record)
        for record in _local_index().load_records()
        if record.anchor_id != "custom_drink_boba_milk_tea"
    )
    artifact = build_fooddb_index_backend_parity(
        local_index=_local_index(),
        sqlite_index=_sqlite_index(tmp_path),
        supabase_index=SupabaseRowsFoodEvidenceIndex.from_rows(rows),
    )

    assert artifact["status"] == "blocked"
    assert "backend_parity_case_failed:boba_alias" in artifact["blockers"]
    boba = next(case for case in artifact["cases"] if case["case_id"] == "boba_alias")
    assert boba["checks"]["accepted_anchor_parity"] is False


def test_fooddb_index_backend_parity_blocks_manager_visible_nutrition_drift(
    tmp_path: Path,
) -> None:
    rows = []
    for record in _local_index().load_records():
        row = asdict(record)
        if record.anchor_id == "custom_drink_boba_milk_tea":
            row["kcal_point"] = 999
            row["kcal_range"] = [990, 1000]
        rows.append(row)

    artifact = build_fooddb_index_backend_parity(
        local_index=_local_index(),
        sqlite_index=_sqlite_index(tmp_path),
        supabase_index=SupabaseRowsFoodEvidenceIndex.from_rows(tuple(rows)),
    )

    assert artifact["status"] == "blocked"
    assert "backend_parity_case_failed:boba_alias" in artifact["blockers"]
    boba = next(case for case in artifact["cases"] if case["case_id"] == "boba_alias")
    assert boba["checks"]["accepted_anchor_parity"] is True
    assert boba["checks"]["manager_visible_evidence_payload_parity"] is False


def test_fooddb_index_backend_parity_blocks_empty_case_suite(tmp_path: Path) -> None:
    artifact = build_fooddb_index_backend_parity(
        local_index=_local_index(),
        sqlite_index=_sqlite_index(tmp_path),
        supabase_index=_supabase_index(),
        cases=(),
    )

    assert artifact["status"] == "blocked"
    assert "backend_parity_case_suite_empty" in artifact["blockers"]
    assert artifact["summary"]["case_count"] == 0


def test_fooddb_index_backend_parity_script_roundtrip(tmp_path: Path) -> None:
    from app.shared.infra.json_artifacts import read_json_artifact
    from scripts.build_accurate_intake_fooddb_index_backend_parity import main

    output = tmp_path / "backend_parity.json"
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
    assert artifact["artifact_type"] == "accurate_intake_fooddb_index_backend_parity_v1"
    assert artifact["status"] == "pass"
    assert sqlite_db.exists()
