from __future__ import annotations

import json
from pathlib import Path

from scripts.build_accurate_intake_mvp_live_cost_summary import (
    build_accurate_intake_live_cost_summary,
    write_accurate_intake_live_cost_summary,
)


def _live_artifact(
    *,
    usage: dict[str, int] | None,
    estimated_cost_usd: float | None = None,
    stage_id: str = "provider_health_smoke",
    latency_ms: int = 321,
    provider_invocation_count: int = 1,
) -> dict[str, object]:
    provider_trace: dict[str, object] = {}
    if usage is not None:
        provider_trace["usage"] = usage
    if estimated_cost_usd is not None:
        provider_trace["estimated_cost_usd"] = estimated_cost_usd
    return {
        "artifact_type": "accurate_intake_mvp_live_diagnostic",
        "generated_at_utc": "2026-05-03T00:00:00Z",
        "claim_scope": "live_diagnostic",
        "provider_profile_id": "builderspace-grok-4-fast-accurate-intake-mvp-live-diagnostic",
        "provider_profile_model": "grok-4-fast",
        "readiness_claimed": False,
        "product_readiness_claimed": False,
        "private_self_use_approved": False,
        "production_selected": False,
        "mutation_rollout_approved": False,
        "runtime_web_activation_approved": False,
        "live_provider_used_as_truth": False,
        "stages": [
            {
                "stage_id": stage_id,
                "status": "pass",
                "latency_ms": latency_ms,
                "timeout_budget_ms": 180000,
                "result_kind": "strict_pass_first_attempt",
            }
        ],
        "provider_invocations": [
            {
                "stage": stage_id,
                "provider_profile_id": "builderspace-grok-4-fast-accurate-intake-mvp-live-diagnostic",
                "provider_profile_model": "grok-4-fast",
                "latency_ms": latency_ms,
                "timeout_budget_ms": 180000,
                "provider_trace": provider_trace,
            }
            for _ in range(provider_invocation_count)
        ],
    }


def test_live_cost_summary_totals_token_usage_and_reported_costs() -> None:
    summary = build_accurate_intake_live_cost_summary(
        [
            _live_artifact(
                usage={"prompt_tokens": 12, "completion_tokens": 8, "total_tokens": 20},
                estimated_cost_usd=0.004,
            )
        ],
        source_paths=[Path("artifacts/run_a/provider_health.json")],
    )

    assert summary["artifact_type"] == "accurate_intake_mvp_live_cost_summary"
    assert summary["claim_scope"] == "live_diagnostic_cost_summary"
    assert "readiness_claimed" not in summary
    assert "product_readiness_claimed" not in summary
    assert "private_self_use_approved" not in summary
    assert "production_selected" not in summary
    assert summary["summary"] == {
        "source_artifact_count": 1,
        "stage_count": 1,
        "provider_invocation_count": 1,
        "total_stage_latency_ms": 321,
        "max_stage_latency_ms": 321,
        "total_provider_invocation_latency_ms": 321,
        "max_provider_invocation_latency_ms": 321,
        "usage_record_count": 1,
        "prompt_tokens": 12,
        "completion_tokens": 8,
        "total_tokens": 20,
        "max_prompt_tokens_per_usage_record": 12,
        "cached_prompt_tokens": 0,
        "cache_reporting_call_count": 0,
        "cache_hit_call_count": 0,
        "reported_cost_record_count": 1,
        "reported_cost_usd": 0.004,
        "cost_unavailable_without_pricing": False,
    }
    assert summary["latency_root_cause_hints"]["provider_invocation_count_high"] is False
    assert summary["latency_root_cause_hints"]["prompt_cache_metrics_missing"] is True
    assert summary["source_artifacts"][0]["sha256"]


