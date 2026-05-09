from __future__ import annotations

from typing import Any


def _coerce_int(value: Any) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return 0
        try:
            return int(value)
        except ValueError:
            return 0
    return 0


def _usage_dict(trace: dict[str, Any]) -> dict[str, Any]:
    usage = trace.get("usage", {}) or {}
    return usage if isinstance(usage, dict) else {}


def _cache_int(usage: dict[str, Any], key: str) -> int | None:
    if key in usage:
        return _coerce_int(usage.get(key))
    return None


def _extract_prompt_tokens(trace: dict[str, Any], usage: dict[str, Any]) -> int:
    if "prompt_tokens" in trace:
        return _coerce_int(trace.get("prompt_tokens"))
    if "prompt_tokens" in usage:
        return _coerce_int(usage.get("prompt_tokens"))
    cache_read_tokens = _cache_int(usage, "cache_read_input_tokens")
    cache_creation_tokens = _cache_int(usage, "cache_creation_input_tokens")
    if cache_read_tokens is not None or cache_creation_tokens is not None:
        return _coerce_int(usage.get("input_tokens")) + _coerce_int(cache_read_tokens) + _coerce_int(
            cache_creation_tokens
        )
    return _coerce_int(usage.get("input_tokens"))


def _extract_completion_tokens(trace: dict[str, Any], usage: dict[str, Any]) -> int:
    return _coerce_int(
        trace.get("completion_tokens")
        or usage.get("completion_tokens")
        or usage.get("output_tokens")
    )


def _extract_cached_prompt_tokens(usage: dict[str, Any]) -> int | None:
    prompt_details = usage.get("prompt_tokens_details")
    if isinstance(prompt_details, dict) and "cached_tokens" in prompt_details:
        return _coerce_int(prompt_details.get("cached_tokens"))
    input_details = usage.get("input_tokens_details")
    if isinstance(input_details, dict) and "cached_tokens" in input_details:
        return _coerce_int(input_details.get("cached_tokens"))
    if "cached_tokens" in usage:
        return _coerce_int(usage.get("cached_tokens"))
    cache_read_tokens = _cache_int(usage, "cache_read_input_tokens")
    cache_creation_tokens = _cache_int(usage, "cache_creation_input_tokens")
    if cache_read_tokens is not None or cache_creation_tokens is not None:
        return _coerce_int(cache_read_tokens)
    return None


def compute_token_usage(llm_traces: list[dict[str, Any]]) -> dict[str, Any]:
    total_prompt_tokens = 0
    total_completion_tokens = 0
    total_cached_prompt_tokens = 0
    known_uncached_prompt_tokens = 0
    cache_reporting_call_count = 0
    cache_hit_call_count = 0
    for trace in llm_traces:
        usage = _usage_dict(trace)
        prompt_tokens = _extract_prompt_tokens(trace, usage)
        total_prompt_tokens += prompt_tokens
        total_completion_tokens += _extract_completion_tokens(trace, usage)
        cached_prompt_tokens = _extract_cached_prompt_tokens(usage)
        if cached_prompt_tokens is not None:
            cache_reporting_call_count += 1
            total_cached_prompt_tokens += cached_prompt_tokens
            known_uncached_prompt_tokens += max(prompt_tokens - cached_prompt_tokens, 0)
            if cached_prompt_tokens > 0:
                cache_hit_call_count += 1
    cache_reporting_missing_count = max(0, len(llm_traces) - cache_reporting_call_count)
    cache_tokens_known = len(llm_traces) == cache_reporting_call_count
    return {
        "total_prompt_tokens": total_prompt_tokens,
        "total_completion_tokens": total_completion_tokens,
        "total_tokens": total_prompt_tokens + total_completion_tokens,
        "llm_call_count": len(llm_traces),
        "total_cached_prompt_tokens": total_cached_prompt_tokens,
        "total_cached_prompt_tokens_observed": total_cached_prompt_tokens if cache_reporting_call_count > 0 else None,
        "total_uncached_prompt_tokens": known_uncached_prompt_tokens if cache_tokens_known else None,
        "known_uncached_prompt_tokens": known_uncached_prompt_tokens,
        "cache_reporting_missing_count": cache_reporting_missing_count,
        "cache_reporting_call_count": cache_reporting_call_count,
        "cache_hit_call_count": cache_hit_call_count,
        "cached_prompt_tokens_known": cache_tokens_known,
        "uncached_prompt_tokens_known": cache_tokens_known,
        "prompt_cache_reporting_observed": cache_reporting_call_count > 0,
        "prompt_cache_hit_observed": cache_hit_call_count > 0,
    }

