from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.composition.calibration_commit_bridge import PLAN_CHANGING_CALIBRATION_FAMILIES
from app.composition.calibration_proposal_artifacts import ACTIVE_CALIBRATION_PROPOSAL_STATUSES
from app.shared.contracts.readiness_claim import build_readiness_claim


_TERMINAL_CALIBRATION_PROPOSAL_STATUSES = [
    "accepted",
    "rejected",
    "deferred_pending_reminder",
    "expired",
    "dismissed",
]


def _stable_read_models() -> list[dict[str, Any]]:
    return [
        {
            "name": "current_budget_view",
            "aliases": [],
            "canonical_name_required_for_plce": True,
            "backend_route": "/today/current-budget",
            "read_function": "app.composition.current_budget_read_model.build_current_budget_view",
            "truth_owner": ["budget", "intake"],
            "stable_fields": [
                "budget_kcal",
                "consumed_kcal",
                "adjustment_kcal",
                "remaining_kcal",
                "active_meal_count",
                "meals",
                "show_macro",
                "macro_guard_reason",
                "last_recomputed_at",
            ],
            "plce_allowed_use": "render_supplied_values_only",
            "plce_forbidden": [
                "recompute_consumed",
                "recompute_remaining",
                "recompute_adjustment_sign",
                "derive_macro_visibility",
            ],
        },
        {
            "name": "body_budget_deficit_summary",
            "aliases": ["deficit_summary"],
            "canonical_name_required_for_plce": True,
            "backend_route": "/today/deficit-summary",
            "read_function": "app.composition.body_budget_deficit_summary.build_body_budget_deficit_summary",
            "truth_owner": ["body", "budget", "composition_read_model"],
            "stable_fields": [
                "source_kind",
                "read_only",
                "truth_owner",
                "target_available",
                "target_source",
                "active_daily_target_kcal",
                "recommended_target_kcal",
                "consumed_kcal",
                "adjustment_kcal",
                "remaining_kcal",
                "estimated_daily_deficit_kcal",
                "latest_weight_kg",
                "latest_weight_observed_at",
                "latest_weight_observation_id",
                "weight_history_count",
                "current_budget",
                "active_body_plan",
            ],
            "plce_allowed_use": "render_deficit_observation_loop_from_backend_values",
            "plce_forbidden": [
                "calculate_tdee",
                "calculate_target_kcal",
                "calculate_remaining_kcal",
                "calculate_estimated_deficit",
                "select_latest_weight",
                "infer_target_source_legality",
            ],
        },
        {
            "name": "active_body_plan_view",
            "aliases": [],
            "canonical_name_required_for_plce": True,
            "backend_route": "/body-plan/active",
            "read_function": "app.body.application.active_body_plan_read_model.build_active_body_plan_view",
            "truth_owner": ["body"],
            "stable_fields": [
                "body_plan_id",
                "plan_status",
                "goal_type",
                "current_weight_kg",
                "target_weight_kg",
                "daily_budget_kcal",
                "recommended_target_kcal",
                "daily_deficit_kcal",
                "safety_floor_kcal",
                "estimated_tdee",
                "target_pace_kg_per_week",
                "plan_source",
                "profile_status",
                "last_updated_at",
            ],
            "plce_allowed_use": "render_active_body_plan_backend_values",
            "plce_forbidden": [
                "run_bmr_formula",
                "run_tdee_formula",
                "infer_manual_override_legality",
                "treat_profile_weight_as_latest_observation",
            ],
        },
        {
            "name": "calibration_proposal_inbox",
            "aliases": [],
            "canonical_name_required_for_plce": True,
            "backend_route": "/calibration/proposals/open",
            "read_function": "app.composition.calibration_proposal_inbox.load_open_calibration_proposal_inbox",
            "truth_owner": ["calibration_proposal_artifacts"],
            "stable_fields": [
                "proposal_container_id",
                "proposal_type",
                "proposal_status",
                "top_option_id",
                "local_date",
                "proposal_family",
                "created_at",
                "accepted_at",
                "options[].proposal_option_id",
                "options[].option_type",
                "options[].option_label",
                "options[].option_summary",
                "options[].rank_order",
                "options[].is_primary",
                "options[].effect_payload",
            ],
            "plce_allowed_use": "render_inbox_mirror_preserving_backend_order",
            "plce_forbidden": [
                "create_proposals",
                "rank_proposals",
                "rewrite_options",
                "expose_full_diagnostic_metadata",
                "accept_defer_reject_outside_stored_action",
            ],
        },
    ]


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
                "docs/specs/UI_CANONICAL_TRUTH_SURFACE_MATRIX.md#BodyBudget PL/CE Integration Readiness Matrix",
            ],
        },
        allowed_next_stage="pl_ce_render_contract_or_weekly_progress_read_model",
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


