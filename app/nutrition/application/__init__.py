from __future__ import annotations
from importlib import import_module
from typing import Any

__all__ = [
    "classify_query_family",
    "evaluate_candidate_eligibility",
    "is_high_variance_family",
    "summarize_eligibility_results",
]

_EXPORT_MAP = {
    "classify_query_family": (".evidence_eligibility", "classify_query_family"),
    "evaluate_candidate_eligibility": (".evidence_eligibility", "evaluate_candidate_eligibility"),
    "is_high_variance_family": (".evidence_eligibility", "is_high_variance_family"),
    "summarize_eligibility_results": (".evidence_eligibility", "summarize_eligibility_results"),
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
