from __future__ import annotations

from .context_normalizer import lookup_key
from .small_anchor_types import (
    AnchorCandidate,
    AnchorModifierSchema,
    AnchorRecord,
    GenericClarifySupport,
    GenericLookupMatchPath,
)


def anchor_records_from_items(items: object) -> tuple[AnchorRecord, ...]:
    records: list[AnchorRecord] = []
    for item in items or []:
        record = _anchor_record_from_item(item)
        if record is not None:
            records.append(record)
    return tuple(records)


def _anchor_record_from_item(item: dict[str, object]) -> AnchorRecord | None:
    if str(item.get("record_kind") or "generic_anchor").strip() != "generic_anchor":
        return None
    low, high = _baseline_kcal_range(item.get("baseline_kcal_range") or [0, 0])
    return AnchorRecord(
        record_kind="generic_anchor",
        anchor_id=str(item.get("anchor_id") or "").strip(),
        canonical_name=str(item.get("canonical_name") or "").strip(),
        aliases=tuple(str(alias).strip() for alias in item.get("aliases", []) if str(alias).strip()),
        dish_type=str(item.get("dish_type") or "").strip(),
        composition_posture=_optional_text(item.get("composition_posture")),
        variance_level=_optional_text(item.get("variance_level")),
        semantic_hints=_tuple_texts(item.get("semantic_hints", [])),
        followup_hints=_tuple_texts(item.get("followup_hints", [])),
        clarify_required=bool(item.get("clarify_required") is True),
        source_posture="generic_anchor_seed",
        baseline_kcal_range=(low, high),
        baseline_likely_kcal=int(item.get("baseline_likely_kcal") or 0),
        major_modifiers=_modifier_schemas_from_items(item.get("major_modifiers", [])),
        composition_hints=_tuple_texts(item.get("composition_hints", [])),
    )


def _modifier_schemas_from_items(values: object) -> tuple[AnchorModifierSchema, ...]:
    return tuple(
        AnchorModifierSchema(
            name=str(modifier.get("name") or "").strip(),
            values=tuple(str(value).strip() for value in modifier.get("values", []) if str(value).strip()),
        )
        for modifier in values
        if str(modifier.get("name") or "").strip()
    )


def _baseline_kcal_range(kcal_range: object) -> tuple[int, int]:
    low = int(kcal_range[0]) if len(kcal_range) > 0 else 0
    high = int(kcal_range[1]) if len(kcal_range) > 1 else low
    return low, high


def candidate_from_record(
    record: AnchorRecord,
    *,
    matched_alias: str,
    match_path: GenericLookupMatchPath,
) -> AnchorCandidate:
    return AnchorCandidate(
        anchor_id=record.anchor_id,
        canonical_name=record.canonical_name,
        matched_alias=matched_alias,
        dish_type=record.dish_type,
        composition_posture=record.composition_posture,
        variance_level=record.variance_level,
        semantic_hints=record.semantic_hints,
        followup_hints=record.followup_hints,
        clarify_required=record.clarify_required,
        source_posture=record.source_posture,
        truth_level="anchor",
        support_role="lookup_support_only",
        baseline_kcal_range=record.baseline_kcal_range,
        baseline_likely_kcal=record.baseline_likely_kcal,
        major_modifiers=record.major_modifiers,
        composition_hints=record.composition_hints,
        match_path=match_path,
    )


def semantic_support_from_item(
    item: dict[str, object],
    query_keys: set[str],
) -> GenericClarifySupport | None:
    if str(item.get("record_kind") or "").strip() != "generic_semantic_only":
        return None
    canonical_name = str(item.get("canonical_name") or "").strip()
    canonical_key = lookup_key(canonical_name)
    if canonical_key in query_keys:
        return clarify_support_from_item(
            item,
            matched_alias=canonical_name,
            match_path="canonical_name_exact",
        )
    aliases = [str(alias).strip() for alias in item.get("aliases", []) if str(alias).strip()]
    for alias in aliases:
        if lookup_key(alias) in query_keys:
            return clarify_support_from_item(
                item,
                matched_alias=alias,
                match_path="alias_exact",
            )
    return None


def clarify_support_from_item(
    item: dict[str, object],
    *,
    matched_alias: str,
    match_path: GenericLookupMatchPath,
) -> GenericClarifySupport:
    return GenericClarifySupport(
        record_kind="generic_semantic_only",
        canonical_name=str(item.get("canonical_name") or "").strip(),
        matched_alias=matched_alias,
        dish_type=_optional_text(item.get("dish_type")),
        composition_posture=_optional_text(item.get("composition_posture")),
        variance_level=_optional_text(item.get("variance_level")),
        semantic_hints=_tuple_texts(item.get("semantic_hints", [])),
        followup_hints=_tuple_texts(item.get("followup_hints", [])),
        clarify_required=True,
        unresolved_reason=_optional_text(item.get("unresolved_reason")),
        match_path=match_path,
    )


def _optional_text(value: object) -> str | None:
    text = str(value or "").strip()
    return text or None


def _tuple_texts(values: object) -> tuple[str, ...]:
    return tuple(str(value).strip() for value in values or [] if str(value).strip())
