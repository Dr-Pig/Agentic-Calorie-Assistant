from __future__ import annotations

from scripts.run_accurate_intake_rt1c_cache_metrics_observability import (
    build_rt1c_cache_metrics_observability_artifact,
)


def test_rt1c_cache_metrics_observability_artifact_passes_and_targets_gate() -> None:
    artifact = build_rt1c_cache_metrics_observability_artifact()

    assert artifact["status"] == "pass"
    assert artifact["target_manager_runtime_gate"] == "rt1c_cache_metrics_observability"
    assert artifact["pass_type"] == "contract"
    assert artifact["summary"]["case_count"] == 3
    assert artifact["summary"]["passed_case_count"] == 3


def test_rt1c_cache_metrics_observability_artifact_records_normalized_cache_metrics() -> None:
    artifact = build_rt1c_cache_metrics_observability_artifact()
    by_id = {case["case_id"]: case for case in artifact["cases"]}

    openai_usage = by_id["openai_prompt_cache_usage_is_normalized"]["observed"]
    assert openai_usage["total_cached_prompt_tokens"] == 960
    assert openai_usage["cache_reporting_call_count"] == 2
    assert openai_usage["cache_hit_call_count"] == 1

    input_output_usage = by_id["input_output_usage_cache_metrics_are_normalized"]["observed"]
    assert input_output_usage["total_prompt_tokens"] == 1720
    assert input_output_usage["total_completion_tokens"] == 240
    assert input_output_usage["total_cached_prompt_tokens"] == 1024

    trace_envelope = by_id["trace_envelope_carries_cache_metrics_summary"]["observed"]
    assert trace_envelope["token_usage"]["prompt_cache_reporting_observed"] is True
    assert trace_envelope["token_usage"]["total_cached_prompt_tokens"] == 1280
