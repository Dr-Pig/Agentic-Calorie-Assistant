from __future__ import annotations

from typing import Any

from app.memory.application.long_term_context_shadow.context_value_scoring import (
    _context_value_scoring_v2_artifact,
)
from app.memory.application.long_term_context_shadow.context_lifecycle_artifact import (
    _context_signal_lifecycle_shadow_artifact,
)
from app.memory.application.long_term_context_shadow.derived_view_artifact import (
    _derived_memory_views_shadow_artifact,
)
from app.memory.application.long_term_context_shadow.extraction_engine_artifact import (
    _candidate_extraction_engine_v2_artifact,
)
from app.memory.application.long_term_context_shadow.friction_budget_artifact import (
    _contextual_friction_budget_shadow_artifact,
)
from app.memory.application.long_term_context_shadow.menu_highlight_artifact import (
    _menu_highlight_shadow_artifact,
)
from app.memory.application.long_term_context_shadow.profile_artifact import (
    _user_context_profile_shadow_artifact,
)
from app.memory.application.long_term_context_shadow.proactive_intelligence_artifact import (
    _proactive_intelligence_shadow_artifact,
)
from app.memory.application.long_term_context_shadow.replay_artifacts import (
    _shadow_replay_evaluators_artifact,
)
from app.memory.application.long_term_context_shadow.review_queue_reducer import (
    _review_queue_reducer_artifact,
)
from app.memory.application.long_term_context_shadow.scope_isolation_artifact import (
    _scope_isolation_shadow_artifact,
)


def build_evaluator_artifacts(
    fixture: dict[str, Any],
    candidates: list,
) -> dict[str, dict[str, Any]]:
    return {
        "candidate_extraction_engine_v2": _candidate_extraction_engine_v2_artifact(
            fixture,
            candidates,
        ),
        "derived_memory_views_shadow_eval": _derived_memory_views_shadow_artifact(
            fixture,
        ),
        "context_signal_lifecycle_shadow_eval": (
            _context_signal_lifecycle_shadow_artifact(fixture, candidates)
        ),
        "user_context_profile_shadow_eval": _user_context_profile_shadow_artifact(
            fixture,
            candidates,
        ),
        "scope_isolation_shadow_eval": _scope_isolation_shadow_artifact(
            fixture,
            candidates,
        ),
        "proactive_intelligence_shadow_eval": (
            _proactive_intelligence_shadow_artifact(fixture, candidates)
        ),
        "contextual_friction_budget_shadow_eval": (
            _contextual_friction_budget_shadow_artifact(fixture, candidates)
        ),
        "menu_highlight_shadow_eval": _menu_highlight_shadow_artifact(
            fixture,
            candidates,
        ),
        "context_value_scoring_v2": _context_value_scoring_v2_artifact(
            fixture,
            candidates,
        ),
        "shadow_replay_evaluators": _shadow_replay_evaluators_artifact(
            fixture,
            candidates,
        ),
        "review_queue_reducer": _review_queue_reducer_artifact(
            fixture,
            candidates,
        ),
    }


__all__ = [
    "build_evaluator_artifacts",
    "_candidate_extraction_engine_v2_artifact",
    "_context_signal_lifecycle_shadow_artifact",
    "_context_value_scoring_v2_artifact",
    "_contextual_friction_budget_shadow_artifact",
    "_derived_memory_views_shadow_artifact",
    "_menu_highlight_shadow_artifact",
    "_proactive_intelligence_shadow_artifact",
    "_review_queue_reducer_artifact",
    "_scope_isolation_shadow_artifact",
    "_shadow_replay_evaluators_artifact",
    "_user_context_profile_shadow_artifact",
]
