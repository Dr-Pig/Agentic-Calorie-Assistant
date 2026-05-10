from __future__ import annotations

import json
from pathlib import Path

from app.composition.local_dogfood_data_hygiene import (
    backup_local_dogfood_db,
    build_local_dogfood_data_manifest,
    classify_local_dogfood_db,
    export_local_dogfood_db,
    import_preview_local_dogfood_export,
)


def test_fixture_and_smoke_databases_are_disposable_but_not_real_dogfood() -> None:
    fixture = classify_local_dogfood_db(Path(".pytest_tmp_local/accurate_intake_browser_shell_smoke.sqlite3"))

    assert fixture["db_class"] == "fixture_smoke_db"
    assert fixture["disposable"] is True
    assert fixture["backup_required_before_reset"] is False
    assert fixture["real_dogfood_data"] is False
    assert fixture["do_not_commit"] is True


def test_real_dogfood_database_requires_backup_before_reset() -> None:
    db_path = Path("workspace_data/local_dogfood/accurate_intake.sqlite3")

    manifest = build_local_dogfood_data_manifest(db_path=db_path, operation="reset")

    assert manifest["db_class"] == "real_dogfood_db"
    assert manifest["operation"] == "reset"
    assert manifest["allowed"] is False
    assert manifest["blockers"] == ["backup_required_before_reset"]
    assert manifest["contains_personal_diet_logs"] is True
    assert manifest["local_only"] is True
    assert manifest["do_not_commit"] is True
    assert manifest["db_exists"] is False
    assert manifest["db_size_bytes"] is None
    assert manifest["db_modified_at_utc"] is None


def test_inspect_reports_existing_source_db_file_metadata(tmp_path: Path) -> None:
    db_path = tmp_path / "real_dogfood" / "accurate_intake.sqlite3"
    db_path.parent.mkdir()
    db_path.write_bytes(b"sqlite bytes")

    manifest = build_local_dogfood_data_manifest(db_path=db_path, operation="inspect")

    assert manifest["status"] == "pass"
    assert manifest["db_exists"] is True
    assert manifest["db_size_bytes"] == len(b"sqlite bytes")
    assert isinstance(manifest["db_modified_at_utc"], str)


def test_real_dogfood_path_classification_wins_case_insensitively_over_smoke_name() -> None:
    db_path = Path("workspace_data/LOCAL_DOGFOOD/accurate_intake_smoke.sqlite3")

    manifest = classify_local_dogfood_db(db_path)

    assert manifest["db_class"] == "real_dogfood_db"
    assert manifest["real_dogfood_data"] is True
    assert manifest["disposable"] is False
    assert manifest["backup_required_before_reset"] is True


def test_real_dogfood_backup_copies_sqlite_file_and_writes_local_only_manifest(tmp_path: Path) -> None:
    db_path = tmp_path / "real_dogfood" / "accurate_intake.sqlite3"
    db_path.parent.mkdir()
    db_path.write_bytes(b"sqlite bytes")
    backup_dir = tmp_path / "backups"

    report = backup_local_dogfood_db(db_path=db_path, backup_dir=backup_dir, label="before-reset")

    backup_path = Path(report["backup_path"])
    manifest_path = Path(report["manifest_path"])
    assert report["status"] == "pass"
    assert backup_path.exists()
    assert backup_path.read_bytes() == b"sqlite bytes"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["operation"] == "backup"
    assert manifest["local_only"] is True
    assert manifest["contains_personal_diet_logs"] is True
    assert manifest["do_not_commit"] is True
    assert manifest["db_exists"] is True
    assert manifest["db_size_bytes"] == len(b"sqlite bytes")
    assert manifest["backup_path"] == str(backup_path)


def test_backup_sanitizes_label_before_writing_local_copy(tmp_path: Path) -> None:
    db_path = tmp_path / "real_dogfood" / "accurate_intake.sqlite3"
    db_path.parent.mkdir()
    db_path.write_bytes(b"sqlite bytes")

    report = backup_local_dogfood_db(
        db_path=db_path,
        backup_dir=tmp_path / "backups",
        label="../before reset!!",
    )

    backup_path = Path(report["backup_path"])
    assert report["status"] == "pass"
    assert ".." not in backup_path.name
    assert "before-reset" in backup_path.name


def test_backup_and_export_keep_generated_filenames_compact_for_windows_paths(
    tmp_path: Path,
) -> None:
    long_stem = "accurate_intake_product_pages_browser_smoke_with_nested_refresh_chain_state"
    db_path = tmp_path / "real_dogfood" / f"{long_stem}.sqlite3"
    db_path.parent.mkdir()
    db_path.write_bytes(b"sqlite bytes")
    long_label = "browser-refresh-chain-export-with-long-artifact-stem"

    backup = backup_local_dogfood_db(
        db_path=db_path,
        backup_dir=tmp_path / "backups",
        label=long_label,
    )
    export = export_local_dogfood_db(
        db_path=db_path,
        export_dir=tmp_path / "exports",
        label=long_label,
    )

    backup_path = Path(backup["backup_path"])
    backup_manifest_path = Path(backup["manifest_path"])
    export_path = Path(export["export_path"])
    export_manifest_path = Path(export["manifest_path"])
    assert len(backup_path.name) <= 96
    assert len(backup_manifest_path.name) <= 112
    assert len(export_path.name) <= 96
    assert len(export_manifest_path.name) <= 112
    assert "browser-refresh-chain-export" in backup_path.name
    assert "browser-refresh-chain-export" in export_path.name
    assert backup_path.exists()
    assert backup_manifest_path.exists()
    assert export_path.exists()
    assert export_manifest_path.exists()


