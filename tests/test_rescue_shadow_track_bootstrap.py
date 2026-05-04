from __future__ import annotations

import importlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

EXPECTED_NON_RUNTIME_FLAGS = {
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

EXPECTED_FORBIDDEN_RUNTIME_EFFECTS = [
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

ACTIVE_RUNTIME_ENTRYPOINTS = [
    "app/routes.py",
    "app/schemas.py",
    "app/models.py",
    "app/composition/intake_routes.py",
    "app/composition/v2_routes.py",
    "app/composition/intake_turn_orchestrator.py",
    "app/composition/intake_execution_orchestrator.py",
    "app/runtime/application/manager_service.py",
    "app/composition/intake_manager_tool_batch.py",
    "app/runtime/interface/provider_runtime.py",
]


def test_shadow_track_status_artifact_contains_exact_non_runtime_flags() -> None:
    module = importlib.import_module("app.rescue.domain.shadow_status")

    assert module.RESCUE_SHADOW_NON_RUNTIME_FLAGS == EXPECTED_NON_RUNTIME_FLAGS

    status = module.build_rescue_shadow_track_status()

    assert status["artifact_type"] == "rescue_shadow_track_status"
    assert status["track"] == "RescueShadow"
    assert status["slice_id"] == "rs0_shadow_track_bootstrap"
    assert {flag: status[flag] for flag in EXPECTED_NON_RUNTIME_FLAGS} == EXPECTED_NON_RUNTIME_FLAGS
    assert status["forbidden_runtime_effects"] == EXPECTED_FORBIDDEN_RUNTIME_EFFECTS


def test_shadow_track_status_module_declares_offline_sidecar_activation_contract() -> None:
    module = importlib.import_module("app.rescue.domain.shadow_status")
    contract = module.SIDECAR_ACTIVATION_CONTRACT

    assert contract.module_name == "rescue.domain.shadow_status"
    assert contract.offline_only is True
    assert contract.activation_blocked is True
    assert contract.not_runtime_authority is True
    assert contract.user_facing_activation is False
    assert contract.mutation_authority is False
    assert contract.product_intelligence_readiness_participant is False


def test_active_runtime_entrypoints_do_not_import_shadow_status_artifact() -> None:
    forbidden_tokens = [
        "app.rescue.domain.shadow_status",
        "shadow_status",
        "rescue_shadow_track_status",
    ]

    for relative_path in ACTIVE_RUNTIME_ENTRYPOINTS:
        text = (ROOT / relative_path).read_text(encoding="utf-8-sig")
        for token in forbidden_tokens:
            assert token not in text, f"{relative_path} imports or references RS0 sidecar token {token!r}"
