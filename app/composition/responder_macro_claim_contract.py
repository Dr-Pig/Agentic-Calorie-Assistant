from __future__ import annotations

from typing import Any


FORBIDDEN_MACRO_CLAIMS_CONTRACT = [
    "protein_g_without_allowed_fact",
    "carbs_g_without_allowed_fact",
    "fat_g_without_allowed_fact",
    "show_macro_without_allowed_fact",
    "macro_guard_reason_without_allowed_fact",
]

INVENTION_BLOCKERS_BY_MACRO_CLAIM_TYPE = {
    "protein_g": "invented_protein_claim",
    "carbs_g": "invented_carbs_claim",
    "fat_g": "invented_fat_claim",
    "show_macro": "invented_macro_visibility_claim",
    "macro_guard_reason": "invented_macro_guard_reason",
}


def committed_macro_allowed_facts() -> list[dict[str, Any]]:
    return [
        {"fact_id": "fact-show-macro", "claim_type": "show_macro", "value": True},
        {"fact_id": "fact-macro-reason", "claim_type": "macro_guard_reason", "value": "committed_and_aligned"},
        {"fact_id": "fact-protein", "claim_type": "protein_g", "value": 20},
        {"fact_id": "fact-carbs", "claim_type": "carbs_g", "value": 50},
        {"fact_id": "fact-fat", "claim_type": "fat_g", "value": 10},
    ]


def committed_macro_accepted_claims() -> list[dict[str, Any]]:
    return [
        {"claim_type": "show_macro", "fact_id": "fact-show-macro", "value": True},
        {"claim_type": "macro_guard_reason", "fact_id": "fact-macro-reason", "value": "committed_and_aligned"},
        {"claim_type": "protein_g", "fact_id": "fact-protein", "value": 20},
        {"claim_type": "carbs_g", "fact_id": "fact-carbs", "value": 50},
        {"claim_type": "fat_g", "fact_id": "fact-fat", "value": 10},
    ]


def hidden_macro_scenario() -> dict[str, Any]:
    return {
        "scenario_id": "macro_hidden_no_visible_claim",
        "budget_status": "ready",
        "allowed_facts": [
            {"fact_id": "fact-show-macro-hidden", "claim_type": "show_macro", "value": False},
            {"fact_id": "fact-macro-hidden-reason", "claim_type": "macro_guard_reason", "value": "no_macro_data"},
        ],
        "accepted_claims": [
            {"claim_type": "show_macro", "fact_id": "fact-show-macro-hidden", "value": False},
            {"claim_type": "macro_guard_reason", "fact_id": "fact-macro-hidden-reason", "value": "no_macro_data"},
        ],
        "rejected_claims": [
            {"claim_type": "protein_g", "fact_id": "missing-protein", "value": 24},
            {"claim_type": "show_macro", "fact_id": "missing-show-macro", "value": True},
        ],
    }