def test_export_copies_real_dogfood_sqlite_and_marks_local_personal_logs(tmp_path: Path) -> None:
    db_path = tmp_path / "real_dogfood" / "accurate_intake.sqlite3"
    db_path.parent.mkdir()
    db_path.write_bytes(b"sqlite bytes")

    report = export_local_dogfood_db(db_path=db_path, export_dir=tmp_path / "exports", label="review")

    export_path = Path(report["export_path"])
    manifest_path = Path(report["manifest_path"])
    assert report["status"] == "pass"
    assert report["operation"] == "export"
    assert report["local_only"] is True
    assert report["contains_personal_diet_logs"] is True
    assert report["do_not_commit"] is True
    assert report["export_contains_sqlite_copy"] is True
    assert export_path.read_bytes() == b"sqlite bytes"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["export_path"] == str(export_path)
    assert manifest["contains_personal_diet_logs"] is True


def test_import_preview_reads_export_manifest_without_writing_target_db(tmp_path: Path) -> None:
    db_path = tmp_path / "real_dogfood" / "accurate_intake.sqlite3"
    db_path.parent.mkdir()
    db_path.write_bytes(b"sqlite bytes")
    export_report = export_local_dogfood_db(db_path=db_path, export_dir=tmp_path / "exports", label="review")
    target_db = tmp_path / "local_dogfood" / "accurate_intake.sqlite3"

    preview = import_preview_local_dogfood_export(
        export_manifest_path=Path(export_report["manifest_path"]),
        target_db_path=target_db,
    )

    assert preview["status"] == "pass"
    assert preview["operation"] == "import-preview"
    assert preview["writes_performed"] is False
    assert preview["import_allowed"] is False
    assert preview["local_only"] is True
    assert preview["contains_personal_diet_logs"] is True
    assert preview["do_not_commit"] is True
    assert target_db.exists() is False
    assert preview["export_format"] == "sqlite_copy_with_manifest"
    assert preview["export_contains_sqlite_copy"] is True
    assert preview["source_export_size_bytes"] == len(b"sqlite bytes")
    assert isinstance(preview["source_export_modified_at_utc"], str)
    assert preview["target_exists"] is False
    assert preview["target_backup_required_before_restore"] is True
    assert preview["manual_next_steps"] == [
        "review_export_manifest",
        "create_target_backup_before_restore",
        "restore_manually_outside_this_preview",
    ]


def test_import_preview_rejects_manifest_without_required_export_copy_metadata(tmp_path: Path) -> None:
    sqlite_copy = tmp_path / "exports" / "accurate_intake.sqlite3"
    sqlite_copy.parent.mkdir()
    sqlite_copy.write_bytes(b"sqlite bytes")
    manifest_path = tmp_path / "exports" / "bad-metadata.manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "operation": "export",
                "local_only": True,
                "do_not_commit": True,
                "contains_personal_diet_logs": True,
                "export_path": str(sqlite_copy),
            }
        ),
        encoding="utf-8",
    )

    preview = import_preview_local_dogfood_export(
        export_manifest_path=manifest_path,
        target_db_path=tmp_path / "local_dogfood" / "accurate_intake.sqlite3",
    )

    assert preview["status"] == "blocked"
    assert "export_format_not_sqlite_copy_with_manifest" in preview["blockers"]
    assert "export_manifest_missing_sqlite_copy_flag" in preview["blockers"]
    assert preview["writes_performed"] is False
    assert preview["import_allowed"] is False


def test_import_preview_rejects_export_manifest_without_sqlite_copy_path(tmp_path: Path) -> None:
    manifest_path = tmp_path / "exports" / "bad.manifest.json"
    manifest_path.parent.mkdir()
    manifest_path.write_text(
        json.dumps(
            {
                "operation": "export",
                "local_only": True,
                "do_not_commit": True,
                "contains_personal_diet_logs": True,
            }
        ),
        encoding="utf-8",
    )

    preview = import_preview_local_dogfood_export(
        export_manifest_path=manifest_path,
        target_db_path=tmp_path / "local_dogfood" / "accurate_intake.sqlite3",
    )

    assert preview["status"] == "blocked"
    assert "export_sqlite_copy_missing" in preview["blockers"]


