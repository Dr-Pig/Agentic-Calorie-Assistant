from __future__ import annotations

"""Deprecated compatibility shim for Phase A context helpers.

Active callers and Phase A tests should import intake-owned modules directly.
This module exists only for bounded compatibility re-exports.
"""

from ...intake.application.attachment_resolver import resolve_attachment_decision
from ...intake.application.context_injection_policy import (
    build_manager_context_pack,
    default_context_injection_policy,
)
from ...intake.application.current_turn_context_assembler import (
    build_chat_interaction_event,
    build_current_turn_context_v1,
)
from ...intake.application.history_expansion_policy import (
    build_history_expansion_request,
    build_history_expansion_result,
    default_history_expansion_policy,
)
from ...intake.application.phase_a_trace import build_phase_a_trace
from ...intake.application.shadow_hypothesis import (
    advance_shadow_hypothesis,
    build_shadow_hypothesis,
)
from ...intake.application.transition_guard import resolve_transition_guard

__all__ = [
    "advance_shadow_hypothesis",
    "build_chat_interaction_event",
    "build_current_turn_context_v1",
    "build_history_expansion_request",
    "build_history_expansion_result",
    "build_manager_context_pack",
    "build_phase_a_trace",
    "build_shadow_hypothesis",
    "default_context_injection_policy",
    "default_history_expansion_policy",
    "resolve_attachment_decision",
    "resolve_transition_guard",
]
