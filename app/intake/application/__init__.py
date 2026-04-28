from __future__ import annotations
from importlib import import_module
from typing import Any

__all__ = [
    "V2Bundle1OnboardingPayload",
    "_normalize_bundle1_live_payload",
    "execute_bundle1_turn",
    "parse_weight_or_budget_intent",
    "process_bundle2_intake",
]

_EXPORT_MAP = {
    "V2Bundle1OnboardingPayload": (".intake_turn_orchestrator", "V2Bundle1OnboardingPayload"),
    "_normalize_bundle1_live_payload": (".manager_tools", "_normalize_bundle1_live_payload"),
    "execute_bundle1_turn": (".intake_turn_orchestrator", "execute_bundle1_turn"),
    "parse_weight_or_budget_intent": (".chat_intents", "parse_weight_or_budget_intent"),
    "process_bundle2_intake": (".intake_execution_orchestrator", "process_bundle2_intake"),
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