def test_import_preview_rejects_export_copy_outside_allowed_local_roots(tmp_path: Path) -> None:
    manifest_path = tmp_path / "exports" / "outside-root.manifest.json"
    manifest_path.parent.mkdir()
    manifest_path.write_text(
        json.dumps(
            {
                "operation": "export",
                "local_only": True,
                "do_not_commit": True,
                "contains_personal_diet_logs": True,
                "export_format": "sqlite_copy_with_manifest",
                "export_contains_sqlite_copy": True,
                "export_path": "not_local_exports/unsafe.sqlite3",
            }
        ),
        encoding="utf-8",
    )

    preview = import_preview_local_dogfood_export(
        export_manifest_path=manifest_path,
        target_db_path=tmp_path / "local_dogfood" / "accurate_intake.sqlite3",
    )

    assert preview["status"] == "blocked"
    assert "source_export_path_outside_allowed_local_roots" in preview["blockers"]
    assert preview["writes_performed"] is False
    assert preview["import_allowed"] is False


def test_import_preview_rejects_export_copy_when_source_equals_target(tmp_path: Path) -> None:
    target_db = tmp_path / "local_dogfood" / "accurate_intake.sqlite3"
    target_db.parent.mkdir()
    target_db.write_bytes(b"sqlite bytes")
    manifest_path = tmp_path / "exports" / "same-target.manifest.json"
    manifest_path.parent.mkdir()
    manifest_path.write_text(
        json.dumps(
            {
                "operation": "export",
                "local_only": True,
                "do_not_commit": True,
                "contains_personal_diet_logs": True,
                "export_format": "sqlite_copy_with_manifest",
                "export_contains_sqlite_copy": True,
                "export_path": str(target_db),
            }
        ),
        encoding="utf-8",
    )

    preview = import_preview_local_dogfood_export(
        export_manifest_path=manifest_path,
        target_db_path=target_db,
    )

    assert preview["status"] == "blocked"
    assert "source_export_path_equals_target_db" in preview["blockers"]
    assert preview["target_exists"] is True


def test_import_preview_rejects_non_sqlite_export_copy(tmp_path: Path) -> None:
    text_copy = tmp_path / "exports" / "accurate_intake.txt"
    text_copy.parent.mkdir()
    text_copy.write_text("not sqlite", encoding="utf-8")
    manifest_path = tmp_path / "exports" / "not-sqlite.manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "operation": "export",
                "local_only": True,
                "do_not_commit": True,
                "contains_personal_diet_logs": True,
                "export_format": "sqlite_copy_with_manifest",
                "export_contains_sqlite_copy": True,
                "export_path": str(text_copy),
            }
        ),
        encoding="utf-8",
    )

    preview = import_preview_local_dogfood_export(
        export_manifest_path=manifest_path,
        target_db_path=tmp_path / "local_dogfood" / "accurate_intake.sqlite3",
    )

    assert preview["status"] == "blocked"
    assert "source_export_path_not_sqlite" in preview["blockers"]


def test_data_hygiene_cli_writes_inspection_manifest(tmp_path: Path) -> None:
    output_path = tmp_path / "hygiene.json"

    from scripts.manage_accurate_intake_local_dogfood_data import main

    exit_code = main(
        [
            "--operation",
            "inspect",
            "--db-path",
            str(tmp_path / "real_dogfood" / "accurate_intake.sqlite3"),
            "--output",
            str(output_path),
        ]
    )

    assert exit_code == 0
    manifest = json.loads(output_path.read_text(encoding="utf-8"))
    assert manifest["operation"] == "inspect"
    assert manifest["db_class"] == "real_dogfood_db"
    assert manifest["reset_without_backup_allowed"] is False


def test_data_hygiene_cli_blocks_export_dir_outside_local_roots(tmp_path: Path) -> None:
    db_path = tmp_path / "real_dogfood" / "accurate_intake.sqlite3"
    db_path.parent.mkdir()
    db_path.write_bytes(b"sqlite bytes")
    output_path = tmp_path / "blocked-export.json"

    from scripts.manage_accurate_intake_local_dogfood_data import main

    exit_code = main(
        [
            "--operation",
            "export",
            "--db-path",
            str(db_path),
            "--export-dir",
            "not_local_exports",
            "--output",
            str(output_path),
        ]
    )

    manifest = json.loads(output_path.read_text(encoding="utf-8"))
    assert exit_code == 1
    assert manifest["status"] == "blocked"
    assert "export_dir_outside_allowed_local_roots" in manifest["blockers"]


def test_self_use_runbook_documents_export_and_import_preview_commands() -> None:
    runbook = Path("docs/quality/ACCURATE_INTAKE_MVP_SELF_USE_RUNBOOK.md").read_text(encoding="utf-8-sig")

    assert "--operation export" in runbook
    assert "--operation import-preview" in runbook
    assert "workspace_data/local_dogfood_exports" in runbook
    assert "local-only SQLite copy plus manifest" in runbook
    assert "db_exists" in runbook
    assert "db_size_bytes" in runbook
    assert "db_modified_at_utc" in runbook
