from __future__ import annotations

WEBSEARCH_MANAGER_OUTPUT_DIAGNOSTIC_PROFILE = {
    "manager_mode": "fixture_websearch_manager_output",
    "provider_profile_role": "deterministic_fixture_only",
    "live_provider_used": False,
    "production_selected": False,
    "readiness_owner": False,
}

WEBSEARCH_MANAGER_OUTPUT_NON_CLAIMS = [
    "no_live_websearch_call",
    "no_live_provider_call",
    "no_runtime_mutation",
    "no_websearch_runtime_truth",
    "no_fooddb_truth_promotion",
    "no_exact_card_truth_promotion",
    "no_readiness_claim",
]

MUTATING_FINAL_ACTIONS = frozenset({"commit", "log_food", "write_ledger", "canonical_write"})
NON_MUTATING_WORKFLOW_EFFECTS = frozenset(
    {
        "answer_only",
        "no_commit",
        "no_mutation",
        "pause_for_clarification",
        "query_only",
        "source_candidate_review",
    }
)
MUTATING_WORKFLOW_EFFECT_FRAGMENTS = (
    "canonical_write",
    "commit",
    "food_log",
    "ledger",
    "mutation_applied",
)
FOLLOWUP_FINAL_ACTIONS = frozenset({"ask_followup", "no_commit", "answer_only"})
REJECTION_FINAL_ACTIONS = frozenset({"no_commit", "answer_only", "ask_followup"})
FORBIDDEN_OUTPUT_KEYS = frozenset(
    {
        "accepted_usage",
        "exact_card_truth",
        "final_kcal",
        "final_truth",
        "food_evidence_record",
        "kcal_range",
        "ledger_mutation_result",
        "likely_kcal",
        "manager_context_packet",
        "manager_context_packet_v1",
        "packet_ready_anchor",
        "packet_ready_evidence",
        "packetizer_input",
        "packetizer_output",
        "runtime_truth_allowed",
    }
)
FORBIDDEN_NON_EMPTY_SURFACES = frozenset(
    {
        "target_attachment",
        "tool_calls",
    }
)

__all__ = [
    "FOLLOWUP_FINAL_ACTIONS",
    "FORBIDDEN_NON_EMPTY_SURFACES",
    "FORBIDDEN_OUTPUT_KEYS",
    "MUTATING_FINAL_ACTIONS",
    "MUTATING_WORKFLOW_EFFECT_FRAGMENTS",
    "NON_MUTATING_WORKFLOW_EFFECTS",
    "REJECTION_FINAL_ACTIONS",
    "WEBSEARCH_MANAGER_OUTPUT_DIAGNOSTIC_PROFILE",
    "WEBSEARCH_MANAGER_OUTPUT_NON_CLAIMS",
]
