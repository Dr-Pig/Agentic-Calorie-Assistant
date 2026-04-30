from __future__ import annotations

from typing import Any


def b2_manager_policy_hints() -> dict[str, Any]:
    """Approved B2 food-semantics hints for live manager diagnostics.

    These hints are product policy context for the Manager LLM. They are not
    deterministic classifiers and must not be used by runtime code to infer
    semantics from raw text.
    """
    return {
        "policy_source": "approved_b2_case_law",
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
        ],
    }


__all__ = ["b2_manager_policy_hints"]
