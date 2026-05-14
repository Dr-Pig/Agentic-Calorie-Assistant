from __future__ import annotations


EXPECTED_TRACE_BY_CASE_ID = {
    "explicit_item_removal_seeded": [
        "entry: route_to_intake",
        "pass2: resolve_correction_target",
        "guard: correction allowed",
        "mutation: remove target item and supersede meal version",
    ],
    "exact_item_official_label": [
        "entry: route_to_intake",
        "pass2: estimate_nutrition",
        "guard: commit allowed",
        "mutation: canonical meal commit",
    ],
    "generic_common_food_range": [
        "entry: route_to_intake",
        "pass2: estimate_nutrition",
        "synthesis: generic range posture without fake exactness",
        "mutation: canonical meal commit",
    ],
    "chinese_chicken_rice_correction_removal_debug": [
        "turn1: estimate and commit new meal",
        "turn2: resolve target, estimate correction, supersede meal version",
        "turn3: resolve removal target without nutrition estimate, supersede meal version",
        "turn4: answer remaining query without mutation",
    ],
    "bubble_milk_tea_refinement": [
        "turn1: estimate and commit initial drink",
        "turn2: attach refinement to committed drink",
        "turn2: estimate updated drink and supersede prior version",
    ],
    "luwei_bare_to_listed_basket": [
        "turn1: ask blocking follow-up and save draft without ledger mutation",
        "turn2: estimate listed basket",
        "turn2: commit only after clarification",
    ],
    "teppan_breakfast_explain_refine_dogfood": [
        "turn1: estimate and commit initial breakfast set",
        "turn2: answer estimate/composition question without tools or mutation",
        "turn3: attach supplied components to active meal",
        "turn3: estimate updated version and supersede prior version",
    ],
    "today_consumed_query_only": [
        "entry: answer current-day budget query",
        "runtime: read state only",
        "mutation: none",
    ],
    "no_plan_consumed_without_budget_target": [
        "entry: degraded no-plan answer",
        "runtime: read state only",
        "mutation: none",
        "response: no invented target or remaining",
    ],
}


__all__ = ["EXPECTED_TRACE_BY_CASE_ID"]
