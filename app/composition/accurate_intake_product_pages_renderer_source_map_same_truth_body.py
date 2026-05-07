from __future__ import annotations


SAME_TRUTH_FIELD_CONTRACTS_BODY = {
    "body": {
        "active_body_plan": {
            "ui_selector": "#body-plan-summary",
            "displayed_fact": "active body plan and target posture",
            "truth_owner": "body_domain",
            "read_model_or_api": "/body-plan/active",
            "required_backend_fields": (
                "plan.daily_budget_kcal",
                "plan.recommended_target_kcal",
                "plan.estimated_tdee",
                "plan.current_weight_kg",
                "plan.target_weight_kg",
                "plan.activity_level",
                "plan.goal_type",
            ),
            "frontend_role": "render_backend_structured_fields_only",
            "allowed_action": "refresh_read_model_or_submit_existing_forms",
            "must_not": [
                "frontend_calculate_tdee",
                "frontend_calculate_target",
                "frontend_infer_manual_override_legality",
            ],
        },
        "weight_observations": {
            "ui_selector": "#weight-history",
            "displayed_fact": "backend-supplied weight observations",
            "truth_owner": "body_domain",
            "read_model_or_api": "/weight/observations",
            "required_backend_fields": (
                "payload.observations",
                "payload.weight_kg",
            ),
            "frontend_role": "render_backend_structured_fields_only",
            "allowed_action": "submit_weight_observation_to_existing_route",
            "must_not": [
                "frontend_infer_calibration_proposal",
                "frontend_infer_weight_trend",
            ],
        },
        "manual_target_readback": {
            "ui_selector": "#manual-daily-target",
            "displayed_fact": "manual daily target readback from backend",
            "truth_owner": "budget_and_body_plan_routes",
            "read_model_or_api": "/body-plan/manual-daily-target",
            "required_backend_fields": (
                "payload.target_kcal",
                "payload.current_budget?.budget_kcal",
            ),
            "frontend_role": "render_backend_structured_fields_only",
            "allowed_action": "submit_existing_manual_target_form",
            "must_not": [
                "frontend_calculate_remaining",
                "frontend_infer_target_legality",
            ],
        },
        "budget_deficit_summary": {
            "ui_selector": "#body-budget-loop",
            "displayed_fact": "daily target consumed remaining and estimated deficit read model",
            "truth_owner": "composition_body_budget_read_model",
            "read_model_or_api": "/today/deficit-summary",
            "required_backend_fields": (
                "deficit.active_daily_target_kcal",
                "deficit.consumed_kcal",
                "deficit.remaining_kcal",
                "deficit.estimated_daily_deficit_kcal",
            ),
            "frontend_role": "render_backend_structured_fields_only",
            "allowed_action": "refresh_read_model",
            "must_not": [
                "frontend_calculate_estimated_deficit",
                "frontend_infer_calibration_proposal",
            ],
        },
        "effective_budget": {
            "ui_selector": "#body-effective-budget",
            "displayed_fact": "runtime effective budget from budget composition read model",
            "truth_owner": "budget_composition_effective_budget_read_model",
            "read_model_or_api": "/today/effective-budget",
            "required_backend_fields": ("effective.runtime_effective_budget_kcal",),
            "frontend_role": "render_backend_structured_fields_only",
            "allowed_action": "refresh_read_model",
            "must_not": [
                "frontend_calculate_effective_budget",
                "frontend_calculate_remaining",
            ],
        },
        "weekly_progress": {
            "ui_selector": "#body-weekly-progress",
            "displayed_fact": "weekly consumed and estimated deficit summary from backend",
            "truth_owner": "composition_body_budget_weekly_read_model",
            "read_model_or_api": "/today/weekly-progress",
            "required_backend_fields": (
                "weekly.total_consumed_kcal",
                "weekly.estimated_weekly_deficit_kcal",
            ),
            "frontend_role": "render_backend_structured_fields_only",
            "allowed_action": "refresh_read_model",
            "must_not": [
                "frontend_compute_weekly_deficit",
                "frontend_infer_weight_trend",
            ],
        },
    },
}


__all__ = ["SAME_TRUTH_FIELD_CONTRACTS_BODY"]
