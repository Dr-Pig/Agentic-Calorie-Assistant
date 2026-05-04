from __future__ import annotations

import importlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

SIDECAR_MODULES = [
    "app.memory",
    "app.memory.domain",
    "app.memory.domain.summaries",
    "app.memory.application",
    "app.memory.application.derived_summaries",
    "app.recommendation",
    "app.recommendation.domain",
    "app.recommendation.domain.candidate_quality",
    "app.recommendation.application",
    "app.recommendation.application.candidate_quality_gate",
    "app.rescue",
    "app.rescue.fixtures",
    "app.rescue.fixtures.shadow_scenarios",
    "app.rescue.domain",
    "app.rescue.domain.proposal_read_models",
    "app.rescue.domain.shadow_context",
    "app.rescue.domain.shadow_status",
    "app.rescue.domain.shadow_trigger",
    "app.rescue.domain.shadow_viability",
    "app.rescue.domain.shadow_options",
    "app.rescue.domain.shadow_artifact",
    "app.rescue.domain.shadow_review_queue",
    "app.rescue.application",
    "app.rescue.application.proposal_read_model",
    "app.rescue.application.shadow_trigger_detector",
    "app.rescue.application.shadow_viability_scorer",
    "app.rescue.application.shadow_option_generator",
    "app.rescue.application.shadow_candidate_artifact",
    "app.rescue.application.shadow_review_queue",
    "app.runtime.contracts.pending_meal_intent",
    "app.runtime.contracts.proactive_gate",
    "app.runtime.application.proactive_deterministic_gate",
]

ACTIVE_RUNTIME_SURFACES = [
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
    "app/composition/manager_context_runtime.py",
    "app/intake/application/manager_context_policy.py",
    "app/runtime/agent/manager_context_payload.py",
]

B2_READINESS_SURFACES = [
    "scripts/build_wave1_phase_b2_evidence_synthesis_smoke.py",
    "scripts/verify_wave1_phase_b2_evidence_synthesis_readiness.py",
    "scripts/audit_wave1_phase_b2_local_p0_closure.py",
]


def test_sidecar_modules_declare_offline_activation_block() -> None:
    for module_name in SIDECAR_MODULES:
        module = importlib.import_module(module_name)
        contract = getattr(module, "SIDECAR_ACTIVATION_CONTRACT")

        assert contract.offline_only is True, module_name
        assert contract.activation_blocked is True, module_name
        assert contract.not_runtime_authority is True, module_name
        assert contract.user_facing_activation is False, module_name
        assert contract.mutation_authority is False, module_name
        assert contract.product_intelligence_readiness_participant is False, module_name


def test_sidecar_modules_are_not_imported_by_active_runtime_surfaces() -> None:
    forbidden_tokens = [
        "app.memory",
        "app.recommendation",
        "app.rescue",
        "proactive_deterministic_gate",
        "pending_meal_intent",
        "proactive_gate",
    ]

    for relative_path in ACTIVE_RUNTIME_SURFACES:
        text = (ROOT / relative_path).read_text(encoding="utf-8-sig")
        for token in forbidden_tokens:
            assert token not in text, f"{relative_path} imports or references sidecar token {token!r}"


def test_sidecar_modules_are_not_b2_readiness_inputs() -> None:
    forbidden_tokens = [
        "app.memory",
        "app.recommendation",
        "app.rescue",
        "proactive_deterministic_gate",
        "pending_meal_intent",
        "proactive_gate",
    ]

    for relative_path in B2_READINESS_SURFACES:
        path = ROOT / relative_path
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8-sig")
        for token in forbidden_tokens:
            assert token not in text, f"{relative_path} couples B2 readiness to sidecar token {token!r}"
