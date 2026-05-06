from __future__ import annotations

from app.composition.accurate_intake_pl_ce_browser_activation_evidence_gate import (
    BROWSER_ARTIFACTS,
    EXPECTED_STATUSES as BROWSER_GATE_EXPECTED_STATUSES,
    REQUIRED_INPUTS as BROWSER_GATE_REQUIRED_INPUTS,
)
from app.composition.accurate_intake_pl_ce_local_mvp_candidate_bundle import (
    EXPECTED_STATUSES as LOCAL_MVP_EXPECTED_STATUSES,
    REQUIRED_INPUTS as LOCAL_MVP_REQUIRED_INPUTS,
)
from app.composition.accurate_intake_pl_ce_ui_context_alignment_pack import (
    REQUIRED_INPUTS as UI_CONTEXT_REQUIRED_INPUTS,
)
from app.composition.accurate_intake_context_live_diagnostic_case_matrix import (
    REQUIRED_CASE_IDS as CONTEXT_LIVE_REQUIRED_CASE_IDS,
)


REQUIRED_INPUTS = (
    "pl_ce_local_mvp_candidate_bundle",
    "pl_ce_browser_activation_evidence_gate",
    "pl_ce_ui_context_alignment_pack",
    "context_live_diagnostic_dry_run_evaluator",
    "context_live_response_contract_dry_run",
)

OPTIONAL_INPUTS = (
    "context_live_diagnostic_review_pack",
    "context_live_diagnostic_gate",
)

EXPECTED_STATUSES = {
    "pl_ce_local_mvp_candidate_bundle": "pl_ce_local_mvp_candidate_ready_for_human_review",
    "pl_ce_browser_activation_evidence_gate": "browser_activation_evidence_ready_for_human_review",
    "pl_ce_ui_context_alignment_pack": "ui_context_alignment_ready_for_human_review",
    "context_live_diagnostic_dry_run_evaluator": "pass",
    "context_live_response_contract_dry_run": "pass",
    "context_live_diagnostic_review_pack": {
        "context_live_diagnostic_review_ready_with_live_canary",
        "context_live_diagnostic_review_ready_without_live_canary",
    },
    "context_live_diagnostic_gate": {
        "context_live_diagnostic_gate_ready_with_live_canary",
        "context_live_diagnostic_gate_ready_without_live_canary",
    },
}

EXPECTED_ARTIFACT_TYPES = {
    "pl_ce_local_mvp_candidate_bundle": "accurate_intake_pl_ce_local_mvp_candidate_bundle",
    "pl_ce_browser_activation_evidence_gate": "accurate_intake_pl_ce_browser_activation_evidence_gate",
    "pl_ce_ui_context_alignment_pack": "accurate_intake_pl_ce_ui_context_alignment_pack",
    "context_live_diagnostic_dry_run_evaluator": (
        "accurate_intake_context_live_diagnostic_dry_run_evaluator"
    ),
    "context_live_response_contract_dry_run": (
        "accurate_intake_context_live_response_contract_dry_run"
    ),
    "context_live_diagnostic_review_pack": "accurate_intake_context_live_diagnostic_review_pack",
    "context_live_diagnostic_gate": "accurate_intake_context_live_diagnostic_gate",
}

EXPECTED_UPSTREAM_REQUIRED_INPUTS = {
    "pl_ce_local_mvp_candidate_bundle": tuple(LOCAL_MVP_REQUIRED_INPUTS),
    "pl_ce_browser_activation_evidence_gate": tuple(BROWSER_GATE_REQUIRED_INPUTS),
    "pl_ce_ui_context_alignment_pack": tuple(UI_CONTEXT_REQUIRED_INPUTS),
}

EXPECTED_NESTED_STATUSES = {
    "pl_ce_local_mvp_candidate_bundle": dict(LOCAL_MVP_EXPECTED_STATUSES),
    "pl_ce_browser_activation_evidence_gate": dict(BROWSER_GATE_EXPECTED_STATUSES),
    "pl_ce_ui_context_alignment_pack": {
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
    },
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
    "mutation_authority",
    "frontend_semantic_owner",
    "deterministic_semantic_inference_used",
    "raw_text_intent_router_used",
    "canonical_eval_promoted",
    "live_provider_invoked",
    "fooddb_used",
    "fooddb_truth_used",
    "readiness_claimed",
    "deterministic_selected_intent",
    "deterministic_selected_target",
)


__all__ = [
    "BROWSER_ARTIFACTS",
    "CONTEXT_LIVE_REQUIRED_CASE_IDS",
    "EXPECTED_ARTIFACT_TYPES",
    "EXPECTED_NESTED_STATUSES",
    "EXPECTED_STATUSES",
    "EXPECTED_UPSTREAM_REQUIRED_INPUTS",
    "FORBIDDEN_TRUTHY_FLAGS",
    "OPTIONAL_INPUTS",
    "REQUIRED_INPUTS",
]
