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
    provider_invocation_overrides: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    provider_trace: dict[str, object] = {}
    if usage is not None:
        provider_trace["usage"] = usage
    if estimated_cost_usd is not None:
        provider_trace["estimated_cost_usd"] = estimated_cost_usd
    if provider_invocation_overrides is None:
        provider_invocation_overrides = [{} for _ in range(provider_invocation_count)]
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
                "diagnostic_stage_id": override.get("diagnostic_stage_id", stage_id),
                "diagnostic_case_id": override.get("diagnostic_case_id"),
                "diagnostic_turn": override.get("diagnostic_turn"),
                "diagnostic_turn_kind": override.get("diagnostic_turn_kind"),
                "manager_round_index": override.get("manager_round_index"),
                "manager_loop_scope": override.get("manager_loop_scope"),
                "provider_trace_stage": override.get("provider_trace_stage"),
                "provider_profile_id": "builderspace-grok-4-fast-accurate-intake-mvp-live-diagnostic",
                "provider_profile_model": "grok-4-fast",
                "latency_ms": override.get("latency_ms", latency_ms),
                "timeout_budget_ms": 180000,
                "provider_trace": _provider_trace_for_override(provider_trace, override),
            }
            for override in provider_invocation_overrides
        ],
    }


def _provider_trace_for_override(
    base_provider_trace: dict[str, object],
    override: dict[str, object],
) -> dict[str, object]:
    override_trace = override.get("provider_trace")
    if isinstance(override_trace, dict):
        return dict(override_trace)
    return dict(base_provider_trace)


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
        "cached_prompt_tokens_observed": None,
        "cached_prompt_tokens_known": False,
        "cache_reporting_call_count": 0,
        "cache_hit_call_count": 0,
        "reported_cost_record_count": 1,
        "reported_cost_usd": 0.004,
        "cost_unavailable_without_pricing": False,
    }
    assert summary["latency_root_cause_hints"]["provider_invocation_count_high"] is False
    assert summary["latency_root_cause_hints"]["prompt_cache_metrics_missing"] is True
    assert summary["prompt_cache_reporting_capability"] == {
        "truth_source": "provider_reported_usage_only",
        "cache_reporting_status": "not_reported",
        "cached_token_count_status": "unknown_provider_not_reported",
        "usage_record_count": 1,
        "cache_reporting_call_count": 0,
        "cache_hit_call_count": 0,
        "cached_prompt_tokens": 0,
        "cached_prompt_tokens_observed": None,
        "cached_tokens_unknown": True,
        "cache_hit_claim_allowed": False,
        "cache_miss_claim_allowed": False,
        "zero_cached_tokens_claim_allowed": False,
        "latency_may_infer_cache_hit": False,
        "provider_passthrough_gap_possible": True,
        "requires_provider_usage_passthrough": True,
        "official_usage_field_candidates": [
            "prompt_tokens_details.cached_tokens",
            "input_tokens_details.cached_tokens",
            "cached_tokens",
            "cache_read_input_tokens",
            "cache_creation_input_tokens",
        ],
    }
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


def test_live_cost_summary_accepts_anthropic_cache_read_usage_field() -> None:
    summary = build_accurate_intake_live_cost_summary(
        [
            _live_artifact(
                usage={
                    "input_tokens": 100,
                    "output_tokens": 10,
                    "cache_read_input_tokens": 70,
                    "cache_creation_input_tokens": 30,
                },
            )
        ]
    )

    assert summary["summary"]["cache_reporting_call_count"] == 1
    assert summary["summary"]["cache_hit_call_count"] == 1
    assert summary["summary"]["cached_prompt_tokens"] == 70
    assert summary["prompt_cache_reporting_capability"]["cache_reporting_status"] == "cache_hit_reported"
    assert summary["prompt_cache_reporting_capability"]["cache_hit_claim_allowed"] is True
    assert summary["prompt_cache_reporting_capability"]["cache_miss_claim_allowed"] is False


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
        "stage_overhead_high": False,
        "turn_non_provider_runtime_high": False,
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


