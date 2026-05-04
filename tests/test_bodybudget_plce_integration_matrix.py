from __future__ import annotations

from importlib import import_module
from pathlib import Path


MATRIX_PATH = Path("docs/specs/UI_CANONICAL_TRUTH_SURFACE_MATRIX.md")
ROOT_ROUTES_PATH = Path("app/routes.py")


def _resolve_symbol(dotted_path: str) -> object:
    module_name, symbol_name = dotted_path.rsplit(".", 1)
    return getattr(import_module(module_name), symbol_name)


def test_bodybudget_plce_integration_matrix_names_backend_read_models_and_routes() -> None:
    matrix = MATRIX_PATH.read_text(encoding="utf-8-sig")

    assert "## BodyBudget PL/CE Integration Readiness Matrix" in matrix
    expected_contracts = {
        "current_budget_view": [
            "/today/current-budget",
            "app.composition.current_budget_read_model.build_current_budget_view",
            "budget_kcal",
            "consumed_kcal",
            "remaining_kcal",
        ],
        "body_budget_deficit_summary": [
            "/today/deficit-summary",
            "app.composition.body_budget_deficit_summary.build_body_budget_deficit_summary",
            "`deficit_summary` is shorthand only",
            "active_daily_target_kcal",
            "estimated_daily_deficit_kcal",
            "latest_weight_kg",
        ],
        "active_body_plan_view": [
            "/body-plan/active",
            "app.body.application.active_body_plan_read_model.build_active_body_plan_view",
            "daily_budget_kcal",
            "recommended_target_kcal",
            "estimated_tdee",
        ],
        "calibration_proposal_inbox": [
            "/calibration/proposals/open",
            "root app mount deferred until activation plan",
            "app.composition.calibration_proposal_inbox.load_open_calibration_proposal_inbox",
            "proposal_container_id",
            "proposal_status",
            "options[].effect_payload",
        ],
    }

    for read_model_name, required_tokens in expected_contracts.items():
        assert read_model_name in matrix
        for token in required_tokens:
            assert token in matrix


def test_bodybudget_plce_integration_matrix_keeps_plce_render_only() -> None:
    matrix = MATRIX_PATH.read_text(encoding="utf-8-sig")

    assert "PL/CE may render, group, collapse, or label supplied values" in matrix
    assert "must not calculate BodyBudget truth" in matrix
    assert "must preserve backend-provided proposal order" in matrix
    assert "option `rank_order`, `is_primary`, and `proposal_status`" in matrix
    forbidden_tokens = [
        "Do not recompute consumed, remaining",
        "Do not calculate TDEE, target kcal, remaining kcal",
        "Do not run BMR/TDEE formulas",
        "do not create, rank, rewrite, accept, defer, or reject proposals",
        "does not add fields to `ManagerContextPacket`",
    ]
    for token in forbidden_tokens:
        assert token in matrix


def test_bodybudget_plce_integration_matrix_references_importable_backend_read_models() -> None:
    for dotted_path in [
        "app.composition.current_budget_read_model.build_current_budget_view",
        "app.composition.body_budget_deficit_summary.build_body_budget_deficit_summary",
        "app.body.application.active_body_plan_read_model.build_active_body_plan_view",
        "app.composition.calibration_proposal_inbox.load_open_calibration_proposal_inbox",
    ]:
        assert callable(_resolve_symbol(dotted_path))


def test_bodybudget_plce_integration_matrix_tracks_calibration_router_activation_status() -> None:
    matrix = MATRIX_PATH.read_text(encoding="utf-8-sig")
    root_routes = ROOT_ROUTES_PATH.read_text(encoding="utf-8")
    calibration_router = _resolve_symbol("app.composition.calibration_routes.router")
    calibration_paths = {route.path for route in calibration_router.routes}

    assert "/calibration/proposals/open" in calibration_paths
    assert "/calibration/proposal/stored-action" in calibration_paths
    assert "calibration_routes" not in root_routes
    assert "root app mount deferred until activation plan" in matrix
    assert "do not mount into the root app without a separate activation plan" in matrix


def test_bodybudget_plce_integration_matrix_distinguishes_proposal_route_projection() -> None:
    matrix = MATRIX_PATH.read_text(encoding="utf-8-sig")
    proposal_container = _resolve_symbol("app.shared.domain.ProposalContainer")

    assert "Route projection fields:" in matrix
    assert "Read function domain fields:" in matrix
    assert "metadata-derived fields are not direct read-function fields" in matrix
    assert "metadata" in proposal_container.model_fields
    assert "local_date" not in proposal_container.model_fields
    assert "proposal_family" not in proposal_container.model_fields
