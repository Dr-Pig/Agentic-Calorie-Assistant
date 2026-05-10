from __future__ import annotations

import importlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

SIDECAR_MODULES = [
    "app.advanced_shadow_lab",
    "app.advanced_shadow_lab.chat_ux_copy_alignment",
    "app.advanced_shadow_lab.case_pairing",
    "app.advanced_shadow_lab.chat_ux_packet",
    "app.advanced_shadow_lab.dogfood_replay",
    "app.advanced_shadow_lab.e2e_fixture_chain",
    "app.advanced_shadow_lab.e2e_fixture_chain_policy",
    "app.advanced_shadow_lab.live_bundle_fixture_inputs",
    "app.advanced_shadow_lab.live_bundle_inputs",
    "app.advanced_shadow_lab.manifest",
    "app.advanced_shadow_lab.no_send_control_comparison",
    "app.advanced_shadow_lab.recommendation_copy_live_diagnostic",
    "app.advanced_shadow_lab.rescue_copy_live_diagnostic",
    "app.advanced_shadow_lab.shadow_comparison",
    "app.advanced_shadow_lab.shadow_comparison_live_rows",
    "app.advanced_shadow_lab.vertical_proof",
    "app.memory",
    "app.memory.domain",
    "app.memory.domain.summaries",
    "app.memory.domain.long_term_context_candidates",
    "app.memory.application",
    "app.memory.application.derived_summaries",
    "app.memory.application.long_term_context_shadow_lab",
    "app.memory.application.long_term_context_shadow.lab_active_view",
    "app.memory.application.long_term_context_shadow.lab_product_shadow_inputs",
    "app.memory.application.long_term_context_shadow.lab_review_surface",
    "app.memory.application.long_term_context_shadow.lab_store",
    "app.memory.application.long_term_context_shadow.reviewed_product_replay",
    "app.memory.application.local_memory_framework_review",
    "app.memory.application.runtime_lab_reviewed_memory_consumer_bridge",
    "app.memory.application.runtime_lab_reviewed_memory_retrieval",
    "app.memory.application.runtime_lab_reviewed_memory_store",
    "app.memory.application.runtime_lab_signal_projection",
    "app.recommendation",
    "app.recommendation.domain",
    "app.recommendation.domain.candidate_quality",
    "app.recommendation.application",
    "app.recommendation.application.candidate_quality_gate",
    "app.recommendation.application.five_node_shadow_fixture",
    "app.recommendation.application.five_node_shadow_runner",
    "app.recommendation.application.five_node_summary_bridge",
    "app.recommendation.application.intake_hint_shadow",
    "app.recommendation.application.reviewed_memory_candidate_bridge",
    "app.recommendation.application.summary_pool_posture",
    "app.recommendation.application.three_node_shadow_contract",
    "app.recommendation.application.three_node_shadow_policy",
    "app.recommendation.application.three_node_summary_bridge",
    "app.rescue",
    "app.rescue.domain",
    "app.rescue.domain.proposal_read_models",
    "app.rescue.domain.shadow_status",
    "app.rescue.application",
    "app.rescue.application.proposal_read_model",
    "app.rescue.application.no_commit_viability",
    "app.rescue.application.option_generation_shadow",
    "app.rescue.application.proposal_shaping_input_shadow",
    "app.rescue.application.reviewed_memory_chain_bridge",
    "app.rescue.application.proposal_shaping_fake_runner",
    "app.rescue.application.proposal_shaping_output_validator_shadow",
    "app.rescue.application.shadow_chain_runner",
    "app.runtime.contracts.pending_meal_intent",
    "app.runtime.contracts.proactive_gate",
    "app.runtime.application.proactive_deterministic_gate",
    "app.runtime.application.proactive_no_send_control_path_evidence",
    "app.runtime.application.proactive_no_send_interaction_model",
    "app.runtime.application.proactive_no_send_nudge_bridge",
    "app.runtime.application.proactive_no_send_nudge_candidate",
    "app.runtime.application.proactive_no_send_review_sink",
    "app.runtime.application.proactive_no_send_shadow_evaluator",
    "app.runtime.application.proactive_recommendation_prompt_bridge",
    "app.runtime.application.proactive_rescue_nudge_bridge",
    "app.runtime.application.proactive_summary_consumer",
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
        "app.advanced_shadow_lab",
        "proactive_deterministic_gate",
        "proactive_no_send_shadow_evaluator",
        "pending_meal_intent",
        "proactive_gate",
    ]

    for relative_path in ACTIVE_RUNTIME_SURFACES:
        text = (ROOT / relative_path).read_text(encoding="utf-8-sig")
        for token in forbidden_tokens:
            assert token not in text, (
                f"{relative_path} imports or references sidecar token {token!r}"
            )


def test_sidecar_modules_are_not_b2_readiness_inputs() -> None:
    forbidden_tokens = [
        "app.memory",
        "app.recommendation",
        "app.rescue",
        "app.advanced_shadow_lab",
        "proactive_deterministic_gate",
        "proactive_no_send_shadow_evaluator",
        "pending_meal_intent",
        "proactive_gate",
    ]

    for relative_path in B2_READINESS_SURFACES:
        path = ROOT / relative_path
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8-sig")
        for token in forbidden_tokens:
            assert token not in text, (
                f"{relative_path} couples B2 readiness to sidecar token {token!r}"
            )
