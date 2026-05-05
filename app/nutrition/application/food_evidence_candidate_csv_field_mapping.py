from __future__ import annotations

from typing import Any

from app.nutrition.application.food_evidence_candidate_record_values import (
    csv_value,
    dedupe,
    number,
    parse_amount_and_unit,
)


def label_for_csv_record(source_id: str, record: dict[str, Any]) -> str:
    if source_id == "local_tw_packaged_extract_188_2":
        return csv_value(
            record, "產品名稱", "product_name", "product", "name", "item_name"
        )
    return first_text(record, ("title", "name", "label"))


def aliases_for_csv_record(
    source_id: str,
    record: dict[str, Any],
    label: str,
) -> list[str]:
    if source_id != "local_tw_packaged_extract_188_2":
        return []
    company = csv_value(
        record, "公司名稱", "company_name", "company", "brand", "manufacturer"
    )
    package_size = csv_value(record, "包裝規格", "package_size", "package", "spec")
    return dedupe(
        alias
        for alias in (
            f"{company} {label}".strip(),
            f"{label} {package_size}".strip(),
        )
        if alias and alias != label
    )


def brand_for_csv_record(source_id: str, record: dict[str, Any]) -> str | None:
    if source_id == "local_tw_packaged_extract_188_2":
        return (
            csv_value(
                record, "公司名稱", "company_name", "company", "brand", "manufacturer"
            )
            or None
        )
    return None


def serving_basis_and_kcal_for_csv_record(
    source_id: str,
    record: dict[str, Any],
) -> tuple[dict[str, Any], str, dict[str, float], float | None]:
    if source_id != "local_tw_packaged_extract_188_2":
        return {"unit_type": "", "amount": None, "label": ""}, "", {}, None

    per_serving = number(
        csv_value(record, "每份熱量", "kcal_per_serving", "calories_per_serving")
    )
    per_100g = number(
        csv_value(record, "每100公克熱量", "kcal_per_100g", "calories_per_100g")
    )
    per_100ml = number(
        csv_value(record, "每100毫升熱量", "kcal_per_100ml", "calories_per_100ml")
    )
    basis_candidates: dict[str, float] = {}
    if per_serving is not None:
        basis_candidates["per_serving"] = per_serving
    if per_100g is not None:
        basis_candidates["per_100g"] = per_100g
    if per_100ml is not None:
        basis_candidates["per_100ml"] = per_100ml

    if per_serving is not None:
        amount, unit_type = parse_amount_and_unit(
            csv_value(record, "每一份量", "serving_size", "serving", "serving_amount")
        )
        if amount is not None and unit_type:
            return (
                {"unit_type": unit_type, "amount": amount, "label": "per_serving"},
                "per_serving",
                basis_candidates,
                per_serving,
            )
    if per_100g is not None:
        return (
            {"unit_type": "g", "amount": 100, "label": "per_100g"},
            "per_100g",
            basis_candidates,
            per_100g,
        )
    if per_100ml is not None:
        return (
            {"unit_type": "ml", "amount": 100, "label": "per_100ml"},
            "per_100ml",
            basis_candidates,
            per_100ml,
        )
    return {"unit_type": "", "amount": None, "label": ""}, "", basis_candidates, None


__all__ = [
    "aliases_for_csv_record",
    "brand_for_csv_record",
    "label_for_csv_record",
    "serving_basis_and_kcal_for_csv_record",
]
