from __future__ import annotations
from importlib import import_module
from typing import Any

__all__ = [
    "build_deterministic_sidecar",
    "build_trace_refs",
    "decide_bundle1_turn",
    "decide_bundle2_step1",
    "decide_bundle2_step2",
    "evaluate_macro_display",
    "render_bundle1_reply",
    "validate_intake_persistence",
    "validate_onboarding_seed",
    "write_bundle1_request_trace_artifact",
    "write_bundle2_request_trace_artifact",
]

_EXPORT_MAP = {
    "build_deterministic_sidecar": (".sidecar_service", "build_deterministic_sidecar"),
    "build_trace_refs": (".request_trace_artifacts", "build_trace_refs"),
    "decide_bundle1_turn": (".manager_service", "decide_bundle1_turn"),
    "decide_bundle2_step1": (".manager_service", "decide_bundle2_step1"),
    "decide_bundle2_step2": (".manager_service", "decide_bundle2_step2"),
    "evaluate_macro_display": (".execution_guard", "evaluate_macro_display"),
    "render_bundle1_reply": (".reply_renderer", "render_bundle1_reply"),
    "validate_intake_persistence": (".execution_guard", "validate_intake_persistence"),
    "validate_onboarding_seed": (".execution_guard", "validate_onboarding_seed"),
    "write_bundle1_request_trace_artifact": (".request_trace_artifacts", "write_bundle1_request_trace_artifact"),
    "write_bundle2_request_trace_artifact": (".request_trace_artifacts", "write_bundle2_request_trace_artifact"),
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