def test_live_cost_summary_breaks_down_latency_by_stage_case_turn_and_slowest_call() -> None:
    summary = build_accurate_intake_live_cost_summary(
        [
            _live_artifact(
                usage={
                    "prompt_tokens": 100,
                    "completion_tokens": 10,
                    "total_tokens": 110,
                    "prompt_tokens_details": {"cached_tokens": 70},
                },
                stage_id="single_case_live_probe",
                latency_ms=15_000,
                provider_invocation_overrides=[
                    {
                        "latency_ms": 3_000,
                        "diagnostic_case_id": "bubble_milk_tea_refinement",
                        "diagnostic_turn": 1,
                        "diagnostic_turn_kind": "new_meal",
                        "manager_round_index": 0,
                        "manager_loop_scope": "turn_entry_or_read_only",
                        "provider_trace_stage": "entry_decision",
                        "provider_trace": {
                            "stage": "entry_decision",
                            "usage": {
                                "prompt_tokens": 100,
                                "completion_tokens": 10,
                                "total_tokens": 110,
                                "prompt_tokens_details": {"cached_tokens": 70},
                            },
                            "transport_attempts": [
                                {"status": "success", "duration_ms": 2_800},
                            ],
                        },
                    },
                    {
                        "latency_ms": 1_000,
                        "diagnostic_case_id": "bubble_milk_tea_refinement",
                        "diagnostic_turn": 2,
                        "diagnostic_turn_kind": "followup_refinement",
                        "manager_round_index": 0,
                        "manager_loop_scope": "intake_execution",
                        "provider_trace_stage": "execution_decision",
                        "provider_trace": {
                            "stage": "execution_decision",
                            "usage": {
                                "prompt_tokens": 100,
                                "completion_tokens": 10,
                                "total_tokens": 110,
                                "prompt_tokens_details": {"cached_tokens": 70},
                            },
                            "transport_attempts": [
                                {"status": "parse_retry", "duration_ms": 600},
                                {"status": "success", "duration_ms": 300},
                            ],
                        },
                    },
                ],
            )
        ]
    )

    breakdown = summary["latency_breakdown"]
    assert breakdown["stage_latency_ms"] == 15_000
    assert breakdown["provider_invocation_latency_ms"] == 4_000
    assert breakdown["stage_overhead_ms"] == 11_000
    assert breakdown["unattributed_provider_invocation_count"] == 0
    assert breakdown["by_diagnostic_stage"][0] == {
        "source_index": 0,
        "diagnostic_stage_id": "single_case_live_probe",
        "stage_latency_ms": 15_000,
        "provider_invocation_count": 2,
        "provider_invocation_latency_ms": 4_000,
        "stage_overhead_ms": 11_000,
        "latency_share_pct": 100.0,
    }
    assert summary["latency_root_cause_hints"]["stage_overhead_high"] is True
    assert "attribute_stage_overhead_to_tool_db_renderer_spans" in summary["latency_optimization_priorities"]
    assert breakdown["by_case"][0]["diagnostic_case_id"] == "bubble_milk_tea_refinement"
    assert breakdown["by_case"][0]["provider_invocation_latency_ms"] == 4_000
    assert [turn["diagnostic_turn"] for turn in breakdown["by_turn"]] == [1, 2]
    assert {
        scope["manager_loop_scope"]: scope["provider_invocation_latency_ms"]
        for scope in breakdown["by_manager_loop_scope"]
    } == {"turn_entry_or_read_only": 3_000, "intake_execution": 1_000}
    assert breakdown["slowest_provider_invocations"][0] == {
        "source_index": 0,
        "invocation_index": 0,
        "stage": "single_case_live_probe",
        "diagnostic_stage_id": "single_case_live_probe",
        "diagnostic_case_id": "bubble_milk_tea_refinement",
        "diagnostic_turn": 1,
        "diagnostic_turn_kind": "new_meal",
        "manager_round_index": 0,
        "manager_loop_scope": "turn_entry_or_read_only",
        "provider_trace_stage": "entry_decision",
        "latency_ms": 3_000,
        "timeout_budget_ms": 180000,
        "prompt_tokens": 100,
        "completion_tokens": 10,
        "cached_tokens_reported": True,
        "cached_tokens": 70,
        "request_payload_utf8_bytes": 0,
        "stable_prefix_utf8_bytes": 0,
        "dynamic_suffix_utf8_bytes": 0,
        "provider_wrapper_overhead_ms": 200,
        "transport_attempt_count": 1,
        "transport_attempt_latency_ms": 2_800,
        "slowest_transport_attempt_ms": 2_800,
        "transport_attempt_statuses": ["success"],
    }


