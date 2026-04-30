from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ...runtime.contracts.phase_a import (
    AttachmentDecision,
    CurrentTurnContextV1,
    ManagerContextPack,
    TransitionGuardResult,
)
from .attachment_resolver import resolve_attachment_decision
from .context_injection_policy import build_manager_context_pack
from .current_turn_context_assembler import build_current_turn_context_v1
from .history_expansion_runtime import activate_pre_manager_history_expansion
from .phase_a_trace import build_phase_a_trace
from .shadow_hypothesis_runtime import ShadowHypothesisRuntimeResult, build_shadow_hypothesis_runtime
from .transition_guard import resolve_transition_guard


@dataclass(frozen=True)
class PhaseARuntimeContext:
    current_turn_context: CurrentTurnContextV1 | None
    manager_context_pack: ManagerContextPack | None
    phase_a_trace: dict[str, Any] | None
    shadow_runtime: ShadowHypothesisRuntimeResult | None
    attachment_decision: AttachmentDecision | None
    transition_guard_result: TransitionGuardResult | None


def prepare_phase_a_runtime_context(
    *,
    raw_user_input: str | None,
    resolved_state: Any,
    current_turn_context: CurrentTurnContextV1 | None,
    manager_context_pack: ManagerContextPack | None,
    phase_a_trace: dict[str, Any] | None,
) -> PhaseARuntimeContext:
    if current_turn_context is None and raw_user_input:
        current_turn_context = build_current_turn_context_v1(
            raw_user_input=raw_user_input,
            resolved_state=resolved_state,
        )
    if current_turn_context is None:
        return PhaseARuntimeContext(
            current_turn_context=None,
            manager_context_pack=manager_context_pack,
            phase_a_trace=phase_a_trace,
            shadow_runtime=None,
            attachment_decision=None,
            transition_guard_result=None,
        )

    pre_attachment_decision = resolve_attachment_decision(current_turn_context)
    pre_transition_guard_result = resolve_transition_guard(current_turn_context, pre_attachment_decision)
    activation = activate_pre_manager_history_expansion(
        current_turn_context=current_turn_context,
        resolved_state=resolved_state,
        pre_attachment_decision=pre_attachment_decision,
        pre_transition_guard_result=pre_transition_guard_result,
    )
    current_turn_context = activation.enriched_current_turn_context
    attachment_decision = activation.post_attachment_decision
    transition_guard_result = activation.post_transition_guard_result
    if phase_a_trace is None or activation.applied:
        phase_a_trace = build_phase_a_trace(
            current_turn_context=current_turn_context,
            attachment_decision=attachment_decision,
            transition_guard_result=transition_guard_result,
            history_expansion_activation=activation.trace_payload() if activation.applied else None,
        )
    shadow_runtime = build_shadow_hypothesis_runtime(
        current_turn_context=current_turn_context,
        attachment_decision=attachment_decision,
        transition_guard_result=transition_guard_result,
    )
    phase_a_trace = dict(phase_a_trace or {})
    phase_a_trace["shadow_hypothesis_runtime"] = shadow_runtime.trace_payload()
    if manager_context_pack is None:
        manager_context_pack = build_manager_context_pack(current_turn_context=current_turn_context)
    return PhaseARuntimeContext(
        current_turn_context=current_turn_context,
        manager_context_pack=manager_context_pack,
        phase_a_trace=phase_a_trace,
        shadow_runtime=shadow_runtime,
        attachment_decision=attachment_decision,
        transition_guard_result=transition_guard_result,
    )


__all__ = [
    "PhaseARuntimeContext",
    "prepare_phase_a_runtime_context",
]
