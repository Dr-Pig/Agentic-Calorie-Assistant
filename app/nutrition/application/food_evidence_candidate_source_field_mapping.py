from __future__ import annotations

from typing import Any

from app.nutrition.application.food_evidence_candidate_record_values import (
    dedupe,
    first_text,
    number,
    split_aliases,
    text,
)


def label_for_json_record(source_id: str, record: dict[str, Any]) -> str:
    if source_id == "base_nutrition_db":
        return first_text(record, ("title", "name", "label"))
    if source_id == "openfoodfacts_taiwan_small":
        return first_text(record, ("product_name", "generic_name"))
    if source_id == "usda_food_list_sample":
        return first_text(record, ("description", "name"))
    if source_id == "tfda_base_candidates":
        return first_text(record, ("variant", "title", "name"))
    return first_text(record, ("title", "variant", "name", "label"))


def aliases_for_json_record(
    source_id: str,
    record: dict[str, Any],
    label: str,
) -> list[str]:
    raw_aliases: list[Any] = []
    if source_id == "base_nutrition_db":
        aliases = record.get("aliases")
        if isinstance(aliases, list):
            raw_aliases.extend(aliases)
        elif aliases:
            raw_aliases.append(aliases)
    if source_id in {"tfda_base_candidates", "tfda_base_review_candidates"}:
        raw_aliases.append(record.get("brand"))
        variant = text(record.get("variant"))
        title = text(record.get("title"))
        if variant and variant != label:
            raw_aliases.append(variant)
        if title and title != label:
            raw_aliases.append(title)
    if source_id == "openfoodfacts_taiwan_small":
        raw_aliases.append(record.get("generic_name"))
    return dedupe(
        alias
        for raw in raw_aliases
        for alias in split_aliases(raw)
        if alias and alias != label
    )


def brand_for_json_record(source_id: str, record: dict[str, Any]) -> str | None:
    if source_id == "openfoodfacts_taiwan_small":
        return first_text(record, ("brands", "brand"))
    if source_id == "newtaipei_brand_candidates":
        return first_text(record, ("brand", "brands"))
    return None


def serving_basis_for_json_record(
    source_id: str, record: dict[str, Any]
) -> dict[str, Any]:
    basis = record.get("serving_basis")
    if isinstance(basis, dict):
        return basis
    if source_id in {"openfoodfacts_taiwan_small", "usda_food_list_sample"}:
        return {"unit_type": "g", "amount": 100, "label": "per_100g"}
    return {"unit_type": "g", "amount": 100, "label": "per_100g"}


def kcal_for_json_record(source_id: str, record: dict[str, Any]) -> float | None:
    if source_id == "base_nutrition_db":
        nutrition = record.get("nutrition")
        if isinstance(nutrition, dict):
            return number(nutrition.get("kcal"))
    if source_id == "openfoodfacts_taiwan_small":
        nutriments = record.get("nutriments")
        if isinstance(nutriments, dict):
            return number(
                nutriments.get("energy-kcal_100g")
                or nutriments.get("energy-kcal")
                or nutriments.get("energy_kcal_100g")
            )
    if source_id == "usda_food_list_sample":
        nutrients = record.get("foodNutrients")
        if isinstance(nutrients, list):
            for nutrient in nutrients:
                if not isinstance(nutrient, dict):
                    continue
                nutrient_name = str(nutrient.get("nutrientName") or "").lower()
                unit_name = str(nutrient.get("unitName") or "").upper()
                if "energy" in nutrient_name and unit_name == "KCAL":
                    return number(nutrient.get("value"))
    return number(
        record.get("kcal") or record.get("calories") or record.get("energy_kcal")
    )


def record_id(record: dict[str, Any]) -> str | None:
    value = (
        record.get("id")
        or record.get("code")
        or record.get("fdcId")
        or record.get("source_id")
        or record.get("產品追溯系統串接碼")
    )
    if value is None:
        return None
    return str(value)


def basic_rejection_reasons(label: str, kcal: float | None) -> list[str]:
    reasons: list[str] = []
    if not label:
        reasons.append("missing_label")
    if kcal is None:
        reasons.append("missing_kcal")
    return reasons


def serving_basis_is_present(serving_basis: dict[str, Any]) -> bool:
    if not isinstance(serving_basis, dict):
        return False
    return bool(serving_basis.get("unit_type")) and serving_basis.get("amount") not in (
        None,
        "",
    )


__all__ = [
    "aliases_for_json_record",
    "basic_rejection_reasons",
    "brand_for_json_record",
    "kcal_for_json_record",
    "label_for_json_record",
    "record_id",
    "serving_basis_for_json_record",
    "serving_basis_is_present",
]