def test_live_cost_summary_aggregates_prompt_cache_identity_reuse() -> None:
    summary = build_accurate_intake_live_cost_summary(
        [
            _live_artifact(
                usage=None,
                stage_id="single_case_live_probe",
                latency_ms=24_000,
                provider_invocation_overrides=[
                    {
                        "latency_ms": 11_000,
                        "manager_loop_scope": "turn_entry_or_read_only",
                        "provider_trace": {
                            "usage": {"prompt_tokens": 7000, "completion_tokens": 300},
                            "prompt_cache_request": {
                                "identity_version": "provider_prompt_cache_request.v1",
                                "stable_prefix_sha256": "stable-a",
                                "stable_prefix_component_sha256": {
                                    "tools": "tools-a",
                                    "response_format": "schema-a",
                                    "system_messages": "system-a",
                                },
                                "stable_prefix_utf8_bytes": 2000,
                                "stable_prefix_component_utf8_bytes": {
                                    "tools": 1200,
                                    "response_format": 500,
                                    "system_messages": 300,
                                },
                                "dynamic_suffix_sha256": "dynamic-turn-1",
                                "dynamic_suffix_utf8_bytes": 3000,
                                "dynamic_suffix_component_utf8_bytes": {
                                    "user_messages": 3000,
                                },
                                "request_payload_utf8_bytes": 5100,
                                "provider_request_includes_prompt_cache_key": False,
                                "cache_truth_source": "provider_reported_usage_only",
                            },
                        },
                    },
                    {
                        "latency_ms": 12_000,
                        "manager_loop_scope": "intake_execution",
                        "provider_trace": {
                            "usage": {
                                "prompt_tokens": 8200,
                                "completion_tokens": 320,
                                "prompt_tokens_details": {"cached_tokens": 0},
                            },
                            "prompt_cache_request": {
                                "identity_version": "provider_prompt_cache_request.v1",
                                "stable_prefix_sha256": "stable-a",
                                "stable_prefix_component_sha256": {
                                    "tools": "tools-a",
                                    "response_format": "schema-a",
                                    "system_messages": "system-a",
                                },
                                "stable_prefix_utf8_bytes": 2000,
                                "stable_prefix_component_utf8_bytes": {
                                    "tools": 1200,
                                    "response_format": 500,
                                    "system_messages": 300,
                                },
                                "dynamic_suffix_sha256": "dynamic-turn-2",
                                "dynamic_suffix_utf8_bytes": 3500,
                                "dynamic_suffix_component_utf8_bytes": {
                                    "user_messages": 3500,
                                },
                                "request_payload_utf8_bytes": 5600,
                                "provider_request_includes_prompt_cache_key": False,
                                "cache_truth_source": "provider_reported_usage_only",
                            },
                        },
                    },
                ],
            )
        ]
    )

    assert summary["provider_invocation_records"][0]["prompt_cache_stable_prefix_sha256"] == "stable-a"
    assert summary["provider_invocation_records"][0]["prompt_cache_stable_prefix_component_sha256"] == {
        "tools": "tools-a",
        "response_format": "schema-a",
        "system_messages": "system-a",
    }
    assert summary["provider_invocation_records"][1]["prompt_cache_dynamic_suffix_sha256"] == "dynamic-turn-2"
    assert summary["provider_invocation_records"][1]["request_payload_utf8_bytes"] == 5600
    assert summary["provider_request_footprint_summary"] == {
        "measurement": "json_utf8_bytes_trace_only",
        "provider_usage_is_token_truth": True,
        "record_count": 2,
        "total_request_payload_utf8_bytes": 10700,
        "max_request_payload_utf8_bytes": 5600,
        "total_stable_prefix_utf8_bytes": 4000,
        "total_dynamic_suffix_utf8_bytes": 6500,
        "max_dynamic_suffix_utf8_bytes": 3500,
        "stable_prefix_component_utf8_bytes": {
            "response_format": 1000,
            "system_messages": 600,
            "tools": 2400,
        },
        "dynamic_suffix_component_utf8_bytes": {"user_messages": 6500},
        "largest_stable_prefix_component": {"component": "tools", "utf8_bytes": 2400},
        "largest_dynamic_suffix_component": {"component": "user_messages", "utf8_bytes": 6500},
    }
    assert summary["prompt_cache_identity_summary"] == {
        "provider_trace_identity_count": 2,
        "missing_identity_count": 0,
        "stable_prefix_unique_count": 1,
        "dynamic_suffix_unique_count": 2,
        "repeated_stable_prefix_observed": True,
        "same_prefix_multiple_dynamic_suffix_observed": True,
        "provider_request_prompt_cache_key_count": 0,
        "cache_reporting_call_count": 1,
        "cache_hit_call_count": 0,
        "stable_prefix_groups": [
            {
                "stable_prefix_sha256": "stable-a",
                "provider_invocation_count": 2,
                "dynamic_suffix_unique_count": 2,
                "cache_reporting_call_count": 1,
                "cache_hit_call_count": 0,
            }
        ],
    }