def test_live_cost_summary_marks_cost_unavailable_when_tokens_have_no_pricing() -> None:
    summary = build_accurate_intake_live_cost_summary(
        [_live_artifact(usage={"input_tokens": 10, "output_tokens": 6, "total_tokens": 16})],
        source_paths=[Path("artifacts/run_b/schema_probe.json")],
    )

    assert summary["summary"]["usage_record_count"] == 1
    assert summary["summary"]["prompt_tokens"] == 10
    assert summary["summary"]["completion_tokens"] == 6
    assert summary["summary"]["total_tokens"] == 16
    assert summary["summary"]["reported_cost_record_count"] == 0
    assert summary["summary"]["reported_cost_usd"] is None
    assert summary["summary"]["cost_unavailable_without_pricing"] is True
    assert summary["cost_policy"] == {
        "billing_truth_source": "provider_reported_artifact_fields_only",
        "token_counts_are_not_billing_truth": True,
        "pricing_table_applied": False,
        "cost_unavailable_without_pricing": True,
    }


def test_live_cost_summary_flags_latency_root_cause_probe_without_readiness_claim() -> None:
    summary = build_accurate_intake_live_cost_summary(
        [
            _live_artifact(
                stage_id="single_case_live_probe",
                latency_ms=135_000,
                provider_invocation_count=10,
                usage={
                    "prompt_tokens": 17_000,
                    "completion_tokens": 450,
                    "total_tokens": 17_450,
                    "prompt_tokens_details": {"cached_tokens": 0},
                },
            )
        ]
    )

    assert summary["summary"]["provider_invocation_count"] == 10
    assert summary["summary"]["total_stage_latency_ms"] == 135_000
    assert summary["summary"]["max_prompt_tokens_per_usage_record"] == 17_000
    assert summary["summary"]["cache_reporting_call_count"] == 10
    assert summary["summary"]["cache_hit_call_count"] == 0
    assert summary["latency_root_cause_hints"] == {
        "provider_invocation_count_high": True,
        "stage_latency_high": True,
        "prompt_token_volume_high": True,
        "prompt_cache_metrics_missing": False,
        "prompt_cache_hits_missing": True,
        "output_tokens_not_primary_driver": True,
    }
    assert summary["latency_optimization_priorities"] == [
        "attribute_provider_invocations_to_manager_rounds",
        "reduce_provider_request_count_per_user_turn",
        "compact_dynamic_context_packets_before_full_suite",
        "move_stable_tool_schema_prefix_before_dynamic_payload",
        "monitor_cached_tokens_before_repeating_runs",
    ]
    assert summary["generated_artifact_policy"]["local_diagnostic_evidence_only"] is True
    assert "readiness_claimed" not in summary


def test_live_cost_summary_omits_fixed_false_claim_fields() -> None:
    summary = build_accurate_intake_live_cost_summary([_live_artifact(usage={"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2})])

    for field in (
        "readiness_claimed",
        "product_readiness_claimed",
        "private_self_use_approved",
        "production_selected",
        "mutation_rollout_approved",
        "runtime_web_activation_approved",
        "model_portability_claimed",
    ):
        assert field not in summary


def test_live_cost_summary_writer_creates_run_specific_local_artifact(tmp_path: Path) -> None:
    source = tmp_path / "run_c" / "provider_health.json"
    source.parent.mkdir(parents=True)
    source.write_text(
        json.dumps(_live_artifact(usage={"prompt_tokens": 3, "completion_tokens": 2, "total_tokens": 5})),
        encoding="utf-8",
    )
    output_path = tmp_path / "run_c" / "accurate_intake_mvp_live_cost_summary_run_c.json"

    output = write_accurate_intake_live_cost_summary(
        artifact_paths=[source],
        output_path=output_path,
    )

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert output == output_path
    assert payload["artifact_type"] == "accurate_intake_mvp_live_cost_summary"
    assert payload["summary"]["total_tokens"] == 5
    assert payload["generated_artifact_policy"] == {
        "commit_as_repo_truth": False,
        "local_diagnostic_evidence_only": True,
    }
