from __future__ import annotations

from typing import Any

from app.memory.application.long_term_context_shadow.body_budget_candidate_extraction import (
    _body_logging_candidates,
    _budget_candidates,
    _calibration_candidates,
)
from app.memory.application.long_term_context_shadow.candidate_records import (
    _build_context_value_items,
)
from app.memory.application.long_term_context_shadow.language_bias_candidate_extraction import (
    _conversation_recall_context_candidates,
    _intake_estimation_bias_candidates,
    _language_candidates,
)
from app.memory.application.long_term_context_shadow.meal_candidate_extraction import (
    _golden_order_candidates,
    _meal_distribution_candidates,
)
from app.memory.application.long_term_context_shadow.preference_usage_candidate_extraction import (
    _app_usage_style_candidates,
    _interaction_preference_candidates,
    _negative_preference_candidates,
    _temporary_preference_candidates,
)
from app.memory.application.long_term_context_shadow.utils import (
    _list_of_dicts,
    _trace_refs,
)
from app.memory.domain.long_term_context_candidates import (
    ContextValueReviewItem,
    LongTermContextCandidate,
)


def _build_candidates(fixture: dict[str, Any]) -> list[LongTermContextCandidate]:
    user_id = str(fixture.get("user_id") or "fixture-user")
    meals = _list_of_dicts(fixture.get("meal_logs"))
    body_observations = _list_of_dicts(fixture.get("body_observations"))
    budgets = _list_of_dicts(fixture.get("budget_summaries"))
    diagnostics = _list_of_dicts(fixture.get("calibration_diagnostics"))
    language_observations = _list_of_dicts(fixture.get("language_observations"))
    bias_events = _list_of_dicts(fixture.get("intake_estimation_events"))
    usage_events = _list_of_dicts(fixture.get("app_usage_events"))
    interaction_events = _list_of_dicts(fixture.get("interaction_events"))
    negative_preferences = _list_of_dicts(
        fixture.get("negative_preference_observations")
    )
    temporary_preferences = _list_of_dicts(
        fixture.get("temporary_preference_observations")
    )
    conversation_summaries = _list_of_dicts(
        fixture.get("conversation_history_summaries")
    )
    trace_refs = _trace_refs(fixture)

    candidates: list[LongTermContextCandidate] = []
    candidates.extend(_meal_distribution_candidates(user_id, meals, trace_refs))
    candidates.extend(_golden_order_candidates(user_id, meals, trace_refs))
    candidates.extend(_body_logging_candidates(user_id, body_observations, trace_refs))
    candidates.extend(_budget_candidates(user_id, budgets, trace_refs))
    candidates.extend(_calibration_candidates(user_id, diagnostics, trace_refs))
    candidates.extend(_language_candidates(user_id, language_observations, trace_refs))
    candidates.extend(
        _intake_estimation_bias_candidates(user_id, bias_events, trace_refs)
    )
    candidates.extend(_app_usage_style_candidates(user_id, usage_events, trace_refs))
    candidates.extend(
        _interaction_preference_candidates(user_id, interaction_events, trace_refs)
    )
    candidates.extend(
        _negative_preference_candidates(user_id, negative_preferences, trace_refs)
    )
    candidates.extend(
        _temporary_preference_candidates(user_id, temporary_preferences, trace_refs)
    )
    candidates.extend(
        _conversation_recall_context_candidates(
            user_id, conversation_summaries, trace_refs
        )
    )
    return candidates


__all__ = [
    "ContextValueReviewItem",
    "LongTermContextCandidate",
    "_build_candidates",
    "_build_context_value_items",
]
