from __future__ import annotations

from typing import Any, Mapping

from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "memory.application.runtime_lab_manager_injection"
)


def build_manager_memory_injection_comparison(
    trace: Mapping[str, Any],
    shadow_memory_context_pack: Mapping[str, Any],
    *,
    enable_lab_injection: bool,
) -> dict[str, Any]:
    baseline = _baseline_run(trace)
    memory_context = _memory_context_run(
        baseline,
        shadow_memory_context_pack,
        enable_lab_injection=enable_lab_injection,
    )
    return {
        "artifact_type": "runtime_lab_manager_memory_injection_comparison",
        "status": "pass",
        "manager_execution_mode": "trace_replay_lab_stub",
        "injection_enabled": enable_lab_injection,
        "baseline_run": baseline,
        "memory_context_run": memory_context,
        "final_response_changed": (
            baseline["final_response"] != memory_context["final_response"]
        ),
        "tool_call_delta": {
            "baseline_tool_calls": baseline["tool_calls"],
            "memory_context_tool_calls": memory_context["tool_calls"],
            "blocked_from_memory_context_run": baseline["tool_calls"],
        },
        "mutation_delta": {
            "baseline_mutation_attempts": baseline["mutation_attempts"],
            "memory_context_mutation_attempts": memory_context["mutation_attempts"],
            "blocked_from_memory_context_run": baseline["mutation_attempts"],
        },
        "latency_comparison": {
            "baseline_ms": baseline["latency_ms"],
            "memory_context_ms": memory_context["latency_ms"],
        },
        "omission_trace": list(shadow_memory_context_pack.get("omission_trace", [])),
        "tool_calls_blocked": True,
        "mutation_attempts_blocked": True,
        "runtime_connected": True,
        "lab_isolated": True,
        "shadow_memory_context_pack_used": enable_lab_injection,
        "runtime_effect_allowed": False,
        "durable_product_memory_written": False,
        "user_facing_behavior_changed": False,
        "canonical_mutation_changed": False,
        "manager_context_packet_changed": False,
        "manager_context_injected": False,
    }


def _baseline_run(trace: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "run_type": "baseline_trace_replay",
        "final_response": _final_response(trace),
        "tool_calls": _tool_calls(trace),
        "mutation_attempts": _mutation_attempts(trace),
        "latency_ms": _latency_ms(trace),
        "shadow_memory_context_pack_used": False,
    }


def _memory_context_run(
    baseline: Mapping[str, Any],
    shadow_memory_context_pack: Mapping[str, Any],
    *,
    enable_lab_injection: bool,
) -> dict[str, Any]:
    final_response = str(baseline["final_response"])
    token_estimate = int(shadow_memory_context_pack.get("token_estimate") or 0)
    if enable_lab_injection:
        count = len(shadow_memory_context_pack.get("entries", []))
        final_response = f"{final_response} [shadow_memory_entries={count}]"
    return {
        "run_type": "memory_context_trace_replay",
        "final_response": final_response,
        "tool_calls": [],
        "mutation_attempts": [],
        "latency_ms": int(baseline["latency_ms"]) + token_estimate,
        "shadow_memory_context_pack_used": enable_lab_injection,
    }


def _final_response(trace: Mapping[str, Any]) -> str:
    renderer_output = trace.get("renderer_output")
    if isinstance(renderer_output, Mapping) and renderer_output.get("assistant_message"):
        return str(renderer_output["assistant_message"])
    return str(trace.get("assistant_message") or "")


def _tool_calls(trace: Mapping[str, Any]) -> list[str]:
    tool_plan = trace.get("tool_plan")
    if isinstance(tool_plan, list):
        return [str(item) for item in tool_plan]
    return []


def _mutation_attempts(trace: Mapping[str, Any]) -> list[str]:
    state_delta = trace.get("state_delta")
    if isinstance(state_delta, Mapping):
        return sorted(str(key) for key in state_delta)
    return []


def _latency_ms(trace: Mapping[str, Any]) -> int:
    latency_tracking = trace.get("latency_tracking")
    if isinstance(latency_tracking, Mapping):
        return int(latency_tracking.get("total_ms") or 0)
    return 0


__all__ = [
    "SIDECAR_ACTIVATION_CONTRACT",
    "build_manager_memory_injection_comparison",
]
