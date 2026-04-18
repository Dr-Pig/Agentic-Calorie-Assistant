from __future__ import annotations

from typing import Any

from .base_nutrition_aliases import merged_base_nutrition_aliases
from .knowledge_loader import (
    _base_nutrition_records,
    _common_dish_priors,
    _exact_item_cards,
    _load_json,
    _main_knowledge_dir,
)
from .knowledge_lookup_normalizer import (
    _compact_text,
    _expand_aliases,
    _format_kcal_band,
    _parse_kcal_band_value,
)


def _bootstrap_card_metadata(card: dict[str, Any]) -> tuple[str, str, str]:
    note = str(card.get("source_note", "") or "").lower()
    if "bootstrap" not in note:
        return "exact_truth", "exact_item", "exact"
    if "drink" in note:
        return "ingredient_anchor", "ingredient_anchor", "anchored"
    return "dish_prior", "dish_prior", "anchored"


def _make_doc(
    *,
    source_type: str,
    title: str,
    aliases: list[str],
    category: str = "",
    content: str = "",
    common_components: list[str] | None = None,
    portion_notes: str = "",
    kcal_band: str | None = None,
    must_ask_if_uncertain: list[str] | None = None,
    notes: str = "",
    brand: str = "",
    source_url: str | None = None,
    confidence: str = "medium",
    evidence_role: str = "unknown",
    record_role: str = "",
    macro_completeness: str = "unknown",
    estimate_eligibility: str = "heuristic_only",
    portion_basis_quality: str = "medium",
    protein_g: float | int | None = None,
    carb_g: float | int | None = None,
    fat_g: float | int | None = None,
    sodium_mg: float | int | None = None,
) -> dict[str, Any]:
    expanded_aliases = _expand_aliases(title=title, aliases=aliases, brand=brand)
    kcal_value = _parse_kcal_band_value(kcal_band)
    source_class_map = {
        "exact_item_card": "exact_item_db",
        "base_nutrition": "base_nutrition_db",
        "common_dish_prior": "base_nutrition_db",
        "convenience_archetype": "meal_template_db",
        "chain_menu_card": "exact_item_db",
        "ramen_shop_profile": "meal_template_db",
    }
    return {
        "source_type": source_type,
        "source_class": source_class_map.get(str(source_type), "unknown"),
        "brand": brand,
        "title": title,
        "aliases": expanded_aliases,
        "category": category,
        "content": content,
        "common_components": common_components or [],
        "portion_notes": portion_notes,
        "serving_basis": portion_notes,
        "kcal_band": kcal_band,
        "kcal": kcal_value,
        "label_kcal": kcal_value,
        "must_ask_if_uncertain": must_ask_if_uncertain or [],
        "notes": notes,
        "source_url": source_url,
        "confidence": confidence,
        "evidence_role": evidence_role,
        "record_role": record_role,
        "macro_completeness": macro_completeness,
        "estimate_eligibility": estimate_eligibility,
        "portion_basis_quality": portion_basis_quality,
        "identity_confidence": "none",
        "provenance": {
            "source_type": source_type,
            "source_url": source_url,
            "source_name": title,
        },
        "conflict_status": "none",
        "selected": False,
        "drop_reason": None,
        "protein_g": protein_g,
        "carb_g": carb_g,
        "fat_g": fat_g,
        "sodium_mg": sodium_mg,
    }


