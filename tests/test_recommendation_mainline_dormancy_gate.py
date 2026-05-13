from __future__ import annotations

from pathlib import Path

from app.advanced_shadow_lab.recommendation_mainline_dormancy_gate import (
    build_recommendation_mainline_dormancy_gate,
)


ROOT = Path(__file__).resolve().parents[1]


def test_recommendation_mainline_dormancy_gate_passes_for_current_repo() -> None:
    gate = build_recommendation_mainline_dormancy_gate(
        quality_decision_pack=_quality_pack(),
        repo_root=ROOT,
    )

    assert gate["artifact_type"] == "advanced_product_lab_recommendation_mainline_dormancy_gate"
    assert gate["status"] == "pass"
    assert gate["quality_decision_pack_ready"] is True
    assert gate["route_mount_clear"] is True
    assert gate["scheduler_delivery_clear"] is True
    assert gate["production_db_migration_clear"] is True
    assert gate["provider_default_runtime_clear"] is True
    assert gate["ready_for_recommendation_train_closeout"] is True
    assert gate["ready_for_mainline_activation"] is False
    assert gate["mainline_activation_enabled"] is False
    assert gate["canonical_product_mutation_allowed"] is False
    assert gate["blockers"] == []


def test_recommendation_mainline_dormancy_gate_blocks_quality_or_mainline_leaks(
    tmp_path: Path,
) -> None:
    _write(tmp_path / "app" / "routes.py", "recommendation.run\n")
    _write(
        tmp_path / "app" / "runtime" / "application" / "manager_service.py",
        "from app.advanced_shadow_lab.recommendation_quality_decision_pack import x\n",
    )
    _write(
        tmp_path / "alembic" / "versions" / "001_advanced_product_lab_recommendation.py",
        "",
    )

    gate = build_recommendation_mainline_dormancy_gate(
        quality_decision_pack={**_quality_pack(), "mainline_activation_enabled": True},
        repo_root=tmp_path,
    )

    assert gate["status"] == "blocked"
    assert gate["ready_for_recommendation_train_closeout"] is False
    assert gate["ready_for_mainline_activation"] is False
    assert gate["blockers"] == [
        "quality_decision_pack.mainline_activation_enabled",
        "active_runtime_surface.app/routes.py.references_recommendation_lab",
        (
            "active_runtime_surface.app/runtime/application/manager_service.py."
            "references_recommendation_lab"
        ),
        "migration.001_advanced_product_lab_recommendation.py",
    ]


def test_recommendation_train_records_pr23_completion_and_next_active_slice() -> None:
    import yaml

    with open(
        "docs/quality/advanced_product_lab_recommendation_pr_train.yaml",
        encoding="utf-8-sig",
    ) as handle:
        plan = yaml.safe_load(handle)

    assert plan["dynamic_remaining_pr_count"] == 1
    assert plan["last_completed_pr_number"] == 23
    assert plan["active_pr_number"] == 24
    assert plan["last_merge_evidence"]["completed_prs"][-1] == {
        "pr_number": 23,
        "pull_request": "local_logical_slice",
        "merge_commit": "working_branch_uncommitted",
        "result": "recommendation_mainline_dormancy_gate_completed_locally",
    }


def _quality_pack() -> dict[str, object]:
    return {
        "artifact_type": "advanced_product_lab_recommendation_quality_decision_pack",
        "status": "pass",
        "ready_for_recommendation_mainline_dormancy_gate": True,
        "ready_for_mainline_activation": False,
        "mainline_activation_enabled": False,
        "mainline_runtime_connected": False,
        "self_use_v1_affected": False,
        "canonical_product_mutation_allowed": False,
        "durable_product_memory_written": False,
        "manager_context_packet_changed": False,
        "production_scheduler_delivery_allowed": False,
        "blockers": [],
    }


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
