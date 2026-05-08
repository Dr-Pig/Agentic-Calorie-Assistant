from __future__ import annotations

from app.composition.current_shell_compatibility_ids import (
    CURRENT_SHELL_COMPATIBILITY_ACTIVATION_REVIEW_ARTIFACT_TYPE,
    CURRENT_SHELL_COMPATIBILITY_ACTIVATION_REVIEW_GROUP_ID,
    CURRENT_SHELL_COMPATIBILITY_ACTIVATION_REVIEW_READY_STATUS,
    CURRENT_SHELL_COMPATIBILITY_BROWSER_ACTIVATION_ARTIFACT_TYPE,
    CURRENT_SHELL_COMPATIBILITY_BROWSER_ACTIVATION_GROUP_ID,
    CURRENT_SHELL_COMPATIBILITY_LOCAL_MVP_ARTIFACT_TYPE,
    CURRENT_SHELL_COMPATIBILITY_LOCAL_MVP_GROUP_ID,
    CURRENT_SHELL_COMPATIBILITY_LOCAL_MVP_READY_STATUS,
    CURRENT_SHELL_COMPATIBILITY_PRODUCT_PAGES_FLOW_ARTIFACT_TYPE,
    CURRENT_SHELL_COMPATIBILITY_PRODUCT_PAGES_FLOW_GROUP_ID,
    CURRENT_SHELL_COMPATIBILITY_UI_CONTEXT_ALIGNMENT_ARTIFACT_TYPE,
)

REQUIRED_CURRENT_CHAIN_ARTIFACTS = (
    "ui_same_truth_contract",
    "context_quality_pack",
    "product_pages_visual_qa",
    "product_pages_long_session_navigation_smoke",
    "pl_ce_ui_context_alignment_pack",
    CURRENT_SHELL_COMPATIBILITY_LOCAL_MVP_GROUP_ID,
    CURRENT_SHELL_COMPATIBILITY_PRODUCT_PAGES_FLOW_GROUP_ID,
    CURRENT_SHELL_COMPATIBILITY_BROWSER_ACTIVATION_GROUP_ID,
    "non_fooddb_manager_tool_contract",
    CURRENT_SHELL_COMPATIBILITY_ACTIVATION_REVIEW_GROUP_ID,
)

EXPECTED_ARTIFACT_TYPES = {
    "ui_same_truth_contract": "accurate_intake_ui_same_truth_render_contract",
    "context_quality_pack": "accurate_intake_context_quality_pack",
    "product_pages_visual_qa": "accurate_intake_product_pages_visual_qa",
    "product_pages_long_session_navigation_smoke": (
        "accurate_intake_product_pages_long_session_navigation_smoke"
    ),
    "pl_ce_ui_context_alignment_pack": CURRENT_SHELL_COMPATIBILITY_UI_CONTEXT_ALIGNMENT_ARTIFACT_TYPE,
    CURRENT_SHELL_COMPATIBILITY_LOCAL_MVP_GROUP_ID: (
        CURRENT_SHELL_COMPATIBILITY_LOCAL_MVP_ARTIFACT_TYPE
    ),
    CURRENT_SHELL_COMPATIBILITY_PRODUCT_PAGES_FLOW_GROUP_ID: (
        CURRENT_SHELL_COMPATIBILITY_PRODUCT_PAGES_FLOW_ARTIFACT_TYPE
    ),
    CURRENT_SHELL_COMPATIBILITY_BROWSER_ACTIVATION_GROUP_ID: (
        CURRENT_SHELL_COMPATIBILITY_BROWSER_ACTIVATION_ARTIFACT_TYPE
    ),
    "non_fooddb_manager_tool_contract": "accurate_intake_non_fooddb_manager_tool_contract",
    CURRENT_SHELL_COMPATIBILITY_ACTIVATION_REVIEW_GROUP_ID: (
        CURRENT_SHELL_COMPATIBILITY_ACTIVATION_REVIEW_ARTIFACT_TYPE
    ),
}

EXPECTED_STATUSES = {
    "ui_same_truth_contract": "pass",
    "context_quality_pack": "context_quality_diagnostic_pass",
    "product_pages_visual_qa": "pass",
    "product_pages_long_session_navigation_smoke": "pass",
    "pl_ce_ui_context_alignment_pack": "ui_context_alignment_ready_for_human_review",
    CURRENT_SHELL_COMPATIBILITY_LOCAL_MVP_GROUP_ID: (
        CURRENT_SHELL_COMPATIBILITY_LOCAL_MVP_READY_STATUS
    ),
    CURRENT_SHELL_COMPATIBILITY_PRODUCT_PAGES_FLOW_GROUP_ID: (
        "product_pages_self_use_flow_ready_for_human_review"
    ),
    CURRENT_SHELL_COMPATIBILITY_BROWSER_ACTIVATION_GROUP_ID: (
        "browser_activation_evidence_ready_for_human_review"
    ),
    "non_fooddb_manager_tool_contract": "non_fooddb_manager_tool_contract_ready_for_human_review",
    CURRENT_SHELL_COMPATIBILITY_ACTIVATION_REVIEW_GROUP_ID: (
        CURRENT_SHELL_COMPATIBILITY_ACTIVATION_REVIEW_READY_STATUS
    ),
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
    "deterministic_semantic_inference_used",
    "raw_text_intent_router_used",
    "mutation_authority",
)
