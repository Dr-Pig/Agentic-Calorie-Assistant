from __future__ import annotations

from copy import deepcopy
from typing import Any


RECENT_CHAT_TOKEN_ESTIMATOR = "rough_cjk_aware_char_estimate_v1"


def build_recent_chat_window(
    turns: list[dict[str, Any]],
    *,
    max_recent_messages: int,
    max_recent_chars: int,
    max_recent_tokens: int,
    pending_followup: dict[str, Any] | None = None,
    pending_draft: dict[str, Any] | None = None,
    target_candidates: list[dict[str, Any]] | None = None,
    interaction_event: Any | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    max_recent_messages = max(0, int(max_recent_messages or 0))
    max_recent_chars = max(0, int(max_recent_chars or 0))
    max_recent_tokens = max(0, int(max_recent_tokens or 0))
    all_turns = [dict(turn) for turn in list(turns or []) if isinstance(turn, dict)]
    selected = all_turns[-max_recent_messages:] if max_recent_messages else []
    omitted_by_message_limit = max(len(all_turns) - len(selected), 0)
    bounded: list[dict[str, Any]] = []
    total_chars = 0
    total_tokens = 0
    omitted_by_char_cap = 0
    omitted_by_token_budget = 0
    char_truncated = False

    for turn in reversed(selected):
        content = str(turn.get("content") or "")
        if max_recent_chars == 0 or max_recent_tokens == 0:
            omitted_by_char_cap += int(max_recent_chars == 0)
            omitted_by_token_budget += int(max_recent_tokens == 0)
            char_truncated = max_recent_chars == 0
            continue
        if not bounded and len(content) > max_recent_chars:
            turn["content"] = content[-max_recent_chars:]
            content = str(turn["content"])
            char_truncated = True
        content_tokens = estimate_recent_chat_tokens(content)
        if bounded and total_chars + len(content) > max_recent_chars:
            omitted_by_char_cap += 1
            char_truncated = True
            continue
        if bounded and total_tokens + content_tokens > max_recent_tokens:
            omitted_by_token_budget += 1
            continue
        if not bounded and content_tokens > max_recent_tokens:
            turn["content"] = _trim_to_token_budget(content, max_recent_tokens)
            content = str(turn["content"])
            content_tokens = estimate_recent_chat_tokens(content)
            char_truncated = True
        total_chars += len(content)
        total_tokens += content_tokens
        bounded.append(_readonly_copy(turn) or {})

    messages = list(reversed(bounded))
    omitted_count = omitted_by_message_limit + omitted_by_char_cap + omitted_by_token_budget
    history_trimmed = omitted_count > 0 or char_truncated
    canonical_state_reinjected = history_trimmed and any(
        (
            pending_followup is not None,
            pending_draft is not None,
            bool(list(target_candidates or [])),
            interaction_event is not None,
        )
    )
    artifact = {
        "loaded_message_count": len(messages),
        "omitted_count": omitted_count,
        "history_trimmed": history_trimmed,
        "canonical_state_reinjected_after_history_trim": canonical_state_reinjected,
        "loaded_char_count": total_chars,
        "loaded_estimated_tokens": total_tokens,
        "hard_char_cap": max_recent_chars,
        "token_budget": max_recent_tokens,
        "token_estimator": RECENT_CHAT_TOKEN_ESTIMATOR,
        "char_truncated": char_truncated,
        "token_budget_status": (
            "at_hard_cap"
            if omitted_by_token_budget > 0
            or char_truncated
            or total_tokens >= max_recent_tokens > 0
            else "within_budget"
        ),
        "loaded_context_summary": {
            "recent_chat_messages": len(messages),
            "pending_followup_present": pending_followup is not None,
            "pending_draft_present": pending_draft is not None,
            "target_candidate_count": len(list(target_candidates or [])),
            "interaction_event_present": interaction_event is not None,
        },
        "omitted_context_summary": {
            "recent_chat_messages_omitted": omitted_count,
            "omitted_by_message_limit": omitted_by_message_limit,
            "omitted_by_char_cap": omitted_by_char_cap,
            "omitted_by_token_budget": omitted_by_token_budget,
        },
    }
    return messages, artifact


def estimate_recent_chat_tokens(text: str) -> int:
    if not text:
        return 0
    ascii_chars = 0
    non_ascii_chars = 0
    for char in text:
        if ord(char) < 128:
            ascii_chars += 1
        else:
            non_ascii_chars += 1
    return (ascii_chars + 3) // 4 + non_ascii_chars


def recent_chat_window_policy(
    *,
    max_recent_messages: int,
    max_recent_chars: int,
    max_recent_tokens: int,
) -> dict[str, Any]:
    return {
        "mode": "token_budgeted",
        "max_messages_safety_cap": max_recent_messages,
        "last_messages": max_recent_messages,
        "max_chars": max_recent_chars,
        "token_budget": max_recent_tokens,
        "token_estimator": RECENT_CHAT_TOKEN_ESTIMATOR,
        "hard_pins_preserved": True,
        "summary_role": "reference_only",
    }


def _trim_to_token_budget(content: str, max_recent_tokens: int) -> str:
    if max_recent_tokens <= 0:
        return ""
    kept: list[str] = []
    used = 0
    for char in reversed(content):
        cost = estimate_recent_chat_tokens(char)
        if used + cost > max_recent_tokens:
            break
        kept.append(char)
        used += cost
    return "".join(reversed(kept))


def _readonly_copy(value: Any) -> Any:
    if value is None:
        return None
    copied = deepcopy(value)
    if isinstance(copied, dict):
        copied["read_only"] = True
        copied["mutation_authority"] = False
    return copied


__all__ = [
    "RECENT_CHAT_TOKEN_ESTIMATOR",
    "build_recent_chat_window",
    "estimate_recent_chat_tokens",
    "recent_chat_window_policy",
]
