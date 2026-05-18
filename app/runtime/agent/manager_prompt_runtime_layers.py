from __future__ import annotations

from typing import Any

RUNTIME_PAYLOAD_LAYER_ORDER = (
    "turn_state",
    "context_engineering",
    "tool_surface",
    "tool_evidence",
    "contract_constraints",
    "loop_control",
    "guard_repair",
)
RUNTIME_PAYLOAD_LAYER_KEYS = {
    "turn_state": ("raw_user_input", "resolved_state", "resolved_state_role", "onboarding_payload"),
    "context_engineering": (
        "phase_a_current_turn_context",
        "phase_a_manager_context_pack",
        "manager_context_packet_v1",
        "phase_a_manager_context_pack_role",
        "phase_a_surface_mode",
        "phase_a_context_pack_version",
        "phase_a_history_expansion_policy",
        "phase_a_history_expansion_enabled",
        "phase_a_shadow_hypothesis",
        "phase_a_shadow_hypothesis_role",
        "phase_a_shadow_hypothesis_instruction",
    ),
    "tool_surface": ("available_tools", "manager_scope_policy", "current_loop_tool_policy"),
    "tool_evidence": ("tool_results",),
    "contract_constraints": ("constraints", "manager_product_policy_hints"),
    "loop_control": ("round_index", "manager_loop_scope"),
    "guard_repair": ("guard_feedback",),
}


def runtime_payload_layer_plan(dynamic_payload_keys: list[str]) -> dict[str, Any]:
    remaining = set(dynamic_payload_keys)
    sections: list[dict[str, Any]] = []
    for section_id in RUNTIME_PAYLOAD_LAYER_ORDER:
        section_keys = [key for key in RUNTIME_PAYLOAD_LAYER_KEYS[section_id] if key in remaining]
        remaining.difference_update(section_keys)
        sections.append(
            {
                "section_id": section_id,
                "owner": runtime_payload_section_owner(section_id),
                "keys": section_keys,
            }
        )
    return {
        "suffix_order": list(RUNTIME_PAYLOAD_LAYER_ORDER),
        "sections": sections,
        "uncategorized_dynamic_keys": sorted(remaining),
    }


def runtime_payload_section_owner(section_id: str) -> str:
    if section_id == "context_engineering":
        return "ManagerRuntime.ContextEngineering"
    if section_id == "tool_evidence":
        return "ManagerRuntime.ToolLoop"
    if section_id == "guard_repair":
        return "ManagerRuntime.Guard"
    return "ManagerRuntime"


__all__ = [
    "RUNTIME_PAYLOAD_LAYER_KEYS",
    "RUNTIME_PAYLOAD_LAYER_ORDER",
    "runtime_payload_layer_plan",
    "runtime_payload_section_owner",
]
