from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROTECTED_MAINLINE_FILES = [
    "app/routes.py",
    "app/schemas.py",
    "app/usecases/text_meal.py",
]
ACTIVE_MAINLINE_FILES = [
    "app/routes.py",
    "app/schemas.py",
    "app/models.py",
    "app/composition/intake_routes.py",
    "app/composition/v2_routes.py",
    "app/composition/intake_turn_orchestrator.py",
    "app/composition/intake_execution_orchestrator.py",
    "app/runtime/application/manager_service.py",
    "app/composition/intake_manager_tool_batch.py",
    "app/runtime/interface/provider_runtime.py",
]
PRODUCT_LAB_TOKENS = [
    "advanced_shadow_lab.product_lab",
    "advanced_product_lab",
    "product_lab_",
]


def test_product_lab_is_not_mounted_by_protected_mainline_surfaces() -> None:
    for relative in PROTECTED_MAINLINE_FILES:
        path = ROOT / relative
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        assert "advanced_shadow_lab.product_lab" not in text
        assert "product_lab_" not in text


def test_product_lab_is_not_imported_by_active_runtime_or_migrations() -> None:
    for relative in ACTIVE_MAINLINE_FILES:
        path = ROOT / relative
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8-sig")
        for token in PRODUCT_LAB_TOKENS:
            assert token not in text, relative

    for path in (ROOT / "alembic" / "versions").glob("*.py"):
        text = path.read_text(encoding="utf-8-sig")
        for token in PRODUCT_LAB_TOKENS:
            assert token not in text, path.name


def test_product_lab_full_loop_closure_does_not_claim_mainline_activation(
    tmp_path: Path,
) -> None:
    from app.advanced_shadow_lab.product_lab_calibration_fixture_inputs import (
        build_product_lab_calibration_fixture_inputs,
    )
    from app.advanced_shadow_lab.product_lab_session_replay import (
        run_advanced_product_lab_dogfood_session,
    )
    from app.advanced_shadow_lab.product_lab_simulated_scenario import (
        build_product_lab_simulated_turns,
    )
    from app.advanced_shadow_lab.product_lab_simulated_summary import (
        build_simulated_dogfood_summary,
    )

    session_artifact = run_advanced_product_lab_dogfood_session(
        artifact_root=tmp_path,
        session_id="activation-wall-full-loop",
        fixture_inputs=build_product_lab_calibration_fixture_inputs(),
        turns=build_product_lab_simulated_turns(),
    )
    summary = build_simulated_dogfood_summary(session_artifact)

    assert summary["advanced_product_lab_product_loop_closed"] is True
    assert summary["lab_user_facing_behavior_changed"] is True
    assert summary["user_facing_behavior_changed"] is False
    assert summary["mainline_runtime_connected"] is False
    assert summary["mainline_activation_enabled"] is False
    assert summary["production_scheduler_delivery_allowed"] is False
    assert summary["production_db_migration_allowed"] is False
    assert summary["canonical_product_mutation_allowed"] is False
    assert summary["product_readiness_claimed"] is False


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