def test_live_cost_summary_attributes_turn_runtime_without_changing_semantics() -> None:
    artifact = _live_artifact(
        usage={"prompt_tokens": 100, "completion_tokens": 10, "total_tokens": 110},
        stage_id="single_case_live_probe",
        latency_ms=18_000,
        provider_invocation_overrides=[
            {
                "latency_ms": 3_000,
                "diagnostic_case_id": "bubble_milk_tea_refinement",
                "diagnostic_turn": 1,
                "diagnostic_turn_kind": "new_meal",
                "manager_loop_scope": "intake_execution",
            }
        ],
    )
    artifact["cases"] = [
        {
            "case_id": "bubble_milk_tea_refinement",
            "stage_id": "single_case_live_probe",
            "turns": [
                {
                    "turn": 1,
                    "kind": "new_meal",
                    "latency_ms": 12_000,
                    "non_provider_latency_ms": 9_000,
                    "provider_invocation_summary": {
                        "provider_invocation_count": 1,
                        "provider_invocation_latency_ms": 3_000,
                        "prompt_tokens": 100,
                        "completion_tokens": 10,
                        "cached_tokens": 0,
                        "cache_reporting_call_count": 0,
                    },
                }
            ],
        }
    ]

    summary = build_accurate_intake_live_cost_summary([artifact])

    breakdown = summary["latency_breakdown"]
    assert breakdown["turn_latency_ms"] == 12_000
    assert breakdown["turn_non_provider_latency_ms"] == 9_000
    assert breakdown["max_turn_non_provider_latency_ms"] == 9_000
    assert breakdown["by_case_turn_runtime"] == [
        {
            "source_index": 0,
            "diagnostic_stage_id": "single_case_live_probe",
            "diagnostic_case_id": "bubble_milk_tea_refinement",
            "diagnostic_turn": 1,
            "diagnostic_turn_kind": "new_meal",
            "turn_latency_ms": 12_000,
            "provider_invocation_count": 1,
            "provider_invocation_latency_ms": 3_000,
            "non_provider_latency_ms": 9_000,
            "prompt_tokens": 100,
            "completion_tokens": 10,
            "cached_tokens": 0,
            "cache_reporting_call_count": 0,
            "latency_share_pct": 100.0,
        }
    ]
    assert breakdown["slowest_turn_runtime_segments"][0]["non_provider_latency_ms"] == 9_000
    assert summary["latency_root_cause_hints"]["turn_non_provider_runtime_high"] is True
    assert "attribute_turn_non_provider_runtime_to_db_guard_renderer_spans" in summary["latency_optimization_priorities"]
    assert "readiness_claimed" not in summary


