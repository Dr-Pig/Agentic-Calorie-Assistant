from __future__ import annotations

from .nutrition_resolution_prompt_text import NUTRITION_RESOLUTION_PROMPT, PRIMARY_PROMPT

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