def build_body_budget_calibration_readiness_artifact() -> dict[str, Any]:
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
        "stable_read_models": _stable_read_models(),
        "plce_contract": {
            "stable_backend_read_models_required": True,
            "frontend_math_allowed": False,
            "context_engineering_summary_requires_separate_contract": True,
            "manager_context_packet_changed": False,
            "deficit_summary_official_name": "body_budget_deficit_summary",
            "deficit_summary_alias_role": "shorthand_only",
            "proposal_inbox_order_owned_by_backend": True,
        },
        "calibration_flow_contract": {
            "input_assembler": {
                "service": "app.composition.calibration_input_assembler."
                "assemble_calibration_model_inputs_from_history",
                "input_source": "real_body_intake_budget_history",
                "window_policy": "local_date_window_inclusive_end",
                "weight_delta_policy": "first_valid_then_last_valid_ordered_by_observed_at_then_id",
                "intake_coverage_policy": "weak_proxy_days_with_completed_meal_over_window_days",
                "llm_role": "none",
            },
            "preview_from_history": {
                "service": "app.composition.calibration_preview_service.build_calibration_preview_from_history",
                "input_source": "real_body_intake_budget_history",
                "manual_model_inputs_payload_role": "diagnostic_only",
                "persist_proposal_default": False,
                "persist_proposal_requires": [
                    "explicit_persist_proposal_true",
                    "proposal_eligible_and_surfaced",
                    "clean_sqlalchemy_session",
                    "no_existing_active_calibration_proposal",
                ],
                "body_plan_mutation_authorized": False,
                "day_budget_ledger_mutation_authorized": False,
                "ledger_entry_calibration_adjustment_enabled": False,
                "llm_role": "none",
            },
            "proposal_inbox": {
                "service": "app.composition.calibration_proposal_inbox.load_open_calibration_proposal_inbox",
                "active_statuses": sorted(ACTIVE_CALIBRATION_PROPOSAL_STATUSES),
                "mirror_only": True,
                "preserve_backend_order": True,
            },
            "stored_action": {
                "service": "app.composition.calibration_commit_bridge.apply_stored_calibration_proposal_action",
                "mutation_requires": "explicit_accept_on_active_stored_proposal",
                "active_statuses": sorted(ACTIVE_CALIBRATION_PROPOSAL_STATUSES),
                "terminal_statuses": _TERMINAL_CALIBRATION_PROPOSAL_STATUSES,
                "conflict_status_code": 409,
                "plan_changing_families": sorted(PLAN_CHANGING_CALIBRATION_FAMILIES),
                "body_plan_mutation_authorized_on_accept": True,
                "day_budget_ledger_refresh_authorized_on_accept": True,
                "ledger_entry_calibration_adjustment_enabled": False,
                "llm_role": "none",
            },
        },
        "route_activation": {
            "root_app_mounted": True,
            "root_mount_status": "activated_for_calibration_contract_routes",
            "router_module": "app.composition.calibration_routes.public_router",
            "router_contract_paths": [
                "/calibration/proposals/open",
                "/calibration/proposal/preview-from-history",
                "/calibration/proposal/stored-action",
            ],
            "internal_diagnostic_paths_not_root_mounted": [
                "/calibration/proposal/preview",
                "/calibration/proposal/action",
            ],
            "frontend_route_call_allowed_after_activation": True,
        },
        "runtime_truth_changed": {
            "scope": "readiness_contract_only",
            "does_not_change": [
                "meal_thread_truth",
                "nutrition_evidence_truth",
                "fooddb_truth",
                "manager_context_packet",
                "rescue_proposal_truth",
                "recommendation_truth",
                "proactive_trigger_truth",
                "body_plan_without_proposal_accept",
                "day_budget_ledger_without_proposal_accept",
            ],
        },
        "non_claims": {
            "live_tool_calling": False,
            "automatic_calibration_enabled": False,
            "rescue_enabled": False,
            "recommendation_enabled": False,
            "proactive_enabled": False,
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
        },
    }


__all__ = ["build_body_budget_calibration_readiness_artifact"]
