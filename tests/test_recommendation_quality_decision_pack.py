from __future__ import annotations

from app.advanced_shadow_lab.recommendation_quality_decision_pack import (
    build_recommendation_quality_decision_pack,
)


def test_recommendation_quality_decision_pack_aggregates_all_required_evidence() -> None:
    pack = build_recommendation_quality_decision_pack(
        pr_train=_pr_train(),
        recommendation_runtime_artifact=_recommendation_runtime(),
        holdout_pack=_holdout_pack(),
        offer_live_diagnostic_summary=_offer_live_summary(),
        paired_lab_e2e_artifact=_paired_e2e(),
        latency_cost_omission_trace=_latency_trace(),
    )

    assert pack["artifact_type"] == "advanced_product_lab_recommendation_quality_decision_pack"
    assert pack["status"] == "pass"
    assert pack["planned_pr_count"] == 24
    assert pack["last_completed_pr_number"] == 21
    assert pack["evidence_summary"] == {
        "recommendation_runtime_passed": True,
        "holdout_pack_passed": True,
        "holdout_case_count": 4,
        "live_grokfast_offer_diagnostic_pass": True,
        "paired_lab_e2e_passed": True,
        "latency_cost_omission_trace_passed": True,
        "no_retry_expansion_enforced": True,
    }
    assert pack["ready_for_recommendation_mainline_dormancy_gate"] is True
    assert pack["ready_for_downstream_shadow_consumers"] is True
    assert pack["ready_for_mainline_activation"] is False
    assert pack["mainline_activation_enabled"] is False
    assert pack["canonical_product_mutation_allowed"] is False
    assert pack["blockers"] == []


def test_recommendation_quality_decision_pack_blocks_missing_live_or_activation_drift() -> None:
    live = _offer_live_summary()
    live["live_grokfast_offer_diagnostic_pass"] = False
    paired = _paired_e2e()
    paired["mainline_activation_enabled"] = True
    latency = _latency_trace()
    latency["no_retry_expansion_trace"]["retry_expansion_attempted"] = True

    pack = build_recommendation_quality_decision_pack(
        pr_train=_pr_train(),
        recommendation_runtime_artifact=_recommendation_runtime(),
        holdout_pack=_holdout_pack(status="blocked"),
        offer_live_diagnostic_summary=live,
        paired_lab_e2e_artifact=paired,
        latency_cost_omission_trace=latency,
    )

    assert pack["status"] == "blocked"
    assert pack["ready_for_recommendation_mainline_dormancy_gate"] is False
    assert pack["ready_for_mainline_activation"] is False
    assert pack["blockers"] == [
        "holdout_pack.status_not_pass",
        "offer_live_diagnostic.live_grokfast_not_passed",
        "paired_lab_e2e.mainline_activation_enabled",
        "latency_cost_omission_trace.retry_expansion_attempted",
    ]


def test_recommendation_train_records_pr22_completion_and_next_active_slice() -> None:
    import yaml

    with open(
        "docs/quality/advanced_product_lab_recommendation_pr_train.yaml",
        encoding="utf-8-sig",
    ) as handle:
        plan = yaml.safe_load(handle)

    assert plan["dynamic_remaining_pr_count"] == 2
    assert plan["last_completed_pr_number"] == 22
    assert plan["active_pr_number"] == 23
    assert plan["last_merge_evidence"]["completed_prs"][-1] == {
        "pr_number": 22,
        "pull_request": "local_logical_slice",
        "merge_commit": "working_branch_uncommitted",
        "result": "recommendation_quality_decision_pack_completed_locally",
    }


def _pr_train() -> dict[str, object]:
    return {
        "planned_pr_count": 24,
        "last_completed_pr_number": 21,
        "dynamic_remaining_pr_count": 3,
    }


def _recommendation_runtime() -> dict[str, object]:
    return {
        "artifact_type": "advanced_product_lab_recommendation_runtime_artifact",
        "status": "pass",
        "recommendation_served_to_lab": True,
        "mainline_activation_enabled": False,
        "canonical_product_mutation_allowed": False,
        "durable_product_memory_written": False,
        "manager_context_packet_changed": False,
    }


def _holdout_pack(status: str = "pass") -> dict[str, object]:
    return {
        "artifact_type": "advanced_product_lab_recommendation_holdout_pack",
        "status": status,
        "summary": {"case_count": 4, "pass_count": 4, "blocked_count": 0},
        "mainline_activation_enabled": False,
        "canonical_product_mutation_allowed": False,
    }


def _offer_live_summary() -> dict[str, object]:
    return {
        "artifact_type": "recommendation_offer_grokfast_live_diagnostic_summary",
        "status": "pass",
        "live_grokfast_offer_diagnostic_pass": True,
        "semantic_quality_claimed": False,
        "mainline_runtime_connected": False,
        "canonical_product_mutation_allowed": False,
    }


def _paired_e2e() -> dict[str, object]:
    return {
        "artifact_type": "advanced_product_lab_recommendation_paired_e2e",
        "status": "pass",
        "comparison": {
            "recommendation_tool_added": True,
            "pending_intake_handoff_added": True,
            "canonical_mutation_changed": False,
            "mainline_activation_changed": False,
            "manager_context_packet_changed": False,
        },
        "mainline_activation_enabled": False,
        "canonical_product_mutation_allowed": False,
    }


def _latency_trace() -> dict[str, object]:
    return {
        "artifact_type": "recommendation_latency_cost_omission_trace",
        "status": "pass",
        "latency_trace": {"latency_budget_exceeded": False},
        "no_retry_expansion_trace": {
            "retry_expansion_allowed": False,
            "retry_expansion_attempted": False,
            "expanded_context_after_budget_exceeded": False,
        },
        "mainline_activation_enabled": False,
        "canonical_product_mutation_allowed": False,
    }
