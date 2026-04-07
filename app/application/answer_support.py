from __future__ import annotations

from typing import Any

from ..application.evidence_assembly import source_class_for_item

MAX_SELECTED_EVIDENCE_ITEMS = 5


def boundary_followup_question() -> str:
    return "請問你剛剛說的是哪一餐？例如早餐、午餐、晚餐或點心。"


def meal_template_context(template: dict[str, Any] | None) -> str:
    if not template:
        return ""
    baseline = template.get("baseline_kcal") or {}
    default_components = template.get("default_components") or []
    component_names = [str(item.get("name", "")).strip() for item in default_components if str(item.get("name", "")).strip()]
    variability = [str(item).strip() for item in template.get("major_variability_factors", []) if str(item).strip()]
    must_ask = [str(item).strip() for item in template.get("must_ask_if_uncertain", []) if str(item).strip()]
    lines = ["", "[MEAL_TEMPLATE]"]
    if template.get("title"):
        lines.append(f"- title: {template['title']}")
    if component_names:
        lines.append(f"- default_components: {', '.join(component_names[:5])}")
    if baseline:
        lines.append(
            f"- baseline_kcal: low={baseline.get('low', 0)} / mid={baseline.get('mid', 0)} / high={baseline.get('high', 0)}"
        )
    if variability:
        lines.append(f"- variability: {', '.join(variability[:2])}")
    if must_ask:
        lines.append(f"- must_ask_if_uncertain: {', '.join(must_ask[:2])}")
    if template.get("renderer_assumption"):
        lines.append(f"- renderer_assumption: {template['renderer_assumption']}")
    return "\n".join(lines)

def evaluate_answer(parsed: dict[str, Any], risk_packet: dict[str, Any], meal_template: dict[str, Any] | None = None) -> dict[str, Any]:
    del meal_template
    missing_components = not parsed["components"]
    if parsed.get("parse_mode") == "structured":
        missing_kcal = (parsed.get("estimated_kcal", 0) <= 0) and (parsed.get("kcal_most_likely", 0) <= 0)
    else:
        missing_kcal = parsed.get("estimated_kcal", 0) <= 0
    missing_macro = parsed["protein_g"] <= 0 and parsed["carb_g"] <= 0 and parsed["fat_g"] <= 0
    missing_required_checks: list[str] = []
    combined_text = " ".join([parsed.get("body", ""), parsed.get("followup_question", ""), *parsed.get("uncertainty_factors", [])])
    lowered = combined_text.lower()
    if parsed.get("estimate_mode") != "exact_item":
        for risk_flag in risk_packet.get("risk_flags", []):
            for check in risk_packet.get("required_checks", {}).get(risk_flag, []):
                keywords = [item.lower() for item in check.get("keywords", [])]
                if keywords and not any(keyword in lowered for keyword in keywords):
                    missing_required_checks.append(f"{risk_flag}:{check['key']}")
    follow_up_needed = bool(parsed.get("follow_up_needed"))
    followup_question = str(parsed.get("followup_question") or "").strip()
    unresolved_info = [str(item).strip() for item in parsed.get("unresolved_info", []) if str(item).strip()]
    return {
        "missing_components": missing_components,
        "missing_kcal": missing_kcal,
        "missing_macro": missing_macro,
        "missing_required_checks": missing_required_checks,
        "required_checks_passed": not missing_required_checks,
        "followup_missing_question": follow_up_needed and not followup_question,
        "clarify_without_unresolved_info": parsed.get("action_taken") == "clarify_before_estimate" and not unresolved_info,
        "estimate_mode": parsed.get("estimate_mode", "llm_only"),
        "estimate_confidence_tier": parsed.get("estimate_confidence_tier", "low"),
        "failure_family": None,
        "reference_kcal_mismatch": False,
        "meal_template_kcal_mismatch": False,
    }


def is_private_only_case(parsed: dict[str, Any], risk_packet: dict[str, Any], user_text: str) -> bool:
    del user_text
    if parsed.get("private_info_risk") == "high":
        return True
    if str(parsed.get("food_origin") or "") == "home_private":
        return True
    return bool(risk_packet.get("private_only"))


def final_best_answer_source(best_source: str, best_parsed: dict[str, Any]) -> str:
    return best_source or ("llm" if best_parsed.get("estimated_kcal", 0) > 0 else "unknown")