def _load_selected_main_docs() -> list[dict[str, Any]]:
    knowledge_dir = _main_knowledge_dir()
    docs: list[dict[str, Any]] = []

    for entry in (_load_json(knowledge_dir / "convenience_store_archetypes_tw.json") or []):
        title = str(entry.get("name", "")).strip()
        if not title:
            continue
        docs.append(
            _make_doc(
                source_type="convenience_archetype",
                title=title,
                aliases=[title, *[item for item in entry.get("aliases", []) if isinstance(item, str)]],
                category=str(entry.get("category", "")),
                content=_compact_text(
                    [
                        str(entry.get("typical_serving", "")),
                        f"{entry.get('typical_kcal_low', '')}-{entry.get('typical_kcal_high', '')} kcal",
                        str(entry.get("why_stable", "")),
                    ]
                ),
                portion_notes=str(entry.get("typical_serving", "")),
                kcal_band=f"{entry.get('typical_kcal_low', '')}-{entry.get('typical_kcal_high', '')} kcal",
                notes=str(entry.get("why_risky", "")),
                source_url=entry.get("source_url"),
                confidence=str(entry.get("confidence", "medium")),
            )
        )

    for entry in (_load_json(knowledge_dir / "chain_menu_cards_tw.json") or []):
        chain_id = str(entry.get("chain_id", "")).strip().lower()
        if chain_id not in {"kebuke", "subway"}:
            continue
        title = str(entry.get("item_name") or entry.get("name") or "").strip()
        if not title:
            continue
        docs.append(
            _make_doc(
                source_type="chain_menu_card",
                title=title,
                aliases=[title, *[item for item in entry.get("aliases", []) if isinstance(item, str)]],
                brand=chain_id,
                category=str(entry.get("item_family", "")),
                content=_compact_text(
                    [
                        str(entry.get("serving_basis", "")),
                        f"{entry.get('kcal', '')} kcal" if entry.get("kcal") else "",
                        str(entry.get("notes", "")),
                    ]
                ),
                portion_notes=str(entry.get("serving_basis", "")),
                kcal_band=f"{int(entry['kcal'])} kcal" if isinstance(entry.get("kcal"), (int, float)) else None,
                notes=str(entry.get("notes", "")),
                source_url=entry.get("source_url"),
                confidence=str(entry.get("confidence", "medium")),
            )
        )

    for entry in (_load_json(knowledge_dir / "ramen_shop_profiles_tw.json") or []):
        title = str(entry.get("name", "")).strip()
        if not title:
            continue
        docs.append(
            _make_doc(
                source_type="ramen_shop_profile",
                title=title,
                aliases=[title, *[item for item in entry.get("aliases", []) if isinstance(item, str)]],
                brand=title,
                category="ramen",
                content=_compact_text(
                    [
                        str(entry.get("representative_bowl", "")),
                        f"{entry.get('default_total_kcal_low', '')}-{entry.get('default_total_kcal_high', '')} kcal",
                        str(entry.get("notes", "")),
                    ]
                ),
                common_components=[item for item in entry.get("default_toppings", []) if isinstance(item, str)],
                portion_notes=str(entry.get("serving_basis", "")),
                kcal_band=f"{entry.get('default_total_kcal_low', '')}-{entry.get('default_total_kcal_high', '')} kcal",
                notes=str(entry.get("why_range_moves", "")),
                confidence="medium",
            )
        )

    return docs


def _load_base_nutrition_docs() -> list[dict[str, Any]]:
    docs: list[dict[str, Any]] = []
    for record in _base_nutrition_records():
        title = str(record.get("title", "")).strip()
        if not title:
            continue
        nutrition = record.get("nutrition") or {}
        serving_basis = record.get("serving_basis") or {}
        portion_label = str(serving_basis.get("label", "")).strip()
        kcal_band = _format_kcal_band(nutrition.get("kcal"))
        protein = nutrition.get("protein_g")
        carb = nutrition.get("carb_g")
        fat = nutrition.get("fat_g")
        if all(isinstance(value, (int, float)) for value in (protein, carb, fat)):
            macro_completeness = "complete"
            estimate_eligibility = "anchored"
        elif isinstance(nutrition.get("kcal"), (int, float)):
            macro_completeness = "kcal_only"
            estimate_eligibility = "heuristic_only"
        else:
            macro_completeness = "partial"
            estimate_eligibility = "heuristic_only"
        amount = serving_basis.get("amount")
        portion_basis_quality = "strong" if isinstance(amount, (int, float)) and float(amount) >= 80 else "medium"
        docs.append(
            _make_doc(
                source_type="base_nutrition",
                title=title,
                aliases=merged_base_nutrition_aliases(record),
                category=str(record.get("category", "")),
                content=_compact_text([portion_label, kcal_band or "", str(record.get("notes", ""))]),
                portion_notes=portion_label,
                kcal_band=kcal_band,
                notes=str(record.get("notes", "")),
                source_url=record.get("source_url"),
                confidence=str(record.get("confidence", "medium")),
                evidence_role="ingredient_anchor",
                record_role="ingredient_anchor",
                macro_completeness=macro_completeness,
                estimate_eligibility=estimate_eligibility,
                portion_basis_quality=portion_basis_quality,
                protein_g=protein,
                carb_g=carb,
                fat_g=fat,
                sodium_mg=nutrition.get("sodium_mg"),
            )
        )
    return docs


