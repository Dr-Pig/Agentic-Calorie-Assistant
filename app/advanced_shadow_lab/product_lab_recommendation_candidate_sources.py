from __future__ import annotations

from typing import Mapping

from app.recommendation.application.candidate_source_port import (
    normalize_recommendation_candidate_sources,
)


def recommendation_source_candidates(
    *,
    payload: Mapping[str, Any],
    memory_context_pack: Mapping[str, Any],
) -> list[dict[str, Any]]:
    artifact = normalize_recommendation_candidate_sources(
        payload=payload,
        memory_context_pack=memory_context_pack,
    )
    return [
        dict(candidate)
        for candidate in artifact.get("candidate_sources") or []
        if isinstance(candidate, Mapping)
    ]


__all__ = ["recommendation_source_candidates"]
