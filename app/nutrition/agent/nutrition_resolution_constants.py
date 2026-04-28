from __future__ import annotations

VALID_DECISIONS = {"DIRECT_ANSWER", "NEED_EXTERNAL_DATA", "ASK_USER"}
VALID_ORIGINS = {
    "generic_common",
    "restaurant_chain",
    "convenience_packaged",
    "customizable_drink",
    "customizable_bowl",
    "home_private",
}
VALID_PRIVATE_INFO_RISK = {"high", "low"}
VALID_RESOLUTION_MODES = {
    "exact_label_finalize",
    "near_exact_finalize",
    "component_estimate",
    "provisional_estimate",
    "cannot_estimate_yet",
}
VALID_RESOLUTION_BASES = {
    "exact_item_evidence",
    "official_source_evidence",
    "component_model",
    "calibrated_component_model",
}
VALID_EXACTNESS = {
    "exact_item",
    "near_exact",
    "calibrated_estimate",
    "component_grounded",
    "best_effort",
    "unknown",
}
VALID_ACTION_TAKEN = {
    "direct_answer",
    "clarify_before_estimate",
    "answer_with_uncertainty",
    "request_tool",
}
VALID_RESPONSE_MODE_HINTS = {
    "exact_answer",
    "rough_estimate_ok",
    "clarify_first",
}
VALID_ESTIMATE_MODES = {
    "exact_item",
    "anchored_component",
    "heuristic_fallback",
    "llm_only",
}
VALID_CONFIDENCE_TIERS = {"high", "medium", "low"}

PRIMARY_PROMPT = """You are the nutrition reasoning layer for a food estimation assistant.

Responsibilities:
- Read meal link, decision result, active meal context, and selected evidence.
- Decide exactness, whether estimation is possible, and the best nutrition answer payload.
- Return structured reasoning only; do not write the final user-facing reply.
- Always output structured nutrition payload fields even when the final user-facing reply will stay concise.

Rules:
- You are the only layer allowed to produce calorie, macro, and component outputs.
- Calorie and component outputs are primary. Macro outputs are helpful hints for downstream deterministic derivation, not the primary truth.
- Never invent exact label values unless supported by exact item or official evidence.
- If the meal can only be estimated provisionally, keep unresolved_info and response_mode_hint=rough_estimate_ok.
- If blocking clarification is required, return action_taken=clarify_before_estimate and response_mode_hint=clarify_first.
- You must explicitly output posture fields, not just calories:
  - `resolution_mode`
  - `resolution_basis`
  - `exactness`
  - `estimate_mode`
  - `confidence`
  - `action_taken`
  - `response_mode_hint`
- You must also always output nutrition structure fields for app payloads:
  - `estimated_kcal`
  - `protein_g`
  - `carb_g`
  - `fat_g`
  - `components`
  - `component_breakdown`
  - `evidence_ids_used`
  - `why_no_more_tools`
  - `current_evidence_sufficiency`
  - `reason_for_not_requesting_tool`
"""
