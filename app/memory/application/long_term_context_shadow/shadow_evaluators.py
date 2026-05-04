from __future__ import annotations

from typing import Any

from app.memory.application.long_term_context_shadow.context_value_scoring import (
    _context_value_scoring_v2_artifact,
)
from app.memory.application.long_term_context_shadow.extraction_engine_artifact import (
    _candidate_extraction_engine_v2_artifact,
)
from app.memory.application.long_term_context_shadow.replay_artifacts import (
    _shadow_replay_evaluators_artifact,
)
from app.memory.application.long_term_context_shadow.review_queue_reducer import (
    _review_queue_reducer_artifact,
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
    "_context_value_scoring_v2_artifact",
    "_review_queue_reducer_artifact",
    "_shadow_replay_evaluators_artifact",
]
