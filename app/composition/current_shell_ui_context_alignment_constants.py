from __future__ import annotations

REQUIRED_INPUTS = (
    "ui_same_truth_contract",
    "product_pages_renderer_source_map",
    "context_coverage_matrix",
    "product_pages_browser_smoke",
    "product_pages_seven_day_diary_smoke",
    "product_pages_short_term_context_smoke",
    "product_pages_visual_qa",
)

EXPECTED_STATUSES = {
    "ui_same_truth_contract": "pass",
    "product_pages_renderer_source_map": "product_pages_renderer_source_map_ready_for_human_review",
    "context_coverage_matrix": {
        "context_coverage_matrix_ready_for_human_review",
        "context_coverage_matrix_ready_with_known_runtime_gaps",
    },
    "product_pages_browser_smoke": "pass",
    "product_pages_seven_day_diary_smoke": "pass",
    "product_pages_short_term_context_smoke": "pass",
    "product_pages_visual_qa": "pass",
}

EXPECTED_ARTIFACT_TYPES = {
    "ui_same_truth_contract": "accurate_intake_ui_same_truth_render_contract",
    "product_pages_renderer_source_map": "accurate_intake_product_pages_renderer_source_map",
    "context_coverage_matrix": "accurate_intake_pl_ce_context_coverage_matrix",
    "product_pages_visual_qa": "accurate_intake_product_pages_visual_qa",
}

EXPECTED_SMOKE_IDS = {
    "product_pages_browser_smoke": "accurate_intake_product_pages_browser_smoke_v1",
    "product_pages_seven_day_diary_smoke": "accurate_intake_product_pages_seven_day_diary_smoke_v1",
    "product_pages_short_term_context_smoke": "accurate_intake_product_pages_short_term_context_smoke_v1",
}

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
    "context_engineering_fault_claimed",
    "real_fooddb_pass_claimed",
    "dogfood_pass",
    "web_readiness_claimed",
    "product_readiness_claimed",
    "private_self_use_approved",
    "production_db_used",
    "manager_context_packet_schema_changed",
    "runtime_truth_changed",
    "mutation_changed",
    "mutation_authority",
    "frontend_semantic_owner",
    "deterministic_semantic_inference_used",
    "deterministic_selected_target",
    "raw_text_intent_router_used",
    "forbidden_storage_used",
)

REQUIRED_TRUE_FLAGS = {
    "ui_same_truth_contract": ("frontend_render_only",),
    "product_pages_renderer_source_map": ("render_only_boundary_ok",),
    "product_pages_browser_smoke": (
        "browser_executed", "chat_page_loaded", "chat_history_reloaded",
        "chat_scroll_behavior_checked", "chat_no_debug_trace", "today_page_loaded",
        "today_summary_rendered", "today_meal_list_rendered", "today_no_debug_trace",
        "body_page_loaded", "body_active_plan_rendered", "body_plan_readback_checked",
        "body_plan_read_model_fields_rendered", "body_latest_weight_rendered_from_backend",
        "body_manual_target_read_model_rendered", "desktop_no_overflow",
        "mobile_no_overflow", "nav_session_query_preserved",
    ),
    "product_pages_seven_day_diary_smoke": (
        "browser_executed", "seven_day_window_checked", "per_day_diary_isolated",
        "per_day_budget_values_checked", "today_date_strip_checked",
        "today_nav_date_preserved", "today_chat_link_date_preserved",
        "desktop_no_overflow", "mobile_no_overflow",
    ),
    "product_pages_short_term_context_smoke": (
        "browser_executed", "browser_reload_checked", "fixture_manager_used",
        "pending_followup_created", "pending_followup_reloaded",
        "context_policy_version_present", "loaded_context_summary_present",
        "omitted_context_summary_present", "pending_pins_present_after_followup",
        "chat_history_context_fields_reloaded", "chat_cjk_roundtrip_rendered",
        "assistant_followup_bubble_rendered", "assistant_commit_bubble_rendered",
        "today_same_day_meal_rendered", "today_summary_rendered",
        "product_pages_no_debug_trace",
    ),
    "product_pages_visual_qa": (
        "browser_executed", "desktop_screenshots_captured", "mobile_screenshots_captured",
        "chat_surface_verified", "today_surface_verified", "body_surface_verified",
        "three_distinct_pages_verified", "desktop_no_overflow", "mobile_no_overflow",
        "visible_trace_debug_terms_absent",
    ),
}
