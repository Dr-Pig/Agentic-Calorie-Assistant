from __future__ import annotations

from importlib import import_module
from typing import Any

__all__ = [
    "RecommendationCandidateRetrievalResult",
    "build_recommendation_candidates",
    "build_recommendation_candidate_spec",
    "build_recommendation_context",
    "build_recommendation_ranking_and_synthesis",
    "build_recommendation_response",
    "retrieve_recommendation_candidates",
]

_EXPORT_MAP = {
    "RecommendationCandidateRetrievalResult": (".candidate_retrieval", "RecommendationCandidateRetrievalResult"),
    "build_recommendation_candidates": (".candidate_retrieval", "build_recommendation_candidates"),
    "build_recommendation_candidate_spec": (".candidate_spec", "build_recommendation_candidate_spec"),
    "build_recommendation_context": (".context", "build_recommendation_context"),
    "build_recommendation_ranking_and_synthesis": (".ranking", "build_recommendation_ranking_and_synthesis"),
    "build_recommendation_response": (".response", "build_recommendation_response"),
    "retrieve_recommendation_candidates": (".candidate_retrieval", "retrieve_recommendation_candidates"),
}


def __getattr__(name: str) -> Any:
    try:
        module_name, attr_name = _EXPORT_MAP[name]
    except KeyError as exc:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from exc
    module = import_module(module_name, __name__)
    value = getattr(module, attr_name)
    globals()[name] = value
    return value
