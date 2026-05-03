from __future__ import annotations

import json
from pathlib import Path

from app.composition.local_dogfood_data_hygiene import (
    backup_local_dogfood_db,
    build_local_dogfood_data_manifest,
    classify_local_dogfood_db,
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
    assert manifest["backup_path"] == str(backup_path)


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
