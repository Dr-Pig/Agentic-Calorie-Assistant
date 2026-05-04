from __future__ import annotations

import json
from pathlib import Path

from app.composition.local_dogfood_data_hygiene import export_local_dogfood_db


def test_local_operator_data_hygiene_bundle_summarizes_real_db_without_writes(tmp_path: Path) -> None:
    from app.composition.accurate_intake_local_operator_data_hygiene_bundle import (
        build_local_operator_data_hygiene_bundle,
    )

    db_path = tmp_path / "real_dogfood" / "accurate_intake.sqlite3"
    db_path.parent.mkdir()
    db_path.write_bytes(b"sqlite bytes")
    backup_dir = tmp_path / "backups"
    export_dir = tmp_path / "exports"

    bundle = build_local_operator_data_hygiene_bundle(
        db_path=db_path,
        backup_dir=backup_dir,
        export_dir=export_dir,
    )

    assert bundle["artifact_type"] == "accurate_intake_local_operator_data_hygiene_bundle"
    assert bundle["status"] == "local_operator_data_hygiene_ready"
    assert bundle["local_only"] is True
    assert bundle["contains_personal_diet_logs"] is True
    assert bundle["do_not_commit"] is True
    assert bundle["writes_performed"] is False
    assert bundle["backup_required_before_reset"] is True
    assert bundle["reset_without_backup_allowed"] is False
    assert bundle["operation_previews"]["reset_guard"]["allowed"] is False
    assert bundle["operation_previews"]["reset_guard"]["blockers"] == ["backup_required_before_reset"]
    assert bundle["operation_previews"]["backup"]["would_write_copy"] is True
    assert bundle["operation_previews"]["export"]["would_write_copy"] is True
    assert bundle["operation_previews"]["import_preview"]["status"] == "not_checked"
    assert bundle["operation_previews"]["import_preview"]["import_allowed"] is False
    assert bundle["operation_previews"]["import_preview"]["writes_performed"] is False
    assert backup_dir.exists() is False
    assert export_dir.exists() is False


def test_local_operator_data_hygiene_bundle_keeps_fixture_db_disposable(tmp_path: Path) -> None:
    from app.composition.accurate_intake_local_operator_data_hygiene_bundle import (
        build_local_operator_data_hygiene_bundle,
    )

    db_path = tmp_path / ".pytest_tmp_local" / "accurate_intake_browser_shell_smoke.sqlite3"
    db_path.parent.mkdir()
    db_path.write_bytes(b"sqlite bytes")

    bundle = build_local_operator_data_hygiene_bundle(db_path=db_path)

    assert bundle["status"] == "local_operator_data_hygiene_ready"
    assert bundle["db_class"] == "fixture_smoke_db"
    assert bundle["contains_personal_diet_logs"] is False
    assert bundle["backup_required_before_reset"] is False
    assert bundle["reset_without_backup_allowed"] is True
    assert bundle["operation_previews"]["reset_guard"]["allowed"] is True
    assert bundle["fooddb_truth_updated"] is False
    assert bundle["production_db_used"] is False
    assert bundle["live_llm_invoked"] is False
    assert bundle["web_tavily_used"] is False
    assert bundle["private_self_use_approved"] is False


def test_local_operator_data_hygiene_bundle_import_preview_reads_manifest_without_importing(
    tmp_path: Path,
) -> None:
    from app.composition.accurate_intake_local_operator_data_hygiene_bundle import (
        build_local_operator_data_hygiene_bundle,
    )

    source_db = tmp_path / "real_dogfood" / "accurate_intake.sqlite3"
    source_db.parent.mkdir()
    source_db.write_bytes(b"sqlite bytes")
    export_report = export_local_dogfood_db(
        db_path=source_db,
        export_dir=tmp_path / "exports",
        label="review",
    )
    target_db = tmp_path / "local_dogfood" / "accurate_intake.sqlite3"

    bundle = build_local_operator_data_hygiene_bundle(
        db_path=target_db,
        import_manifest_path=Path(export_report["manifest_path"]),
    )

    import_preview = bundle["operation_previews"]["import_preview"]
    assert bundle["status"] == "local_operator_data_hygiene_ready"
    assert import_preview["status"] == "pass"
    assert import_preview["import_allowed"] is False
    assert import_preview["writes_performed"] is False
    assert target_db.exists() is False


def test_local_operator_data_hygiene_bundle_blocks_invalid_import_preview(tmp_path: Path) -> None:
    from app.composition.accurate_intake_local_operator_data_hygiene_bundle import (
        build_local_operator_data_hygiene_bundle,
    )

    bad_manifest = tmp_path / "exports" / "bad.manifest.json"
    bad_manifest.parent.mkdir()
    bad_manifest.write_text("{not json", encoding="utf-8")

    bundle = build_local_operator_data_hygiene_bundle(
        db_path=tmp_path / "local_dogfood" / "accurate_intake.sqlite3",
        import_manifest_path=bad_manifest,
    )

    assert bundle["status"] == "blocked"
    assert "import_preview.export_manifest_invalid_json" in bundle["blockers"]
    assert bundle["operation_previews"]["import_preview"]["writes_performed"] is False
    assert bundle["operation_previews"]["import_preview"]["import_allowed"] is False


def test_local_operator_data_hygiene_bundle_cli_writes_artifact(tmp_path: Path, capsys) -> None:
    from scripts import build_accurate_intake_local_operator_data_hygiene_bundle as module

    db_path = tmp_path / "real_dogfood" / "accurate_intake.sqlite3"
    db_path.parent.mkdir()
    db_path.write_bytes(b"sqlite bytes")
    output_path = tmp_path / "operator-hygiene.json"

    exit_code = module.main(
        [
            "--db-path",
            str(db_path),
            "--backup-dir",
            str(tmp_path / "backups"),
            "--export-dir",
            str(tmp_path / "exports"),
            "--output",
            str(output_path),
        ]
    )
    printed = json.loads(capsys.readouterr().out)
    artifact = json.loads(output_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert artifact == printed
    assert artifact["status"] == "local_operator_data_hygiene_ready"
    assert artifact["writes_performed"] is False


def test_local_operator_data_hygiene_bundle_stays_out_of_fooddb_websearch_and_live_boundaries() -> None:
    source_paths = [
        Path("app/composition/accurate_intake_local_operator_data_hygiene_bundle.py"),
        Path("scripts/build_accurate_intake_local_operator_data_hygiene_bundle.py"),
    ]

    for source_path in source_paths:
        source = source_path.read_text(encoding="utf-8")
        for fragment in (
            "NutritionEvidenceStorePort",
            "FoodEvidenceRecord",
            "PacketReadyAnchor",
            "TavilyClient",
            "BuilderSpaceAdapter",
            "builderspace_adapter",
            "kimi",
            "grok",
        ):
            assert fragment not in source
