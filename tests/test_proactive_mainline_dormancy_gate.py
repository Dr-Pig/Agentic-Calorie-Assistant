from __future__ import annotations

from pathlib import Path

import yaml

from app.advanced_shadow_lab.proactive_mainline_dormancy_gate import (
    build_proactive_mainline_dormancy_gate,
)


ROOT = Path(__file__).resolve().parents[1]


def test_proactive_mainline_dormancy_gate_passes_for_current_repo() -> None:
    gate = build_proactive_mainline_dormancy_gate(
        proactive_pr_train=_train(),
        repo_root=ROOT,
    )

    assert gate["artifact_type"] == "advanced_product_lab_proactive_mainline_dormancy_gate"
    assert gate["status"] == "pass"
    assert gate["proactive_train_ready"] is True
    assert gate["route_mount_clear"] is True
    assert gate["scheduler_delivery_clear"] is True
    assert gate["production_db_migration_clear"] is True
    assert gate["durable_memory_activation_clear"] is True
    assert gate["ready_for_proactive_train_closeout"] is True
    assert gate["ready_for_mainline_activation"] is False
    assert gate["mainline_activation_enabled"] is False
    assert gate["canonical_product_mutation_allowed"] is False
    assert gate["blockers"] == []


def test_proactive_mainline_dormancy_gate_blocks_route_migration_or_flag_leaks(
    tmp_path: Path,
) -> None:
    _write(tmp_path / "app" / "routes.py", "proactive.run\n")
    _write(
        tmp_path / "app" / "runtime" / "application" / "manager_service.py",
        "from app.advanced_shadow_lab.product_lab_proactive import run\n",
    )
    _write(
        tmp_path / "alembic" / "versions" / "001_advanced_product_lab_proactive.py",
        "",
    )
    train = _train()
    train["required_artifact_flags"]["production_scheduler_delivery_allowed"] = True

    gate = build_proactive_mainline_dormancy_gate(
        proactive_pr_train=train,
        repo_root=tmp_path,
    )

    assert gate["status"] == "blocked"
    assert gate["ready_for_proactive_train_closeout"] is False
    assert gate["ready_for_mainline_activation"] is False
    assert gate["blockers"] == [
        "proactive_pr_train.required_artifact_flags.production_scheduler_delivery_allowed",
        "active_runtime_surface.app/routes.py.references_proactive_lab",
        (
            "active_runtime_surface.app/runtime/application/manager_service.py."
            "references_proactive_lab"
        ),
        "migration.001_advanced_product_lab_proactive.py",
    ]


def _train() -> dict[str, object]:
    with open(
        "docs/quality/advanced_product_lab_proactive_chat_first_pr_train.yaml",
        encoding="utf-8-sig",
    ) as handle:
        return dict(yaml.safe_load(handle))


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
