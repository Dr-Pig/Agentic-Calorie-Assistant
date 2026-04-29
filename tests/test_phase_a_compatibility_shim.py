from __future__ import annotations

from app.runtime.application.phase_a_context import (
    advance_shadow_hypothesis,
    build_current_turn_context_v1,
    build_history_expansion_request,
    build_history_expansion_result,
    build_manager_context_pack,
    build_shadow_hypothesis,
    resolve_attachment_decision,
    resolve_transition_guard,
)


def test_phase_a_context_shim_reexports_expected_compatibility_surface() -> None:
    assert callable(build_current_turn_context_v1)
    assert callable(resolve_attachment_decision)
    assert callable(resolve_transition_guard)
    assert callable(build_manager_context_pack)
    assert callable(build_history_expansion_request)
    assert callable(build_history_expansion_result)
    assert callable(build_shadow_hypothesis)
    assert callable(advance_shadow_hypothesis)
