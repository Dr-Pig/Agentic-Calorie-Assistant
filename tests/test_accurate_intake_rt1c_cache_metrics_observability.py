from __future__ import annotations

from app.runtime.infrastructure.trace.text_meal_observability import (
    build_trace_envelope,
    compute_token_usage,
)


def test_compute_token_usage_normalizes_openai_cached_prompt_tokens() -> None:
    usage = compute_token_usage(
        [
            {
                "usage": {
                    "prompt_tokens": 1200,
                    "completion_tokens": 120,
                    "prompt_tokens_details": {"cached_tokens": 960},
                }
            },
            {
                "usage": {
                    "prompt_tokens": 400,
                    "completion_tokens": 80,
                    "prompt_tokens_details": {"cached_tokens": 0},
                }
            },
        ]
    )

    assert usage == {
        "total_prompt_tokens": 1600,
        "total_completion_tokens": 200,
        "total_tokens": 1800,
        "llm_call_count": 2,
        "total_cached_prompt_tokens": 960,
        "total_cached_prompt_tokens_observed": 960,
        "total_uncached_prompt_tokens": 640,
        "known_uncached_prompt_tokens": 640,
        "cache_reporting_missing_count": 0,
        "cache_reporting_call_count": 2,
        "cache_hit_call_count": 1,
        "cached_prompt_tokens_known": True,
        "uncached_prompt_tokens_known": True,
        "prompt_cache_reporting_observed": True,
        "prompt_cache_hit_observed": True,
    }


def test_compute_token_usage_supports_input_output_style_cache_reporting() -> None:
    usage = compute_token_usage(
        [
            {
                "usage": {
                    "input_tokens": 1400,
                    "output_tokens": 200,
                    "input_tokens_details": {"cached_tokens": 1024},
                }
            },
            {
                "usage": {
                    "input_tokens": 320,
                    "output_tokens": 40,
                }
            },
        ]
    )

    assert usage["total_prompt_tokens"] == 1720
    assert usage["total_completion_tokens"] == 240
    assert usage["total_cached_prompt_tokens"] == 1024
    assert usage["total_cached_prompt_tokens_observed"] == 1024
    assert usage["total_uncached_prompt_tokens"] is None
    assert usage["known_uncached_prompt_tokens"] == 376
    assert usage["cache_reporting_missing_count"] == 1
    assert usage["cache_reporting_call_count"] == 1
    assert usage["cache_hit_call_count"] == 1
    assert usage["cached_prompt_tokens_known"] is False
    assert usage["uncached_prompt_tokens_known"] is False
    assert usage["prompt_cache_reporting_observed"] is True
    assert usage["prompt_cache_hit_observed"] is True


def test_compute_token_usage_supports_cache_read_and_creation_usage_fields() -> None:
    usage = compute_token_usage(
        [
            {
                "usage": {
                    "input_tokens": 50,
                    "output_tokens": 10,
                    "cache_read_input_tokens": 1000,
                    "cache_creation_input_tokens": 250,
                }
            }
        ]
    )

    assert usage["total_prompt_tokens"] == 1300
    assert usage["total_completion_tokens"] == 10
    assert usage["total_tokens"] == 1310
    assert usage["total_cached_prompt_tokens"] == 1000
    assert usage["total_cached_prompt_tokens_observed"] == 1000
    assert usage["total_uncached_prompt_tokens"] == 300
    assert usage["known_uncached_prompt_tokens"] == 300
    assert usage["cache_reporting_call_count"] == 1
    assert usage["cache_hit_call_count"] == 1
    assert usage["cached_prompt_tokens_known"] is True
    assert usage["uncached_prompt_tokens_known"] is True


def test_build_trace_envelope_carries_cache_metrics_into_trace_contract() -> None:
    envelope = build_trace_envelope(
        request_id="rt1c-request",
        user_id="u-1",
        timestamp="2026-05-08T00:00:00Z",
        provider_name="fake_provider",
        schema_signature="schema-v1",
        source_page_version="page-v1",
        trace_contract={
            "route_family": "intake",
            "manager_output": {"intent": "log_meal"},
            "followup_policy_decision": "optional_refinement",
            "followup_decision": "ask_size_then_commit",
            "grounding_summary": {},
            "grounding_attempts": [],
            "persistence_decision": {},
            "retry_reason": None,
        },
        llm_traces=[
            {
                "stage": "manager_pass_1",
                "usage": {
                    "prompt_tokens": 1500,
                    "completion_tokens": 110,
                    "prompt_tokens_details": {"cached_tokens": 1280},
                },
            }
        ],
        debug_steps=[],
        quality_signals={},
        best_answer_source="primary",
        retry_triggered=False,
        multi_turn_context={"is_multi_turn": False},
    )

    assert envelope.token_usage["total_prompt_tokens"] == 1500
    assert envelope.token_usage["total_cached_prompt_tokens"] == 1280
    assert envelope.token_usage["cache_reporting_call_count"] == 1
    assert envelope.trace_contract["token_usage"] == envelope.token_usage