def _load_common_dish_prior_docs() -> list[dict[str, Any]]:
    docs: list[dict[str, Any]] = []
    for record in _common_dish_priors():
        title = str(record.get("title", "")).strip()
        if not title:
            continue
        nutrition = record.get("nutrition") or {}
        serving_basis = record.get("serving_basis") or {}
        portion_label = str(serving_basis.get("label", "")).strip()
        kcal_band = _format_kcal_band(nutrition.get("kcal"))
        docs.append(
            _make_doc(
                source_type="common_dish_prior",
                title=title,
                aliases=[title, *[str(item) for item in record.get("aliases", []) if str(item).strip()]],
                category=str(record.get("category", "")),
                content=_compact_text(
                    [
                        portion_label,
                        kcal_band or "",
                        " ".join(str(item) for item in record.get("common_components", []) if str(item).strip()),
                        str(record.get("notes", "")),
                    ]
                ),
                common_components=[str(item) for item in record.get("common_components", []) if str(item).strip()],
                portion_notes=portion_label,
                kcal_band=kcal_band,
                notes=str(record.get("notes", "")),
                confidence=str(record.get("confidence", "medium")),
                evidence_role="dish_prior",
                record_role="dish_prior",
                macro_completeness="complete",
                estimate_eligibility="anchored",
                portion_basis_quality="strong",
                protein_g=nutrition.get("protein_g"),
                carb_g=nutrition.get("carb_g"),
                fat_g=nutrition.get("fat_g"),
                sodium_mg=nutrition.get("sodium_mg"),
            )
        )
    return docs


def load_retrieval_documents() -> list[dict[str, Any]]:
    docs: list[dict[str, Any]] = []
    for card in _exact_item_cards():
        common_components = [item for item in card.get("common_components", []) if isinstance(item, str)]
        evidence_role, record_role, estimate_eligibility = _bootstrap_card_metadata(card)
        docs.append(
            _make_doc(
                source_type=card.get("source_type", "exact_item_card"),
                title=str(card.get("title", "")),
                aliases=[str(card.get("title", "")), *[item for item in card.get("aliases", []) if isinstance(item, str)]],
                brand=str(card.get("brand", "")),
                category=str(card.get("category", "")),
                content=_compact_text(
                    [
                        " ".join(common_components),
                        str(card.get("portion_notes", "")),
                        str(card.get("kcal_band", "")),
                    ]
                ),
                common_components=common_components,
                portion_notes=str(card.get("portion_notes", "")),
                kcal_band=str(card.get("kcal_band", "")) or None,
                must_ask_if_uncertain=[item for item in card.get("must_ask_if_uncertain", []) if isinstance(item, str)],
                notes=str(card.get("source_note", "")),
                source_url=card.get("source_url"),
                confidence=str(card.get("confidence", "medium")),
                evidence_role=evidence_role,
                record_role=record_role,
                macro_completeness="complete",
                estimate_eligibility=estimate_eligibility,
                portion_basis_quality="strong",
            )
        )
    docs.extend(_load_base_nutrition_docs())
    docs.extend(_load_common_dish_prior_docs())
    docs.extend(_load_selected_main_docs())
    return docs
