from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = (
    ROOT / "docs" / "quality" / "advanced_product_lab_rescue_phase1_pr_train.yaml"
)
DOC_INDEX_PATH = ROOT / "docs" / "DOC_INDEX.md"


def _plan() -> dict:
    return yaml.safe_load(PLAN_PATH.read_text(encoding="utf-8-sig"))


def test_rescue_phase1_train_records_twenty_four_right_sized_prs() -> None:
    plan = _plan()

    assert plan["artifact_type"] == "advanced_product_lab_rescue_phase1_pr_train"
    assert plan["status"] == "active"
    assert plan["planned_pr_count"] == 24
    assert plan["dynamic_remaining_pr_count"] == 11
    assert plan["last_completed_pr_number"] == 13
    assert (
        plan["planned_pr_count"] - plan["last_completed_pr_number"]
        == plan["dynamic_remaining_pr_count"]
    )

    prs = plan["pr_train"]
    assert len(prs) == 24
    assert [item["pr_number"] for item in prs] == list(range(1, 25))
    assert prs[0]["slice_id"] == "rescue_phase1_spec_to_slice_reconciliation"
    assert prs[-1]["slice_id"] == "rescue_phase1_integrated_e2e_decision_pack"
    assert len({item["slice_id"] for item in prs}) == 24


def test_rescue_phase1_train_keeps_lab_completion_separate_from_mainline_activation() -> None:
    plan = _plan()
    strategy = plan["branch_strategy"]

    assert strategy["target_branch"] == "codex/advanced-product-lab"
    assert strategy["lab_runtime_surface_may_be_complete"] is True
    assert strategy["lab_user_facing_surfaces_allowed"] is True
    assert strategy["lab_isolated_mutation_ledger_allowed"] is True
    assert strategy["live_grokfast_diagnostics_allowed"] is True
    assert strategy["kimi_live_calls_allowed"] is False
    assert strategy["mainline_activation_enabled"] is False
    assert strategy["self_use_v1_affected"] is False

    required_flags = plan["required_artifact_flags"]
    assert required_flags["lab_enabled"] is True
    assert required_flags["mainline_activation_enabled"] is False
    assert required_flags["mainline_runtime_connected"] is False
    assert required_flags["mainline_route_or_api_mount_allowed"] is False
    assert required_flags["production_scheduler_delivery_allowed"] is False
    assert required_flags["canonical_product_db_mutation_allowed"] is False
    assert required_flags["manager_context_packet_changed_in_mainline"] is False


def test_rescue_phase1_train_covers_canonical_rescue_spec_inputs() -> None:
    plan = _plan()
    refs = set(plan["spec_coverage_matrix"]["canonical_source_refs"])

    assert {
        "docs/specs/L0_PRODUCT_CAPABILITY_SPEC.md",
        "docs/specs/L1_RUNTIME_OWNERSHIP_SPEC.md",
        "docs/specs/L2_DATA_STATE_SPEC.md",
        "docs/specs/L3_4_RESCUE_RUNTIME_CONTRACT_SPEC.md",
        "docs/specs/L3M_GUARDRAIL_MATH_SPEC.md",
        "docs/specs/L4B_RETRIEVAL_POLICY_SPEC.md",
        "docs/specs/L4C_CONTEXT_PACKING_SPEC.md",
        "docs/specs/L3_6_PROACTIVE_SCHEDULER_SPEC.md",
        "docs/quality/UX_JOURNEY_TO_SLICE_MAP.md",
    }.issubset(refs)

    clauses = {
        item["coverage_id"]: item for item in plan["spec_coverage_matrix"]["required_clauses"]
    }
    assert clauses["intake_rescue_separation"]["first_pr"] == 10
    assert clauses["guardrail_math_and_safety_floor"]["first_pr"] == 5
    assert clauses["proposal_container_accept_dismiss"]["first_pr"] == 15
    assert clauses["planned_event_budget_allocation"]["first_pr"] == 12
    assert clauses["proactive_rescue_nudge_boundary"]["first_pr"] == 22
    assert clauses["integrated_journey_f_f2_t"]["first_pr"] == 24


def test_rescue_phase1_train_declares_dynamic_estimate_protocol() -> None:
    plan = _plan()
    protocol = plan["dynamic_estimate_protocol"]

    assert protocol["update_after_each_merge"] is True
    assert protocol["estimate_may_increase"] is True
    assert protocol["estimate_may_decrease"] is True
    assert protocol["do_not_use_chat_memory_as_only_plan"] is True
    assert (
        "docs/quality/advanced_product_lab_rescue_phase1_pr_train.yaml"
        in protocol["persistent_truth_files"]
    )
    assert protocol["update_fields"] == [
        "dynamic_remaining_pr_count",
        "last_completed_pr_number",
        "last_merge_evidence",
        "estimate_notes",
    ]


def test_rescue_phase1_train_assigns_semantic_ownership_without_llm_math_truth() -> None:
    plan = _plan()
    boundary = plan["llm_deterministic_boundary"]
    owner = plan["semantic_owner"]

    assert boundary["decision_surface"] == "rescue_phase1_runtime_lab"
    assert boundary["truth_owner"] == "hybrid"
    assert boundary["deterministic_role"] == [
        "derive_budget_math",
        "validate_viability",
        "reject_illegal_mutation",
        "derive_effective_from",
        "project_lab_commit_effect",
    ]
    assert boundary["llm_role"] == [
        "shape_proposal_language",
        "present_response",
        "classify_negotiation_when_contract_backed",
    ]
    assert "daily_kcal_adjustment" in boundary["do_not_override"]
    assert owner["mutation_legality"] == "ProposalContainer_and_LedgerEntry_validators"


def test_rescue_phase1_train_names_live_and_e2e_milestones() -> None:
    plan = _plan()

    milestone_ids = {item["milestone_id"] for item in plan["milestones"]}
    assert {
        "fixture_golden_set_replay",
        "simulated_self_use_trace_replay",
        "grokfast_rescue_proposal_shaping_diagnostic",
        "grokfast_rescue_response_presentation_diagnostic",
        "lab_accept_dismiss_e2e",
        "integrated_f_f2_t_e2e_decision_pack",
    }.issubset(milestone_ids)
    assert all(
        item["provider_profile"] in {"none", "builderspace-grok-4-fast"}
        for item in plan["milestones"]
    )


def test_rescue_phase1_train_is_indexed_without_becoming_bootstrap_truth() -> None:
    doc_index = DOC_INDEX_PATH.read_text(encoding="utf-8-sig")

    assert "advanced_product_lab_rescue_phase1_pr_train.yaml" in doc_index
    assert "advanced rescue Phase 1 PR train" in doc_index
    assert "advanced_product_lab_rescue_phase1_pr_train.yaml" not in doc_index[
        doc_index.index("## Active Bootstrap") : doc_index.index("## Active Truth Rules")
    ]
