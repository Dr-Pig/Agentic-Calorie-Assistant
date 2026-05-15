from __future__ import annotations

from typing import Any


def nutrition_manager_policy_hints() -> dict[str, Any]:
    """Approved food-semantics hints for live manager diagnostics.

    These hints are product policy context for the Manager LLM. They are not
    deterministic classifiers and must not be used by runtime code to infer
    semantics from raw text.
    """
    return {
        "policy_source": "approved_nutrition_case_law",
        "policy_role": "manager_context_hint_not_deterministic_classifier",
        "rules": [
            {
                "policy_id": "pearl_milk_tea_missing_sugar_size",
                "applies_to": "first-turn pearl milk tea or common commercial drink logging with missing size/sugar details",
                "manager_behavior": (
                    "Allow a logged estimate when evidence is estimable, but include a refinement follow-up. "
                    "The follow-up asks for precision and must not block commit by itself."
                ),
            },
            {
                "policy_id": "self_selected_basket_without_listed_items",
                "applies_to": "bare self-selected mixed basket foods without listed ingredients, such as luwei or hotpot-style baskets",
                "manager_behavior": (
                    "Do not estimate or canonical-write the bare basket turn. Ask the user to list items or portions. "
                    "Listed ingredients may be estimated item by item in a later turn."
                ),
            },
            {
                "policy_id": "listed_basket_followup_with_items",
                "applies_to": (
                    "follow-up turn after a self-selected mixed basket clarification when the user provides concrete "
                    "listed items or ingredients"
                ),
                "manager_behavior": (
                    "When the user provides concrete listed items after a basket clarification, call the nutrition "
                    "evidence tool before final commit. This is no longer composition-unknown; do not repeat the same "
                    "composition clarification unless the listed details are still insufficient. The follow-up may "
                    "only list item names and may not repeat the basket label; use prior turn context to attach it."
                ),
                "runtime_authority": "validate_evidence_packet_and_final_mapping_only",
            },
            {
                "policy_id": "brand_combo_with_explicit_components",
                "applies_to": (
                    "a branded or chain combo plus concrete items, sides, or drinks named in the same turn"
                ),
                "manager_behavior": (
                    "Do not ask for the component list again; put the main item and named side/drink items in "
                    "listed_items, use retrieval_goal='listed_item_lookup', and call the nutrition evidence tool "
                    "before final commit. Ask only if evidence rejects a component or a required component is "
                    "still genuinely missing."
                ),
                "runtime_authority": "validate_evidence_packet_and_final_mapping_only",
            },
        ],
    }


__all__ = ["nutrition_manager_policy_hints"]
