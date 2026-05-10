from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROTECTED_MAINLINE_FILES = [
    "app/routes.py",
    "app/schemas.py",
    "app/usecases/text_meal.py",
]


def test_product_lab_is_not_mounted_by_protected_mainline_surfaces() -> None:
    for relative in PROTECTED_MAINLINE_FILES:
        path = ROOT / relative
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        assert "advanced_shadow_lab.product_lab" not in text
        assert "product_lab_" not in text


def test_product_lab_keeps_merge_back_activation_wall_flags() -> None:
    from app.advanced_shadow_lab.product_lab_fixture_inputs import (
        build_product_lab_fixture_inputs,
    )
    from app.advanced_shadow_lab.product_lab_runtime import run_advanced_product_lab_turn
    from tests.test_advanced_product_lab_runtime import _turn

    artifact = run_advanced_product_lab_turn(
        lab_mode="isolated_advanced_product_lab",
        turn=_turn("activation-wall-turn"),
        fixture_inputs=build_product_lab_fixture_inputs(),
    )

    assert artifact["full_product_lab_runtime_enabled"] is True
    assert artifact["lab_user_facing_behavior_changed"] is True
    assert artifact["merge_back_activation_wall"] == {
        "mainline_activation_requires_separate_pr": True,
        "self_use_v1_route_or_startup_changed": False,
        "mainline_runtime_connected": False,
        "mainline_route_or_api_mount_allowed": False,
        "production_scheduler_delivery_allowed": False,
        "production_db_migration_allowed": False,
        "canonical_product_mutation_allowed": False,
        "manager_context_packet_changed": False,
    }
    assert artifact["user_facing_behavior_changed"] is False
    assert artifact["production_db_migration_allowed"] is False
    assert artifact["canonical_product_mutation_allowed"] is False
