from __future__ import annotations

from app.composition.current_shell_compatibility_ids import (
    CURRENT_SHELL_COMPATIBILITY_LOCAL_MVP_ARTIFACT_TYPE,
    CURRENT_SHELL_COMPATIBILITY_LOCAL_MVP_GROUP_ID,
    CURRENT_SHELL_COMPATIBILITY_LOCAL_MVP_READY_STATUS,
    CURRENT_SHELL_COMPATIBILITY_PRODUCT_PAGES_FLOW_ARTIFACT_TYPE,
)

REQUIRED_INPUTS = (
    CURRENT_SHELL_COMPATIBILITY_LOCAL_MVP_GROUP_ID,
    "product_pages_browser_smoke",
    "product_pages_seven_day_diary_smoke",
    "product_pages_short_term_context_smoke",
    "product_pages_target_candidate_ui_smoke",
    "product_pages_visual_qa",
    "product_pages_body_noplan_degraded_smoke",
    "fixture_full_product_loop_e2e",
    "product_pages_self_use_flow_gate",
)

EXPECTED_STATUSES = {
    CURRENT_SHELL_COMPATIBILITY_LOCAL_MVP_GROUP_ID: (
        CURRENT_SHELL_COMPATIBILITY_LOCAL_MVP_READY_STATUS
    ),
    "product_pages_browser_smoke": "pass",
    "product_pages_seven_day_diary_smoke": "pass",
    "product_pages_short_term_context_smoke": "pass",
    "product_pages_target_candidate_ui_smoke": "pass",
    "product_pages_visual_qa": "pass",
    "product_pages_body_noplan_degraded_smoke": "pass",
    "fixture_full_product_loop_e2e": "fixture_product_loop_e2e_diagnostic_pass",
    "product_pages_self_use_flow_gate": "product_pages_self_use_flow_ready_for_human_review",
}

EXPECTED_ARTIFACT_TYPES = {
    CURRENT_SHELL_COMPATIBILITY_LOCAL_MVP_GROUP_ID: (
        CURRENT_SHELL_COMPATIBILITY_LOCAL_MVP_ARTIFACT_TYPE
    ),
    "product_pages_visual_qa": "accurate_intake_product_pages_visual_qa",
    "product_pages_self_use_flow_gate": CURRENT_SHELL_COMPATIBILITY_PRODUCT_PAGES_FLOW_ARTIFACT_TYPE,
    "fixture_full_product_loop_e2e": "accurate_intake_fixture_full_product_loop_e2e",
}

EXPECTED_SMOKE_IDS = {
    "product_pages_browser_smoke": "accurate_intake_product_pages_browser_smoke_v1",
    "product_pages_seven_day_diary_smoke": "accurate_intake_product_pages_seven_day_diary_smoke_v1",
    "product_pages_short_term_context_smoke": "accurate_intake_product_pages_short_term_context_smoke_v1",
    "product_pages_target_candidate_ui_smoke": "accurate_intake_product_pages_target_candidate_ui_smoke_v1",
    "product_pages_body_noplan_degraded_smoke": "accurate_intake_product_pages_body_noplan_degraded_smoke_v1",
}

BROWSER_ARTIFACTS = (
    "product_pages_browser_smoke",
    "product_pages_seven_day_diary_smoke",
    "product_pages_short_term_context_smoke",
    "product_pages_target_candidate_ui_smoke",
    "product_pages_visual_qa",
    "product_pages_body_noplan_degraded_smoke",
)

REQUIRED_SELF_USE_FLOW_SUMMARY_FLAGS = (
    "three_distinct_pages_verified",
    "seven_day_diary_checked",
    "short_term_context_checked",
    "target_candidate_ui_checked",
    "today_macro_runtime_mirror_checked",
    "renderer_source_closure_checked",
    "context_target_browser_closure_checked",
    "body_noplan_degraded_checked",
)

REQUIRED_PRODUCT_LOOP_STEPS = (
    "target_update",
    "food_log",
    "listed_basket_commit",
    "correction",
    "removal",
    "remaining_query",
    "reload_continuity",
    "browser_render_same_truth",
    "context_replay",
    "fake_provider_context_smoke",
)

