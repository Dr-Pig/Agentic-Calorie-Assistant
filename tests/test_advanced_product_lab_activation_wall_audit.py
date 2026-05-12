from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact


ROOT = Path(__file__).resolve().parents[1]


def test_activation_wall_audit_passes_for_current_mainline_repo() -> None:
    from app.advanced_shadow_lab.product_lab_activation_wall_audit import (
        build_product_lab_activation_wall_audit,
    )

    audit = build_product_lab_activation_wall_audit(
        closure_pack=_closure_pack(),
        repo_root=ROOT,
    )

    assert audit["artifact_type"] == "advanced_product_lab_activation_wall_audit"
    assert audit["status"] == "pass"
    assert audit["lab_enabled"] is True
    assert audit["mainline_activation_enabled"] is False
    assert audit["mainline_runtime_connected"] is False
    assert audit["self_use_v1_affected"] is False
    assert audit["route_mount_clear"] is True
    assert audit["scheduler_delivery_clear"] is True
    assert audit["production_db_migration_clear"] is True
    assert audit["provider_default_runtime_clear"] is True
    assert audit["blockers"] == []


def test_activation_wall_audit_blocks_route_lab_and_migration_leaks(
    tmp_path: Path,
) -> None:
    from app.advanced_shadow_lab.product_lab_activation_wall_audit import (
        build_product_lab_activation_wall_audit,
    )

    _write(tmp_path / "app" / "routes.py", "from app.advanced_shadow_lab import x\n")
    _write(
        tmp_path / "app" / "advanced_shadow_lab" / "leak.py",
        "from app.database import get_db\nAPIRouter()\n",
    )
    _write(tmp_path / "alembic" / "versions" / "001_advanced_product_lab.py", "")

    audit = build_product_lab_activation_wall_audit(
        closure_pack={**_closure_pack(), "mainline_activation_enabled": True},
        repo_root=tmp_path,
    )

    assert audit["status"] == "blocked"
    assert audit["next_allowed_slices"] == []
    assert audit["blockers"] == [
        "closure_pack.mainline_activation_enabled.claim_drift",
        "active_runtime_surface.app/routes.py.references_advanced_shadow_lab",
        "advanced_lab.app/advanced_shadow_lab/leak.py.contains_APIRouter",
        "advanced_lab.app/advanced_shadow_lab/leak.py.imports_app.database",
        "migration.001_advanced_product_lab.py",
    ]


def test_activation_wall_audit_cli_writes_repo_scan_artifact(tmp_path: Path) -> None:
    closure_path = tmp_path / "closure.json"
    output = tmp_path / "activation-wall.json"
    write_json_artifact(closure_path, _closure_pack())

    result = subprocess.run(
        [
            sys.executable,
            "scripts/build_advanced_product_lab_activation_wall_audit.py",
            "--closure-pack-json",
            str(closure_path),
            "--output",
            str(output),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    stdout_audit = json.loads(result.stdout)
    file_audit = read_json_artifact(output)
    assert stdout_audit == file_audit
    assert file_audit["status"] == "pass"
    assert file_audit["source_closure_pack_path"] == str(closure_path)


def _closure_pack(**overrides: object) -> dict[str, object]:
    pack: dict[str, object] = {
        "artifact_type": "advanced_product_lab_memory_record_closure_pack",
        "status": "pass",
        "lab_enabled": True,
        "lab_product_loop_closed": True,
        "mainline_activation_enabled": False,
        "mainline_runtime_connected": False,
        "self_use_v1_affected": False,
        "durable_product_memory_written": False,
        "canonical_product_mutation_allowed": False,
        "production_scheduler_delivery_allowed": False,
        "blockers": [],
    }
    pack.update(overrides)
    return pack


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
