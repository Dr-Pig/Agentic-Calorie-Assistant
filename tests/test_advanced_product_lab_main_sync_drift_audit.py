from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
AUDIT_PATH = (
    ROOT / "docs" / "quality" / "advanced_product_lab_main_sync_drift_audit.yaml"
)
TRAIN_PATH = (
    ROOT
    / "docs"
    / "quality"
    / "advanced_product_lab_context_engineering_stress_pr_train.yaml"
)
DOC_INDEX_PATH = ROOT / "docs" / "DOC_INDEX.md"


def _load(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8-sig"))


def test_main_sync_drift_audit_records_safe_main_to_lab_merge() -> None:
    audit = _load(AUDIT_PATH)

    assert audit["artifact_type"] == "advanced_product_lab_main_sync_drift_audit"
    assert audit["status"] == "recorded"
    assert audit["slice_number"] == 1
    assert audit["slice_id"] == "main_to_lab_sync_and_contract_drift_audit"
    assert audit["source_main_commit"] == "0f6a694f"
    assert audit["merge_base_commit"] == "95ba5852"
    assert audit["merge_posture"] == "main_to_lab_no_runtime_activation"
    assert audit["advanced_lab_bootstrap_preserved"] is True
    assert audit["advanced_lab_artifacts_removed"] == []


def test_main_sync_drift_audit_keeps_activation_wall_and_names_main_changes() -> None:
    audit = _load(AUDIT_PATH)

    assert audit["activation_wall"] == {
        "mainline_activation_enabled": False,
        "production_route_or_api_mount_allowed": False,
        "production_scheduler_delivery_allowed": False,
        "production_db_migration_allowed": False,
        "canonical_product_mutation_allowed_on_main": False,
        "durable_product_memory_activation_on_main": False,
    }
    assert audit["main_change_family"] == "current_shell_fooddb_desktop_dogfood_alignment"
    assert audit["merged_file_count"] == 12
    assert "static/accurate-intake-desktop.html" in audit["merged_files"]
    assert "app/nutrition/application/fooddb_real_manager_e2e.py" in audit["merged_files"]


def test_context_engineering_stress_train_marks_slice_one_complete() -> None:
    train = _load(TRAIN_PATH)

    assert train["dynamic_remaining_slice_count"] == 11
    assert train["last_completed_slice_number"] == 5
    assert train["active_slice_number"] is None
    assert train["last_merge_evidence"]["completed_slices"][0] == {
        "slice_number": 1,
        "slice_id": "main_to_lab_sync_and_contract_drift_audit",
        "result": "main_sync_drift_audit_recorded",
        "artifact": "docs/quality/advanced_product_lab_main_sync_drift_audit.yaml",
        "dynamic_remaining_slice_count_after": 15,
    }


def test_main_sync_drift_audit_is_indexed() -> None:
    doc_index = DOC_INDEX_PATH.read_text(encoding="utf-8-sig")

    assert "advanced_product_lab_main_sync_drift_audit.yaml" in doc_index