FORBIDDEN_TRUTHY_FLAGS = (
    "ready_for_live_diagnostic_decision",
    "ready_for_fdb_integration",
    "live_llm_invoked",
    "live_provider_called",
    "web_tavily_used",
    "web_tavily_invoked",
    "websearch_evidence_used",
    "fooddb_evidence_used",
    "fooddb_truth_updated",
    "real_fooddb_pass_claimed",
    "dogfood_pass",
    "web_readiness_claimed",
    "product_readiness_claimed",
    "private_self_use_approved",
    "production_db_used",
    "manager_context_packet_schema_changed",
    "runtime_truth_changed",
    "mutation_changed",
    "frontend_semantic_owner",
    "frontend_selected_target",
    "deterministic_semantic_inference_used",
    "deterministic_selected_target",
    "raw_text_intent_router_used",
    "mutation_authority",
    "forbidden_storage_used",
)

REQUIRED_TRUE_FLAGS = {
    "product_pages_browser_smoke": (
        "browser_executed",
        "chat_page_loaded",
        "chat_sent_cjk_message",
        "chat_assistant_bubble_rendered",
        "chat_history_reloaded",
        "chat_scroll_behavior_checked",
        "chat_reload_scroll_behavior_checked",
        "today_page_loaded",
        "today_date_switch_checked",
        "today_summary_rendered",
        "today_meal_list_rendered",
        "body_page_loaded",
        "body_active_plan_rendered",
        "body_plan_readback_checked",
        "body_plan_read_model_fields_rendered",
        "body_latest_weight_rendered_from_backend",
        "body_manual_target_read_model_rendered",
        "today_manual_target_readback_checked",
        "desktop_no_overflow",
        "mobile_no_overflow",
        "mobile_populated_state_checked",
        "product_cjk_copy_rendered",
        "nav_session_query_preserved",
    ),
    "product_pages_seven_day_diary_smoke": (
        "browser_executed",
        "seven_day_window_checked",
        "per_day_diary_isolated",
        "per_day_budget_values_checked",
        "today_date_strip_checked",
        "today_nav_date_preserved",
        "today_chat_link_date_preserved",
        "desktop_no_overflow",
        "mobile_no_overflow",
    ),
    "product_pages_short_term_context_smoke": (
        "browser_executed",
        "browser_reload_checked",
        "fixture_manager_used",
        "pending_followup_created",
        "pending_followup_reloaded",
        "context_policy_version_present",
        "loaded_context_summary_present",
        "omitted_context_summary_present",
        "pending_pins_present_after_followup",
        "chat_history_context_fields_reloaded",
        "chat_cjk_roundtrip_rendered",
        "assistant_followup_bubble_rendered",
        "assistant_commit_bubble_rendered",
        "today_same_day_meal_rendered",
        "today_summary_rendered",
        "product_pages_no_debug_trace",
    ),
    "product_pages_target_candidate_ui_smoke": (
        "browser_executed",
        "browser_reload_checked",
        "chat_page_loaded",
        "chat_history_reloaded",
        "target_candidate_surface_checked",
        "target_candidate_list_read_only",
        "context_strip_read_only",
        "product_pages_no_debug_trace",
    ),
    "product_pages_visual_qa": (
        "browser_executed",
        "desktop_screenshots_captured",
        "mobile_screenshots_captured",
        "chat_surface_verified",
        "today_surface_verified",
        "body_surface_verified",
        "three_distinct_pages_verified",
        "desktop_no_overflow",
        "mobile_no_overflow",
        "visible_trace_debug_terms_absent",
    ),
    "product_pages_body_noplan_degraded_smoke": (
        "browser_executed",
        "body_page_loaded",
        "today_page_loaded",
        "no_plan_body_status_rendered",
        "body_targets_hidden_for_no_plan",
        "body_budget_degraded_rendered",
        "today_no_plan_budget_rendered",
        "no_bootstrap_or_mutation_post",
        "product_pages_no_debug_trace",
    ),
    "fixture_full_product_loop_e2e": ("fixture_evidence_used",),
    "product_pages_self_use_flow_gate": (
        "all_required_browser_artifacts_executed",
        "browser_executed_required",
    ),
}
