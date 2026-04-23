from __future__ import annotations
from app.schemas import ComponentEstimate, IngredientCandidate
from .nutrition_profiles import EstimateMode, ConfidenceTier, HIGH_RISK_KEYWORDS, _kcal
from .nutrition_lookup_policy import resolve_ingredient_estimate

def _estimate_mode_from_components(component_estimates: list[ComponentEstimate], unknown: list[str]) -> EstimateMode:
    if not component_estimates:
        return "llm_only"
    if any(item.estimate_basis == "heuristic_only" for item in component_estimates) or unknown:
        return "heuristic_fallback_mode"
    if all(item.estimate_basis == "exact" for item in component_estimates):
        return "exact_item_mode"
    return "anchored_component_mode"


def _confidence_tier_for_result(
    *,
    component_estimates: list[ComponentEstimate],
    unknown: list[str],
    matched_critical: int,
    critical_total: int,
) -> ConfidenceTier:
    if not component_estimates or (critical_total > 0 and matched_critical < critical_total):
        return "low"
    if any(item.estimate_basis == "heuristic_only" for item in component_estimates) or unknown:
        return "low"
    if all(item.confidence_tier == "high" for item in component_estimates):
        return "high"
    return "medium"


def deterministic_macro_estimate(ingredients: list[IngredientCandidate]) -> dict[str, object]:
    component_estimates: list[ComponentEstimate] = []
    protein = 0
    carb = 0
    fat = 0
    unknown: list[str] = []
    matched_critical = 0
    critical_total = 0
    macro_basis: list[dict[str, object]] = []
    portion_assumptions: list[str] = []
    heuristic_dependencies: list[str] = []

    for ingredient in ingredients:
        if ingredient.is_critical:
            critical_total += 1
        lookup = resolve_ingredient_estimate(ingredient.name, ingredient.amount_hint, ingredient.role)
        print(f"  [DEBUG] Processing ingredient: {ingredient.name} | hint: {ingredient.amount_hint} | matched: {bool(lookup)}")
        if lookup is None:
            unknown.append(ingredient.name)
            continue
        if ingredient.is_critical:
            matched_critical += 1
        print(f"  [DEBUG] Component {ingredient.name}: P={lookup.profile.protein_g}, C={lookup.profile.carb_g}, F={lookup.profile.fat_g} (Kcal: {_kcal(lookup.profile)})")
        component_estimates.append(
            ComponentEstimate(
                name=ingredient.name,
                source="lookup",
                evidence_role=lookup.evidence_role,
                estimate_basis=lookup.estimate_basis,
                confidence_tier=lookup.confidence_tier,
                quantity_hint=ingredient.amount_hint or None,
                estimated_kcal=_kcal(lookup.profile),
                protein_g=lookup.profile.protein_g,
                carb_g=lookup.profile.carb_g,
                fat_g=lookup.profile.fat_g,
                heuristic_dependencies=list(lookup.heuristic_dependencies),
            )
        )
        protein += lookup.profile.protein_g
        carb += lookup.profile.carb_g
        fat += lookup.profile.fat_g
        print(f"  [DEBUG] Running Totals: P={protein}, C={carb}, F={fat}")
        macro_basis.append(
            {
                "name": ingredient.name,
                "source_name": lookup.source_name,
                "evidence_role": lookup.evidence_role,
                "estimate_basis": lookup.estimate_basis,
                "macro_completeness": lookup.macro_completeness,
                "confidence_tier": lookup.confidence_tier,
            }
        )
        portion_assumptions.extend(lookup.portion_assumptions)
        heuristic_dependencies.extend(lookup.heuristic_dependencies)

    estimated_kcal = protein * 4 + carb * 4 + fat * 9
    deterministic_hit = bool(component_estimates) and (critical_total == 0 or matched_critical == critical_total)
    estimate_mode = _estimate_mode_from_components(component_estimates, unknown)
    confidence_tier = _confidence_tier_for_result(
        component_estimates=component_estimates,
        unknown=unknown,
        matched_critical=matched_critical,
        critical_total=critical_total,
    )
    evidence_gaps = []
    if unknown:
        evidence_gaps.append("unmatched_components")
    if any(item.estimate_basis == "heuristic_only" for item in component_estimates):
        evidence_gaps.append("heuristic_macro_dependency")
    if critical_total > matched_critical:
        evidence_gaps.append("critical_component_gap")

    if estimate_mode == "exact_item_mode":
        why_not_exact = ""
    elif estimate_mode == "anchored_component_mode":
        why_not_exact = "No exact item truth matched; estimate comes from complete ingredient anchors."
    elif estimate_mode == "heuristic_fallback_mode":
        why_not_exact = "Estimate depends on heuristic macro inference or incomplete ingredient anchors."
    else:
        why_not_exact = "No deterministic ingredient evidence was available."

    return {
        "component_estimates": component_estimates,
        "totals": {
            "protein_g": protein,
            "carb_g": carb,
            "fat_g": fat,
            "estimated_kcal": estimated_kcal,
        },
        "unknown_components": unknown,
        "deterministic_hit": deterministic_hit,
        "estimate_mode": estimate_mode,
        "confidence_tier": confidence_tier,
        "evidence_gaps": evidence_gaps,
        "macro_basis": macro_basis,
        "portion_assumptions": list(dict.fromkeys(item for item in portion_assumptions if item)),
        "heuristic_dependencies": list(dict.fromkeys(item for item in heuristic_dependencies if item)),
        "why_not_exact": why_not_exact,
        "matched_critical": matched_critical,
        "critical_total": critical_total,
    }


def apply_high_risk_sanity_checks(
    *,
    title: str,
    components: list[str],
    protein_g: int,
    carb_g: int,
    fat_g: int,
    uncertainty_factors: list[str],
) -> list[str]:
    flagged = list(dict.fromkeys(uncertainty_factors))
    joined = " ".join([title, *components]).lower()

    if any(token.lower() in joined for token in HIGH_RISK_KEYWORDS["ramen"]) and fat_g < 15:
        flagged.append("濃湯拉麵的脂肪估計可能偏低，實際油脂與喝湯量可能更高。")
    if any(token.lower() in joined for token in HIGH_RISK_KEYWORDS["gyudon"]) and (carb_g < 40 or fat_g < 10):
        flagged.append("牛丼類餐點通常會包含較多白飯與醬汁，目前估計可能偏低。")
    if any(token.lower() in joined for token in HIGH_RISK_KEYWORDS["breakfast_shop_oily_items"]) and fat_g < 10:
        flagged.append("早餐店煎製油量與起司/美乃滋用量可能讓脂肪再更高。")
    return list(dict.fromkeys(flagged))
