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
from .knowledge_doc_loaders import (
    load_base_nutrition_docs,
    load_common_dish_prior_docs,
    load_selected_main_docs,
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
    docs.extend(load_base_nutrition_docs(_make_doc))
    docs.extend(load_common_dish_prior_docs(_make_doc))
    docs.extend(load_selected_main_docs(_make_doc))
    return docs
