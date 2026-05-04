from __future__ import annotations

from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract("rescue.domain.shadow_status")

RESCUE_SHADOW_NON_RUNTIME_FLAGS = {
    "shadow_mode": True,
    "real_runtime_effect": False,
    "rescue_committed": False,
    "proposal_committed": False,
    "day_budget_mutated": False,
    "body_plan_mutated": False,
    "meal_thread_mutated": False,
    "durable_memory_written": False,
    "manager_context_injected": False,
    "proactive_sent": False,
    "recommendation_served": False,
    "live_provider_used": False,
    "product_readiness_claimed": False,
    "private_self_use_approved": False,
}

FORBIDDEN_RESCUE_SHADOW_RUNTIME_EFFECTS = [
    "ManagerContextPacket",
    "DayBudgetLedger mutation",
    "LedgerEntry creation",
    "BodyPlan mutation",
    "MealThread mutation",
    "ProposalContainer commit",
    "live chat runtime",
    "live provider call",
    "proactive send",
    "recommendation served",
]


def build_rescue_shadow_track_status() -> dict[str, object]:
    return {
        "artifact_type": "rescue_shadow_track_status",
        "track": "RescueShadow",
        "slice_id": "rs0_shadow_track_bootstrap",
        **RESCUE_SHADOW_NON_RUNTIME_FLAGS,
        "forbidden_runtime_effects": list(FORBIDDEN_RESCUE_SHADOW_RUNTIME_EFFECTS),
    }
