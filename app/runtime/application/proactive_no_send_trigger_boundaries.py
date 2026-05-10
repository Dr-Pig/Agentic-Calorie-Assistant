from __future__ import annotations

from typing import Any

from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "runtime.application.proactive_no_send_trigger_boundaries"
)


def add_trigger_boundaries(row: dict[str, Any], trigger_type: str) -> None:
    if trigger_type == "recommendation_prompt":
        row["recommendation_prompt_boundary"] = {
            "allowed": ["candidate_invitation_only"],
            "forbidden": [
                "output_actual_ranked_food_candidates",
                "query_live_menu_or_search",
                "create_intake_hint_packet",
                "serve_recommendation_result",
            ],
        }
        row["recommendation_served"] = False
        row["intake_hint_packet_created"] = False
    if trigger_type == "calibration_insight":
        row["allowed_output"] = ["offer_calibration_preview"]
        row["forbidden_output"] = [
            "tell_user_should_change_target",
            "output_specific_new_kcal_target",
            "mutate_body_plan",
        ]
        row["body_plan_mutated"] = False
    if trigger_type == "rescue_nudge":
        row["allowed_output"] = ["invite_future_rescue_review"]
        row["forbidden_output"] = [
            "output_specific_future_deficit",
            "create_rescue_proposal",
            "mutate_day_budget_ledger",
        ]
        row["rescue_committed"] = False


__all__ = ["SIDECAR_ACTIVATION_CONTRACT", "add_trigger_boundaries"]
