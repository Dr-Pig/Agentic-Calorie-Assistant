from __future__ import annotations

from app.recommendation.application.offer_live_diagnostic_summary import (
    summarize_recommendation_offer_live_diagnostic,
)


def test_offer_live_diagnostic_summary_accepts_passed_grokfast_offer_node() -> None:
    summary = summarize_recommendation_offer_live_diagnostic(
        {
            "artifact_type": "recommendation_three_node_live_diagnostic",
            "status": "pass",
            "provider_mode": "live_builderspace_grokfast_diagnostic",
            "live_requested": True,
            "live_invoked": True,
            "live_provider_invoked": True,
            "node_status_by_physical_node": {
                "recommendation_planning": "pass",
                "offer_synthesis": "pass",
            },
            "node_provider_used_by_physical_node": {
                "recommendation_planning": True,
                "offer_synthesis": True,
            },
            "deterministic_guard_replayed": True,
            "recommendation_response": {
                "candidate_id": "golden-1",
                "recommendation_served": False,
                "intake_commit_requested": False,
                "is_canonical_truth": False,
            },
            "activation_flags": {
                "mainline_runtime_connected": False,
                "canonical_product_mutation_allowed": False,
                "user_facing_behavior_changed": False,
            },
            "blockers": [],
        }
    )

    assert summary == {
        "artifact_type": "recommendation_offer_grokfast_live_diagnostic_summary",
        "status": "pass",
        "source_artifact_type": "recommendation_three_node_live_diagnostic",
        "provider_mode": "live_builderspace_grokfast_diagnostic",
        "live_grokfast_offer_diagnostic_pass": True,
        "offer_synthesis_provider_used": True,
        "deterministic_guard_replayed": True,
        "selected_candidate_id": "golden-1",
        "recommendation_served": False,
        "intake_committed": False,
        "canonical_product_mutation_allowed": False,
        "mainline_runtime_connected": False,
        "user_facing_behavior_changed": False,
        "semantic_quality_claimed": False,
        "blockers": [],
    }


def test_offer_live_diagnostic_summary_blocks_serving_or_mutation_claims() -> None:
    summary = summarize_recommendation_offer_live_diagnostic(
        {
            "artifact_type": "recommendation_three_node_live_diagnostic",
            "status": "pass",
            "provider_mode": "live_builderspace_grokfast_diagnostic",
            "live_requested": True,
            "live_invoked": True,
            "live_provider_invoked": True,
            "node_status_by_physical_node": {"offer_synthesis": "pass"},
            "node_provider_used_by_physical_node": {"offer_synthesis": True},
            "deterministic_guard_replayed": True,
            "recommendation_response": {
                "candidate_id": "golden-1",
                "recommendation_served": True,
                "intake_commit_requested": True,
                "is_canonical_truth": True,
            },
            "activation_flags": {
                "mainline_runtime_connected": True,
                "canonical_product_mutation_allowed": True,
                "user_facing_behavior_changed": True,
            },
            "blockers": [],
        }
    )

    assert summary["status"] == "blocked"
    assert summary["live_grokfast_offer_diagnostic_pass"] is False
    assert summary["blockers"] == [
        "recommendation_response.recommendation_served_true",
        "recommendation_response.intake_commit_requested_true",
        "recommendation_response.is_canonical_truth_true",
        "activation_flags.mainline_runtime_connected_true",
        "activation_flags.canonical_product_mutation_allowed_true",
        "activation_flags.user_facing_behavior_changed_true",
    ]


def test_recommendation_train_records_pr19_completion_and_next_active_slice() -> None:
    import yaml

    with open(
        "docs/quality/advanced_product_lab_recommendation_pr_train.yaml",
        encoding="utf-8-sig",
    ) as handle:
        plan = yaml.safe_load(handle)

    assert plan["dynamic_remaining_pr_count"] <= 5
    assert plan["last_completed_pr_number"] >= 19
    assert plan["active_pr_number"] is None or plan["active_pr_number"] >= 20
    assert {
        "pr_number": 19,
        "pull_request": "local_logical_slice",
        "merge_commit": "working_branch_uncommitted",
        "result": "recommendation_offer_grokfast_live_diagnostic_completed_locally",
        "live_artifact": (
            "artifacts/advanced_product_lab_recommendation_offer_grokfast_"
            "diagnostic_pr19_live.json"
        ),
    } in plan["last_merge_evidence"]["completed_prs"]
