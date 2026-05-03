from __future__ import annotations

import importlib


def test_provider_independence_audit_passes_for_pr93_strategy() -> None:
    module = importlib.import_module("scripts.build_accurate_intake_provider_independence_audit")

    audit = module.build_provider_independence_audit()

    assert audit["artifact_type"] == "accurate_intake_provider_independence_audit"
    assert audit["passed"] is True
    assert audit["provider_independence_audit"] == {
        "no_product_semantic_enum_references_provider_names": True,
        "no_manager_contract_text_hardcodes_grokfast_behavior": True,
        "no_food_kb_source_references_provider_profile": True,
        "decision_pack_separates_provider_diagnostic_evidence_from_product_truth": True,
        "live_artifacts_always_carry_provider_profile_identity": True,
    }
    assert audit["blockers"] == []


def test_provider_independence_audit_blocks_provider_reference_in_product_semantics() -> None:
    module = importlib.import_module("scripts.build_accurate_intake_provider_independence_audit")

    offenders = module._provider_reference_offenders(  # noqa: SLF001 - audit unit contract.
        {"docs/quality/product_semantic.json": "workflow_effect: grok-4-fast_special_case"}
    )

    assert offenders == [
        {
            "path": "docs/quality/product_semantic.json",
            "provider_marker": "grok",
        }
    ]


def test_provider_independence_audit_scans_canonical_semantic_register() -> None:
    module = importlib.import_module("scripts.build_accurate_intake_provider_independence_audit")

    paths = [path.as_posix() for path in module.PRODUCT_SEMANTIC_PATHS]

    assert "docs/specs/WAVE_1_PHASE_B2_SEMANTIC_DECISION_REGISTER.md" in paths


def test_provider_independence_audit_validates_generated_artifact_shapes() -> None:
    module = importlib.import_module("scripts.build_accurate_intake_provider_independence_audit")

    audit = module.build_provider_independence_audit(
        decision_pack_artifact={
            "artifact_type": "accurate_intake_mvp_live_decision_pack",
            "claim_scope": "live_diagnostic_decision_pack",
            "production_selected": False,
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
            "live_provider_used_as_truth": False,
            "provider_robustness_summary": {"single_profile_only": True},
            "evidence_summary": {"live_invoked": True},
            "decision_boundary": {"production_manager_selected": False},
        },
        live_artifact={
            "artifact_type": "accurate_intake_mvp_live_diagnostic",
            "provider_profile_id": "builderspace-grok-4-fast-accurate-intake-mvp-live-diagnostic",
            "provider_profile_model": "grok-4-fast",
            "provider_profile_role": "accurate_intake_mvp_live_diagnostic",
            "production_selected": False,
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
            "live_provider_used_as_truth": False,
        },
    )

    assert audit["provider_independence_audit"][
        "decision_pack_separates_provider_diagnostic_evidence_from_product_truth"
    ] is True
    assert audit["provider_independence_audit"]["live_artifacts_always_carry_provider_profile_identity"] is True


def test_provider_independence_audit_blocks_generated_artifact_overclaim() -> None:
    module = importlib.import_module("scripts.build_accurate_intake_provider_independence_audit")

    audit = module.build_provider_independence_audit(
        decision_pack_artifact={
            "artifact_type": "accurate_intake_mvp_live_decision_pack",
            "production_selected": True,
            "provider_robustness_summary": {"single_profile_only": False},
            "decision_boundary": {"production_manager_selected": True},
        },
        live_artifact={
            "artifact_type": "accurate_intake_mvp_live_diagnostic",
            "provider_profile_id": "builderspace-grok-4-fast-accurate-intake-mvp-live-diagnostic",
            "provider_profile_model": "grok-4-fast",
            "production_selected": True,
        },
    )

    assert audit["passed"] is False
    assert "decision_pack_provider_evidence_truth_boundary_invalid" in audit["blockers"]
    assert "live_artifact_provider_identity_or_non_claim_invalid" in audit["blockers"]
