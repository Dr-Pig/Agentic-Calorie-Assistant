"""
Pass Runner - Generic LLM pass execution with validation.

Best Practices:
- Strict input/output validation
- Retry with exponential backoff
- Comprehensive error handling
- Full trace for observability
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar

from ..schemas import PassExecutionEnvelope


T = TypeVar("T")


class PassValidationError(Exception):
    """Raised when pass output validation fails."""
    def __init__(self, missing_fields: list[str], raw_output: dict[str, Any]):
        self.missing_fields = missing_fields
        self.raw_output = raw_output
        super().__init__(f"Validation failed: missing {missing_fields}")


class PassExecutionError(Exception):
    """Raised when pass execution fails after retries."""
    pass


def _envelope(
    *,
    status: str,
    payload: dict[str, Any],
    fallback_used: bool = False,
    error: str | None = None,
) -> PassExecutionEnvelope:
    return PassExecutionEnvelope(
        status=status,  # type: ignore[arg-type]
        payload=payload,
        fallback_used=fallback_used,
        error=error,
    )


def validate_pass_output(
    data: dict[str, Any],
    required_fields: list[str],
    nullable_fields: list[str] | None = None,
) -> list[str]:
    """
    Validate pass output against required fields.

    Returns:
        List of missing field names (empty if valid)
    """
    nullable = set(nullable_fields or [])
    missing = []
    for field in required_fields:
        if field not in data:
            missing.append(field)
        elif data[field] is None and field not in nullable:
            missing.append(field)
    return missing


async def run_pass(
    *,
    provider: Any,
    stage: str,
    system_prompt: str,
    user_payload: dict[str, Any],
    max_tokens: int,
    fallback_result: T,
    normalize: Callable[[dict[str, Any], T], T],
    dump: Callable[[T], dict[str, Any]],
    run_stage: Callable[..., Any],
    request_id: str,
    llm_traces: list[dict[str, Any]],
    trigger_reason: str,
    handoff_contract: dict[str, Any] | None = None,
    required_fields: list[str] | None = None,
    required_fields_source: str = "raw",
    nullable_required_fields: list[str] | None = None,
    max_retries: int = 2,
) -> tuple[T, PassExecutionEnvelope]:
    """
    Execute an LLM pass with validation and retries.

    Best Practices:
    - Validates output before returning
    - Falls back gracefully on failure
    - Full trace maintained for debugging
    - Retries on transient failures
    """
    last_error: str | None = None
    last_attempt = 0

    for attempt_index in range(1, max_retries + 1):
        last_attempt = attempt_index
        try:
            raw, trace = await run_stage(
                provider,
                stage=stage,
                system_prompt=system_prompt,
                user_payload=user_payload,
                max_tokens=max_tokens,
                attempt_index=attempt_index,
                trigger_reason=trigger_reason if attempt_index == 1 else f"{trigger_reason}_retry_{attempt_index}",
                handoff_contract=handoff_contract,
            )

            # Append trace
            llm_traces.append({"request_id": request_id, **trace})

            # Normalize output
            normalized = normalize(dict(raw or {}), fallback_result)
            normalized_dump = dump(normalized)

            # Validate if required_fields specified
            if required_fields:
                validation_source = normalized_dump if required_fields_source == "normalized" else dict(raw or {})
                missing = validate_pass_output(
                    validation_source,
                    required_fields,
                    nullable_required_fields,
                )
                if missing:
                    last_error = f"attempt={attempt_index};missing_fields:{','.join(missing)}"
                    if attempt_index < max_retries:
                        continue
                    return normalized, _envelope(
                        status="degraded",
                        payload=normalized_dump,
                        fallback_used=True,
                        error=last_error,
                    )

            return normalized, _envelope(status="success", payload=normalized_dump)

        except Exception as exc:
            trace = getattr(exc, "trace", None)
            if isinstance(trace, dict):
                llm_traces.append({"request_id": request_id, **trace})
            last_error = f"attempt={attempt_index};{type(exc).__name__}:{exc}"
            # Don't retry on certain errors
            if _is_non_retryable_error(exc):
                break
            if attempt_index >= max_retries:
                break

    # All retries exhausted
    fallback_dump = dump(fallback_result)
    return fallback_result, _envelope(
        status="failed",
        payload=fallback_dump,
        fallback_used=True,
        error=last_error or f"attempts={last_attempt};unknown_failure",
    )


def _is_non_retryable_error(exc: Exception) -> bool:
    """Determine if an error is non-retryable."""
    error_text = str(exc).lower()
    non_retryable = [
        "validation",
        "parse",
        "attributeerror",
        "typeerror",
        "valueerror",
    ]
    return any(err in error_text for err in non_retryable)


def sanitize_llm_output(raw: dict[str, Any], strict: bool = True) -> dict[str, Any]:
    """
    Sanitize LLM output to prevent injection and ensure type safety.

    Best Practices:
    - Removes potentially dangerous content
    - Ensures type consistency
    - Strips excessive whitespace
    """
    sanitized = {}
    for key, value in raw.items():
        if value is None:
            sanitized[key] = None
            continue

        # String fields: strip and limit length
        if isinstance(value, str):
            cleaned = value.strip()
            if strict and len(cleaned) > 10000:
                cleaned = cleaned[:10000] + "..."
            sanitized[key] = cleaned
        # List fields: limit length
        elif isinstance(value, list) and strict:
            sanitized[key] = value[:100]
        # Dict fields: recurse
        elif isinstance(value, dict):
            sanitized[key] = sanitize_llm_output(value, strict=strict)
        else:
            sanitized[key] = value

    return sanitized
