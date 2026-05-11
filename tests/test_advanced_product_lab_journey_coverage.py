from __future__ import annotations

from pathlib import Path

from app.advanced_shadow_lab.product_lab_closure_summary import (
    build_product_lab_closure_summary,
)
from app.advanced_shadow_lab.product_lab_journey_coverage import (
    IN_SCOPE_JOURNEY_IDS,
    build_product_lab_journey_coverage_summary,
)


def test_product_lab_journey_coverage_maps_current_scope_and_gaps() -> None:
    summary = build_product_lab_journey_coverage_summary({})

    assert summary["in_scope_journey_ids"] == [
        "A",
        "B",
        "C",
        "D",
        "E",
        "F",
        "F2",
        "G",
        "H",
        "I",
        "J",
        "K",
        "L",
        "M",
        "N",
        "Q",
        "S",
        "T",
        "U",
        "V",
    ]
    assert summary["excluded_journey_ids"] == ["O", "P", "R"]
    assert summary["covered_by_existing_executable_evidence_journey_ids"] == [
        "A",
        "B",
        "C",
        "D",
        "E",
        "F",
        "F2",
        "G",
        "H",
        "I",
        "J",
        "K",
        "L",
        "M",
        "N",
        "Q",
        "S",
        "U",
    ]
    assert summary["implemented_but_missing_executable_scenario_journey_ids"] == ["T"]
    assert summary["product_capability_gap_journey_ids"] == ["V"]
    assert summary["advanced_product_lab_journey_coverage_closed"] is False
    assert summary["next_product_capability_slice"] == "weekly_insight_proactive_lab"


def test_product_lab_journey_coverage_rows_keep_claim_boundaries() -> None:
    summary = build_product_lab_journey_coverage_summary({})
    by_id = {row["journey_id"]: row for row in summary["journey_coverage_rows"]}

    assert list(by_id) == IN_SCOPE_JOURNEY_IDS
    assert by_id["Q"]["coverage_status"] == "covered_by_existing_executable_evidence"
    assert by_id["S"]["coverage_status"] == "covered_by_existing_executable_evidence"
    assert by_id["U"]["do_not_cross"] == [
        "no_body_plan_tdee_rewrite",
        "no_production_ledger_write",
        "no_scheduler_or_notification",
    ]
    assert by_id["V"]["truth_owner"] == "proactive_weekly_insight_product_spec"
    for row in by_id.values():
        assert row["claim_boundary"] == "coverage_index_not_readiness_claim"
        assert row["mainline_activation_allowed"] is False
        assert row["semantic_decision_inferred_by_runner"] is False


def test_product_lab_journey_coverage_evidence_refs_are_executable_files() -> None:
    root = Path(__file__).resolve().parents[1]
    summary = build_product_lab_journey_coverage_summary({})

    for row in summary["journey_coverage_rows"]:
        if row["coverage_status"] != "covered_by_existing_executable_evidence":
            continue
        for ref in row["executable_evidence_refs"]:
            assert (root / ref).exists(), ref


def test_product_lab_closure_summary_embeds_journey_gap_decision_gate() -> None:
    summary = build_product_lab_closure_summary(_closed_session())

    assert summary["advanced_product_lab_product_loop_closed"] is True
    assert summary["advanced_product_lab_journey_coverage_closed"] is False
    assert summary["product_capability_gap_journey_ids"] == ["V"]
    assert summary["implemented_but_missing_executable_scenario_journey_ids"] == ["T"]
    assert summary["new_report_family_created"] is False


def _closed_session() -> dict[str, object]:
    return {
        "status": "pass",
        "lab_memory_store_written": True,
        "lab_memory_context_injected": True,
        "product_recommendation_selected_candidate_ids": ["golden-1"],
        "product_proactive_delivery_packet_ready": True,
        "product_outputs_applied_to_chat_surface": True,
        "lab_chat_action_outcome_types": [
            "recommendation_intake_draft",
            "rescue_commit_confirmation",
            "pending_intake_confirmed_lab",
        ],
        "lab_rescue_action_decision_kinds": ["request_shorter_variant"],
        "lab_calibration_effect_applied_count": 1,
        "lab_chat_action_blockers": [],
        "mainline_activation_enabled": False,
        "canonical_product_mutation_allowed": False,
        "durable_product_memory_written": False,
        "production_scheduler_delivery_allowed": False,
    }
