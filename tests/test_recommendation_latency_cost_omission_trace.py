from __future__ import annotations

from app.recommendation.application.latency_cost_omission_trace import (
    build_recommendation_latency_cost_omission_trace,
)


def test_latency_cost_trace_accepts_under_budget_recommendation_artifact() -> None:
    trace = build_recommendation_latency_cost_omission_trace(
        recommendation_artifact=_recommendation_artifact(served=True),
        stage_latency_ms={
            "recommendation_planning": 420,
            "candidate_retrieval_guard_scoring": 25,
            "offer_synthesis": 560,
        },
        provider_cost_units={
            "recommendation_planning": 1.0,
            "offer_synthesis": 1.2,
        },
        latency_budget_ms=2_500,
    )

    assert trace["artifact_type"] == "recommendation_latency_cost_omission_trace"
    assert trace["status"] == "pass"
    assert trace["latency_trace"]["total_latency_ms"] == 1_005
    assert trace["latency_trace"]["latency_budget_exceeded"] is False
    assert trace["cost_trace"]["provider_node_count"] == 2
    assert trace["cost_trace"]["estimated_provider_cost_units"] == 2.2
    assert trace["degraded_omission_trace"] == {
        "required": False,
        "recommendation_context_omitted": False,
        "omission_reason": "",
        "source_omission_traces": [],
    }
    assert trace["no_retry_expansion_trace"] == {
        "retry_expansion_allowed": False,
        "retry_expansion_attempted": False,
        "expanded_context_after_budget_exceeded": False,
    }
    assert trace["mainline_activation_enabled"] is False
    assert trace["canonical_product_mutation_allowed"] is False
    assert trace["blockers"] == []


def test_latency_cost_trace_requires_omission_when_latency_budget_is_exceeded() -> None:
    trace = build_recommendation_latency_cost_omission_trace(
        recommendation_artifact=_recommendation_artifact(
            served=False,
            source_omissions=[
                {
                    "candidate_id": "generic-1",
                    "omission_reason": "generic_evidence_not_proactive",
                    "source_node": "candidate_retrieval_guard_scoring",
                }
            ],
        ),
        stage_latency_ms={
            "recommendation_planning": 1_200,
            "candidate_retrieval_guard_scoring": 100,
            "offer_synthesis": 1_400,
        },
        latency_budget_ms=2_000,
    )

    assert trace["status"] == "pass"
    assert trace["latency_trace"]["latency_budget_exceeded"] is True
    assert trace["degraded_omission_trace"] == {
        "required": True,
        "recommendation_context_omitted": True,
        "omission_reason": "latency_budget_exceeded",
        "source_omission_traces": [
            {
                "candidate_id": "generic-1",
                "omission_reason": "generic_evidence_not_proactive",
                "source_node": "candidate_retrieval_guard_scoring",
            }
        ],
    }
    assert trace["no_retry_expansion_trace"]["retry_expansion_attempted"] is False


def test_latency_cost_trace_blocks_serving_or_retry_expansion_after_budget_exceeded() -> None:
    trace = build_recommendation_latency_cost_omission_trace(
        recommendation_artifact=_recommendation_artifact(served=True),
        stage_latency_ms={
            "recommendation_planning": 1_200,
            "candidate_retrieval_guard_scoring": 100,
            "offer_synthesis": 1_400,
        },
        latency_budget_ms=2_000,
        retry_expansion_attempted=True,
        context_expansion_attempted=True,
    )

    assert trace["status"] == "blocked"
    assert trace["blockers"] == [
        "degraded_omission.recommendation_served_despite_latency_budget",
        "no_retry_expansion.retry_expansion_attempted",
        "no_retry_expansion.context_expanded_after_budget_exceeded",
    ]


def test_recommendation_train_records_pr21_completion_and_next_active_slice() -> None:
    import yaml

    with open(
        "docs/quality/advanced_product_lab_recommendation_pr_train.yaml",
        encoding="utf-8-sig",
    ) as handle:
        plan = yaml.safe_load(handle)

    assert plan["dynamic_remaining_pr_count"] <= 3
    assert plan["last_completed_pr_number"] >= 21
    assert plan["active_pr_number"] is None or plan["active_pr_number"] >= 22
    assert {
        "pr_number": 21,
        "pull_request": "local_logical_slice",
        "merge_commit": "working_branch_uncommitted",
        "result": "recommendation_latency_cost_omission_trace_completed_locally",
    } in plan["last_merge_evidence"]["completed_prs"]


def _recommendation_artifact(
    *,
    served: bool,
    source_omissions: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    return {
        "artifact_type": "advanced_product_lab_recommendation_runtime_artifact",
        "status": "pass",
        "physical_node_order": [
            "recommendation_planning",
            "candidate_retrieval_guard_scoring",
            "offer_synthesis",
        ],
        "recommendation_served_to_lab": served,
        "retrieval_guard_scoring": {
            "omission_traces": list(source_omissions or []),
        },
        "mainline_activation_enabled": False,
        "mainline_runtime_connected": False,
        "served_to_mainline_user": False,
        "canonical_product_mutation_allowed": False,
        "durable_product_memory_written": False,
        "manager_context_packet_changed": False,
    }
