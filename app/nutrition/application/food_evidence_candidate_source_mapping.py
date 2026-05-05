from __future__ import annotations

from typing import Any, Callable

from app.nutrition.application.food_evidence_candidate_csv_field_mapping import (
    aliases_for_csv_record,
    brand_for_csv_record,
    label_for_csv_record,
    serving_basis_and_kcal_for_csv_record,
)
from app.nutrition.application.food_evidence_candidate_record_values import (
    csv_value,
    dedupe,
    first_text,
    number,
    split_aliases,
    split_multivalue_field,
    text,
)
from app.nutrition.application.food_evidence_candidate_source_field_mapping import (
    aliases_for_json_record,
    basic_rejection_reasons,
    brand_for_json_record,
    kcal_for_json_record,
    label_for_json_record,
    record_id,
    serving_basis_for_json_record,
    serving_basis_is_present,
)
from app.nutrition.application.food_raw_source_inventory import RawSourceDefinition

CandidateBuilder = Callable[..., dict[str, Any]]


def candidate_from_json_record(
    definition: RawSourceDefinition,
    record: dict[str, Any],
    row_index: int,
    build_candidate: CandidateBuilder,
) -> tuple[dict[str, Any], list[str]]:
    source_id = definition.source_id
    label = label_for_json_record(source_id, record)
    kcal = kcal_for_json_record(source_id, record)
    reasons = basic_rejection_reasons(label=label, kcal=kcal)
    if reasons:
        return {}, reasons

    aliases = aliases_for_json_record(source_id, record, label)
    serving_basis = serving_basis_for_json_record(source_id, record)
    return (
        build_candidate(
            definition=definition,
            label=label,
            row_index=row_index,
            record_id=record_id(record),
            kcal=kcal,
            aliases=aliases,
            category=first_text(record, ("category", "dataType")),
            brand=brand_for_json_record(source_id, record),
            serving_basis=serving_basis,
            source_url=first_text(record, ("source_url", "url")),
            raw_record=record,
            extra_provenance=None,
        ),
        [],
    )


def candidate_from_csv_record(
    definition: RawSourceDefinition,
    record: dict[str, Any],
    row_index: int,
    build_candidate: CandidateBuilder,
) -> tuple[dict[str, Any], list[str]]:
    source_id = definition.source_id
    label = label_for_csv_record(source_id, record)
    serving_basis, nutrition_basis, basis_candidates, kcal = (
        serving_basis_and_kcal_for_csv_record(
            source_id,
            record,
        )
    )
    reasons = basic_rejection_reasons(label=label, kcal=kcal)
    if not serving_basis_is_present(serving_basis):
        reasons.append("missing_serving_basis")
    if reasons:
        return {}, dedupe(reasons)

    brand = brand_for_csv_record(source_id, record)
    image_urls = split_multivalue_field(
        csv_value(
            record,
            "正面外包裝照片",
            "反面外包裝照片",
            "側面外包裝照片",
            "營養標示圖片",
            "內容物標示圖片",
            "image_urls",
            "image_url",
            "images",
            "image",
        )
    )
    return (
        build_candidate(
            definition=definition,
            label=label,
            row_index=row_index,
            record_id=record_id(record),
            kcal=kcal,
            aliases=aliases_for_csv_record(source_id, record, label),
            category=csv_value(record, "產品分類", "category"),
            brand=brand,
            serving_basis=serving_basis,
            source_url=image_urls[0] if image_urls else None,
            raw_record=record,
            extra_provenance={
                "company_name": brand,
                "product_name": label,
                "package_size": csv_value(
                    record, "包裝規格", "package_size", "package", "spec"
                ),
                "nutrition_basis": nutrition_basis,
                "basis_candidates": basis_candidates,
                "image_urls": image_urls,
            },
        ),
        [],
    )


def candidate_from_xlsx_record(
    definition: RawSourceDefinition,
    record: dict[str, Any],
    row_index: int,
    build_candidate: CandidateBuilder,
) -> tuple[dict[str, Any], list[str]]:
    label = text(record.get("label"))
    kcal = number(record.get("corrected_kcal")) or number(record.get("kcal"))
    reasons = basic_rejection_reasons(label=label, kcal=kcal)
    if reasons:
        return {}, reasons
    return (
        build_candidate(
            definition=definition,
            label=label,
            row_index=row_index,
            record_id=None,
            kcal=kcal,
            aliases=split_aliases(record.get("aliases")),
            category=text(record.get("category")),
            brand=None,
            serving_basis={
                "unit_type": "g",
                "amount": 100,
                "label": "per_100g_edible_portion",
            },
            source_url=None,
            raw_record=record,
            extra_provenance=None,
        ),
        [],
    )


__all__ = [
    "candidate_from_csv_record",
    "candidate_from_json_record",
    "candidate_from_xlsx_record",
    "record_id",
]
