from __future__ import annotations


SAME_TRUTH_FIELD_CONTRACTS_CHAT_TODAY = {
    "chat": {
        "conversation_history": {
            "ui_selector": "#chat-scroll",
            "displayed_fact": "date-scoped chat messages",
            "truth_owner": "composition_chat_history_read_model",
            "read_model_or_api": "/accurate-intake/chat-history",
            "required_backend_fields": ("payload.messages", "message.role", "message.content"),
            "frontend_role": "render_backend_structured_fields_only",
            "allowed_action": "read_or_submit_message",
            "must_not": [
                "frontend_infer_intent",
                "frontend_infer_workflow",
                "frontend_select_target",
            ],
        },
        "current_turn_response": {
            "ui_selector": "#chat-scroll",
            "displayed_fact": "manager response bubble from current turn",
            "truth_owner": "manager_runtime_response",
            "read_model_or_api": "/estimate",
            "required_backend_fields": ("payload.coach_message",),
            "frontend_role": "render_backend_structured_fields_only",
            "allowed_action": "submit_message_to_existing_backend_route",
            "must_not": [
                "frontend_infer_intent",
                "frontend_infer_logged_status",
                "frontend_infer_evidence_gap",
            ],
        },
        "session_navigation": {
            "ui_selector": "#local-date",
            "displayed_fact": "selected user and date context",
            "truth_owner": "browser_url_and_backend_query_contract",
            "read_model_or_api": "/accurate-intake/chat-history",
            "required_backend_fields": ("user_id: userId()", "local_date: selectedDate()"),
            "frontend_role": "preserve_query_context_only",
            "allowed_action": "navigate_between_chat_today_body",
            "must_not": [
                "frontend_create_memory",
                "frontend_override_backend_context",
            ],
        },
        "context_status_strip": {
            "ui_selector": "#chat-context-strip",
            "displayed_fact": "latest Manager context sidecar status from chat history messages",
            "truth_owner": "manager_context_runtime_trace_sidecar",
            "read_model_or_api": "/accurate-intake/chat-history",
            "required_backend_fields": (
                "message.context_policy_version",
                "message.loaded_context_summary",
                "message.omitted_context_summary",
                "message.pending_pins_present",
                "message.target_candidate_count",
            ),
            "frontend_role": "render_backend_structured_fields_only",
            "allowed_action": "read_context_status_from_chat_history",
            "must_not": [
                "frontend_infer_context_snapshot",
                "frontend_infer_manager_context_gap",
                "frontend_infer_intent",
            ],
        },
        "read_only_target_candidates": {
            "ui_selector": "#chat-target-candidate-list",
            "displayed_fact": "read-only correction or removal target candidate names",
            "truth_owner": "manager_context_target_candidate_sidecar",
            "read_model_or_api": "/accurate-intake/chat-history",
            "required_backend_fields": (
                "message.target_candidate_count",
                "message.target_candidate_names",
            ),
            "frontend_role": "render_backend_structured_fields_only",
            "allowed_action": "render_candidate_names_for_review_only",
            "must_not": [
                "frontend_select_target",
                "frontend_infer_correction_intent",
                "frontend_infer_mutation_legality",
            ],
        },
    },
    "today": {
        "budget_summary": {
            "ui_selector": "#remaining-kcal",
            "displayed_fact": "daily budget consumed and remaining values",
            "truth_owner": "budget_domain",
            "read_model_or_api": "/today/current-budget",
            "required_backend_fields": (
                "payload.budget_kcal",
                "payload.consumed_kcal",
                "payload.remaining_kcal",
            ),
            "frontend_role": "render_backend_structured_fields_only",
            "allowed_action": "refresh_read_model",
            "must_not": [
                "frontend_recompute_consumed",
                "frontend_recompute_remaining",
                "frontend_infer_overshoot",
            ],
        },
        "meal_summaries": {
            "ui_selector": "#meal-list",
            "displayed_fact": "active meal summaries for selected day",
            "truth_owner": "intake_and_budget_projection",
            "read_model_or_api": "/today/current-budget",
            "required_backend_fields": (
                "payload.meals",
                "meal.meal_title",
                "meal.total_kcal",
                "meal.resolution_status",
            ),
            "frontend_role": "render_backend_structured_fields_only",
            "allowed_action": "read_only_diary_navigation",
            "must_not": [
                "frontend_treat_summary_as_full_meal_truth",
                "frontend_infer_food_semantics",
            ],
        },
        "macro_surface": {
            "ui_selector": "#macro-panel",
            "displayed_fact": "day-level consumed protein carbs and fat only when backend visibility allows it",
            "truth_owner": "budget_domain_macro_visibility_policy",
            "read_model_or_api": "/today/current-budget",
            "required_backend_fields": (
                "payload.consumed_protein",
                "payload.consumed_carbs",
                "payload.consumed_fat",
                "payload.show_macro",
                "payload.macro_guard_reason",
            ),
            "frontend_role": "render_backend_structured_fields_only",
            "allowed_action": "refresh_read_model",
            "must_not": [
                "frontend_infer_macro_visibility",
                "frontend_compute_macro_values",
                "frontend_parse_assistant_text_for_macro_truth",
            ],
        },
    },
}


__all__ = ["SAME_TRUTH_FIELD_CONTRACTS_CHAT_TODAY"]
