from __future__ import annotations

from app.providers.builderspace_trace import normalize_usage_cache_metrics


def test_usage_cache_metrics_normalize_openai_cached_tokens_without_inventing_other_fields() -> None:
    usage = {
        "prompt_tokens": 2006,
        "completion_tokens": 300,
        "total_tokens": 2306,
        "prompt_tokens_details": {"cached_tokens": 1920},
    }

    metrics = normalize_usage_cache_metrics(usage)

    assert metrics == {
        "cache_metrics_available": True,
        "cached_tokens": 1920,
        "cache_read_input_tokens": None,
        "cache_creation_input_tokens": None,
    }


def test_usage_cache_metrics_normalize_anthropic_cache_read_and_creation_tokens() -> None:
    usage = {
        "input_tokens": 21,
        "output_tokens": 393,
        "cache_creation_input_tokens": 188086,
        "cache_read_input_tokens": 0,
    }

    metrics = normalize_usage_cache_metrics(usage)

    assert metrics == {
        "cache_metrics_available": True,
        "cached_tokens": None,
        "cache_read_input_tokens": 0,
        "cache_creation_input_tokens": 188086,
    }


def test_usage_cache_metrics_support_input_token_detail_cached_tokens() -> None:
    usage = {
        "input_tokens": 1400,
        "output_tokens": 200,
        "input_tokens_details": {"cached_tokens": 1024},
    }

    metrics = normalize_usage_cache_metrics(usage)

    assert metrics == {
        "cache_metrics_available": True,
        "cached_tokens": 1024,
        "cache_read_input_tokens": None,
        "cache_creation_input_tokens": None,
    }


def test_usage_cache_metrics_preserve_unavailable_cache_metrics_as_null_not_zero() -> None:
    usage = {"prompt_tokens": 42, "completion_tokens": 5, "total_tokens": 47}

    metrics = normalize_usage_cache_metrics(usage)

    assert metrics == {
        "cache_metrics_available": False,
        "cached_tokens": None,
        "cache_read_input_tokens": None,
        "cache_creation_input_tokens": None,
    }


def test_usage_cache_metrics_treat_missing_usage_as_unavailable() -> None:
    metrics = normalize_usage_cache_metrics(None)

    assert metrics == {
        "cache_metrics_available": False,
        "cached_tokens": None,
        "cache_read_input_tokens": None,
        "cache_creation_input_tokens": None,
    }