def test_live_cost_summary_classifies_product_turn_latency_slo_without_readiness_claim() -> None:
    summary = build_accurate_intake_live_cost_summary(
        [
            _live_artifact(
                usage={"prompt_tokens": 100, "completion_tokens": 10, "total_tokens": 110},
                stage_id="single_case_live_probe",
                latency_ms=45_000,
                provider_invocation_overrides=[
                    {
                        "latency_ms": 7_000,
                        "diagnostic_case_id": "remaining_budget_query",
                        "diagnostic_turn": 1,
                        "diagnostic_turn_kind": "budget_query",
                        "manager_loop_scope": "turn_entry_or_read_only",
                    },
                    {
                        "latency_ms": 13_000,
                        "diagnostic_case_id": "chicken_rice_log",
                        "diagnostic_turn": 1,
                        "diagnostic_turn_kind": "new_meal",
                        "manager_loop_scope": "intake_execution",
                    },
                    {
                        "latency_ms": 21_000,
                        "diagnostic_case_id": "bubble_milk_tea_refinement",
                        "diagnostic_turn": 2,
                        "diagnostic_turn_kind": "followup_refinement",
                        "manager_loop_scope": "intake_execution",
                    },
                ],
            )
        ]
    )

    latency_slo = summary["latency_slo"]
    assert latency_slo["diagnostic_only_not_readiness"] is True
    assert latency_slo["summary"]["single_sample_hard_budget_exceeded"] is True
    assert latency_slo["summary"]["single_sample_over_interactive_budget"] is True
    rows_by_turn_kind = {
        row["diagnostic_turn_kind"]: row
        for row in latency_slo["provider_turn_budget"]["rows"]
    }
    assert rows_by_turn_kind["budget_query"]["latency_class"] == "read_only_or_entry"
    assert rows_by_turn_kind["budget_query"]["single_sample_status"] == "within_interactive_budget"
    assert rows_by_turn_kind["new_meal"]["latency_class"] == "intake_no_web"
    assert rows_by_turn_kind["new_meal"]["single_sample_status"] == "over_interactive_budget"
    assert rows_by_turn_kind["followup_refinement"]["latency_class"] == "intake_clarify_or_correction"
    assert rows_by_turn_kind["followup_refinement"]["single_sample_status"] == "hard_timeout_budget_exceeded"
    assert "readiness_claimed" not in summary


def test_live_cost_summary_flags_stage_overhead_against_latency_slo() -> None:
    summary = build_accurate_intake_live_cost_summary(
        [
            _live_artifact(
                usage={"prompt_tokens": 40, "completion_tokens": 8, "total_tokens": 48},
                stage_id="provider_health_smoke",
                latency_ms=197_000,
                provider_invocation_overrides=[
                    {
                        "latency_ms": 1_000,
                        "manager_loop_scope": "turn_entry_or_read_only",
                    }
                ],
            )
        ]
    )

    latency_slo = summary["latency_slo"]
    assert latency_slo["provider_turn_budget"]["rows"] == []
    assert latency_slo["manager_scope_budget"]["rows"][0]["single_sample_status"] == "within_interactive_budget"
    assert latency_slo["stage_overhead_budget"]["rows"][0]["observed_latency_ms"] == 196_000
    assert latency_slo["stage_overhead_budget"]["rows"][0]["single_sample_status"] == "stage_overhead_hard_budget_exceeded"
    assert latency_slo["summary"] == {
        "budget_row_source": "provider_turn_budget_or_manager_scope_fallback",
        "provider_invocation_count": 1,
        "budget_row_count": 1,
        "stage_overhead_row_count": 1,
        "single_sample_hard_budget_exceeded": True,
        "single_sample_over_interactive_budget": False,
        "single_sample_clean": False,
    }


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
