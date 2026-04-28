from __future__ import annotations

from typing import Any

from .base_nutrition_aliases import merged_base_nutrition_aliases
from .knowledge_loader import _base_nutrition_records, _common_dish_priors, _load_json, _main_knowledge_dir
from .knowledge_lookup_normalizer import _compact_text, _format_kcal_band


def load_selected_main_docs(make_doc) -> list[dict[str, Any]]:
    knowledge_dir = _main_knowledge_dir()
    docs: list[dict[str, Any]] = []

    for entry in (_load_json(knowledge_dir / "convenience_store_archetypes_tw.json") or []):
        title = str(entry.get("name", "")).strip()
        if title:
            docs.append(
                make_doc(
                    source_type="convenience_archetype",
                    title=title,
                    aliases=[title, *[item for item in entry.get("aliases", []) if isinstance(item, str)]],
                    category=str(entry.get("category", "")),
                    content=_compact_text([str(entry.get("typical_serving", "")), f"{entry.get('typical_kcal_low', '')}-{entry.get('typical_kcal_high', '')} kcal", str(entry.get("why_stable", ""))]),
                    portion_notes=str(entry.get("typical_serving", "")),
                    kcal_band=f"{entry.get('typical_kcal_low', '')}-{entry.get('typical_kcal_high', '')} kcal",
                    notes=str(entry.get("why_risky", "")),
                    source_url=entry.get("source_url"),
                    confidence=str(entry.get("confidence", "medium")),
                )
            )

    for entry in (_load_json(knowledge_dir / "chain_menu_cards_tw.json") or []):
        chain_id = str(entry.get("chain_id", "")).strip().lower()
        title = str(entry.get("item_name") or entry.get("name") or "").strip()
        if chain_id in {"kebuke", "subway"} and title:
            docs.append(
                make_doc(
                    source_type="chain_menu_card",
                    title=title,
                    aliases=[title, *[item for item in entry.get("aliases", []) if isinstance(item, str)]],
                    brand=chain_id,
                    category=str(entry.get("item_family", "")),
                    content=_compact_text([str(entry.get("serving_basis", "")), f"{entry.get('kcal', '')} kcal" if entry.get("kcal") else "", str(entry.get("notes", ""))]),
                    portion_notes=str(entry.get("serving_basis", "")),
                    kcal_band=f"{int(entry['kcal'])} kcal" if isinstance(entry.get("kcal"), (int, float)) else None,
                    notes=str(entry.get("notes", "")),
                    source_url=entry.get("source_url"),
                    confidence=str(entry.get("confidence", "medium")),
                )
            )

    for entry in (_load_json(knowledge_dir / "ramen_shop_profiles_tw.json") or []):
        title = str(entry.get("name", "")).strip()
        if title:
            docs.append(
                make_doc(
                    source_type="ramen_shop_profile",
                    title=title,
                    aliases=[title, *[item for item in entry.get("aliases", []) if isinstance(item, str)]],
                    brand=title,
                    category="ramen",
                    content=_compact_text([str(entry.get("representative_bowl", "")), f"{entry.get('default_total_kcal_low', '')}-{entry.get('default_total_kcal_high', '')} kcal", str(entry.get("notes", ""))]),
                    common_components=[item for item in entry.get("default_toppings", []) if isinstance(item, str)],
                    portion_notes=str(entry.get("serving_basis", "")),
                    kcal_band=f"{entry.get('default_total_kcal_low', '')}-{entry.get('default_total_kcal_high', '')} kcal",
                    notes=str(entry.get("why_range_moves", "")),
                    confidence="medium",
                )
            )

    return docs


def load_base_nutrition_docs(make_doc) -> list[dict[str, Any]]:
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
            make_doc(
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


def load_common_dish_prior_docs(make_doc) -> list[dict[str, Any]]:
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
            make_doc(
                source_type="common_dish_prior",
                title=title,
                aliases=[title, *[str(item) for item in record.get("aliases", []) if str(item).strip()]],
                category=str(record.get("category", "")),
                content=_compact_text([portion_label, kcal_band or "", " ".join(str(item) for item in record.get("common_components", []) if str(item).strip()), str(record.get("notes", ""))]),
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
