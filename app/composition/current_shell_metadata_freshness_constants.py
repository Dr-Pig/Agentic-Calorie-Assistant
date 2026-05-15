from __future__ import annotations

from app.composition import current_shell_compatibility_ids as cs_ids

REQUIRED_PL_CE_METADATA_ARTIFACTS = (
    "context_quality_pack", "product_pages_visual_qa", "pl_ce_local_review_decision_pack",
    "pl_ce_local_mvp_candidate_bundle", "pl_ce_activation_review_manifest",
    "ui_same_truth_render_contract",
)

EXPECTED_ARTIFACT_TYPES = {
    "context_quality_pack": "accurate_intake_context_quality_pack",
    "product_pages_visual_qa": "accurate_intake_product_pages_visual_qa",
    "pl_ce_local_review_decision_pack": cs_ids.CURRENT_SHELL_COMPATIBILITY_LOCAL_REVIEW_ARTIFACT_TYPE,
    "pl_ce_local_mvp_candidate_bundle": cs_ids.CURRENT_SHELL_COMPATIBILITY_LOCAL_MVP_ARTIFACT_TYPE,
    "pl_ce_activation_review_manifest": "accurate_intake_pl_ce_activation_review_manifest",
    "ui_same_truth_render_contract": "accurate_intake_ui_same_truth_render_contract",
}

EXPECTED_STATUSES = {
    "context_quality_pack": "context_quality_diagnostic_pass",
    "product_pages_visual_qa": "pass",
    "pl_ce_local_review_decision_pack": cs_ids.CURRENT_SHELL_COMPATIBILITY_LOCAL_REVIEW_READY_STATUS,
    "pl_ce_local_mvp_candidate_bundle": cs_ids.CURRENT_SHELL_COMPATIBILITY_LOCAL_MVP_READY_STATUS,
    "pl_ce_activation_review_manifest": "pl_ce_activation_review_manifest_ready",
    "ui_same_truth_render_contract": "pass",
}

MIN_CONTEXT_SUMMARY_COUNTS = {
    "context_replay_scenario_count": 12,
    "pending_pin_scenarios": 3,
    "manager_semantic_required_scenarios": 1,
    "short_term_runtime_replay_scenario_count": 7,
    "fake_provider_handoff_scenario_count": 6,
}

OVERCLAIM_FLAGS = (
    "ready_for_live_diagnostic_decision",
    "ready_for_fdb_integration",
    "live_llm_invoked",
    "web_tavily_used",
    "web_tavily_invoked",
    "production_db_used",
    "fooddb_truth_updated",
    "fooddb_evidence_used",
    "websearch_evidence_used",
    "real_fooddb_pass_claimed",
    "dogfood_pass",
    "web_readiness_claimed",
    "product_readiness_claimed",
    "private_self_use_approved",
    "frontend_semantic_owner",
    "runtime_truth_changed",
    "mutation_changed",
    "manager_context_packet_schema_changed",
    "context_engineering_fault_claimed",
    "deterministic_semantic_inference_used",
    "raw_text_intent_router_used",
    "mutation_authority",
    "canonical_eval_promoted",
)
