from __future__ import annotations
from importlib import import_module
from typing import Any

__all__ = [
    "RemainingBudgetAnswerContract",
    "build_current_budget_view",
    "build_remaining_budget_answer_contract",
]

_EXPORT_MAP = {
    "RemainingBudgetAnswerContract": (".current_budget_answer", "RemainingBudgetAnswerContract"),
    "build_current_budget_view": (".current_budget_read_model", "build_current_budget_view"),
    "build_remaining_budget_answer_contract": (".current_budget_answer", "build_remaining_budget_answer_contract"),
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
