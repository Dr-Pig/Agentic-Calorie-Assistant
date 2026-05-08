from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.composition.body_budget_calibration_readiness_flow import (
    build_calibration_flow_contract,
)
from app.composition.body_budget_calibration_readiness_read_models import (
    build_body_budget_stable_read_models,
)
from app.composition.body_budget_calibration_readiness_shell import (
    build_journey_smoke_gates,
    build_non_claims,
    build_route_activation_contract,
    build_runtime_truth_changed_contract,
)
from app.shared.contracts.readiness_claim import build_readiness_claim


def _readiness_claim() -> dict[str, Any]:
    return build_readiness_claim(
        claim_scope="unit_contract",
        activation_stage="contract",
        semantic_authority_source="deterministic_validator",
        producer_honesty={
            "runner_inferred_semantics": False,
            "final_mapping_fabricated": False,
            "mutation_fabricated": False,
            "frontend_math_authorized": False,
        },
        evidence_lineage={
            "producers": [
                "app.composition.body_budget_calibration_readiness."
                "build_body_budget_calibration_readiness_artifact",
            ],
            "artifacts": [
                "docs/specs/UI_CANONICAL_TRUTH_SURFACE_MATRIX.md#BodyBudget CurrentShell Integration Readiness Matrix",
            ],
        },
        allowed_next_stage="calibration_acceptance_chat_surface_or_rescue_overlay_foundation",
        forbidden_claims=[
            "product_ready",
            "private_self_use_approved",
            "web_ready",
            "automatic_calibration_enabled",
            "recommendation_enabled",
            "rescue_enabled",
            "proactive_enabled",
            "mutation_ready",
        ],
        readiness_claimed=False,
    )


def _integration_readiness_matrix(stable_read_models: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "doc_path": (
            "docs/specs/UI_CANONICAL_TRUTH_SURFACE_MATRIX.md"
            "#BodyBudget CurrentShell Integration Readiness Matrix"
        ),
        "canonical_read_model_names": [read_model["name"] for read_model in stable_read_models],
        "backend_routes": {read_model["name"]: read_model["backend_route"] for read_model in stable_read_models},
        "read_functions": {read_model["name"]: read_model["read_function"] for read_model in stable_read_models},
        "frontend_fallback_calculation_authorized": False,
        "manager_context_packet_changed": False,
        "missing_field_policy": "extend_backend_read_model_first",
    }


def _current_shell_contract(stable_read_models: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "stable_backend_read_models_required": True,
        "frontend_math_allowed": False,
        "context_engineering_summary_requires_separate_contract": True,
        "manager_context_packet_changed": False,
        "deficit_summary_official_name": "body_budget_deficit_summary",
        "deficit_summary_alias_role": "shorthand_only",
        "proposal_inbox_order_owned_by_backend": True,
        "integration_readiness_matrix": _integration_readiness_matrix(stable_read_models),
    }


def build_body_budget_calibration_readiness_artifact() -> dict[str, Any]:
    stable_read_models = build_body_budget_stable_read_models()
    return {
        "artifact_schema_version": "body_budget_calibration_readiness.v1",
        "artifact_type": "body_budget_calibration_readiness",
        "status": "ok",
        "generated_at": datetime.now(UTC).isoformat(),
        "claim_scope": "local_body_budget_calibration_contract",
        "local_only": True,
        "diagnostic_only": True,
        "readiness_claimed": False,
        "readiness_claim": _readiness_claim(),
        "stable_read_models": stable_read_models,
        "current_shell_contract": _current_shell_contract(stable_read_models),
        "calibration_flow_contract": build_calibration_flow_contract(),
        "route_activation": build_route_activation_contract(),
        "journey_smoke_gates": build_journey_smoke_gates(),
        "runtime_truth_changed": build_runtime_truth_changed_contract(),
        "non_claims": build_non_claims(),
    }


__all__ = ["build_body_budget_calibration_readiness_artifact"]
