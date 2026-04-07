from __future__ import annotations

import json
import re
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Any

from .base_nutrition_aliases import merged_base_nutrition_aliases


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _main_knowledge_dir() -> Path:
    return _repo_root().parent / "line-liff-calorie-helper-main" / "knowledge"


def _local_knowledge_dir() -> Path:
    return _repo_root() / "app" / "knowledge"


def _normalize(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text or "").strip()
    variant_map = {
        "鷄": "雞",
        "雞塊": "雞塊",
    }
    for src, dst in variant_map.items():
        normalized = normalized.replace(src, dst)
    return normalized


def _canonicalize_lookup_text(text: str) -> str:
    normalized = _normalize_lower(text)
    normalized = re.sub(r"[「」『』（）()【】\[\]<>〈〉《》]", " ", normalized)
    normalized = re.sub(r"[,，、:：;；/／|｜+＋]", " ", normalized)
    normalized = normalized.replace("的", " ")
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def _normalize_lower(text: str) -> str:
    return _normalize(text).lower()


def _normalize_tokens(text: str) -> list[str]:
    normalized = _canonicalize_lookup_text(text)
    return [token for token in re.findall(r"[a-z0-9\u4e00-\u9fff]+", normalized) if len(token) > 1]


def _lookup_key(text: str) -> str:
    return "".join(_normalize_tokens(text))


def _load_json(path: Path) -> Any:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _risk_profiles() -> list[dict[str, Any]]:
    payload = _load_json(_local_knowledge_dir() / "risk_gate_packets_tw.json") or {}
    return list(payload.get("profiles", []))


@lru_cache(maxsize=1)
def _exact_item_cards() -> list[dict[str, Any]]:
    payload = _load_json(_local_knowledge_dir() / "exact_item_cards_tw.json") or {}
    return list(payload.get("cards", []))


def _bootstrap_card_metadata(card: dict[str, Any]) -> tuple[str, str, str]:
    note = str(card.get("source_note", "") or "").lower()
    if "bootstrap" not in note:
        return "exact_truth", "exact_item", "exact"
    if "drink" in note:
        return "ingredient_anchor", "ingredient_anchor", "anchored"
    return "dish_prior", "dish_prior", "anchored"


@lru_cache(maxsize=1)
def _meal_templates() -> list[dict[str, Any]]:
    payload = _load_json(_local_knowledge_dir() / "meal_templates_tw.json") or {}
    return list(payload.get("templates", []))


@lru_cache(maxsize=1)
def _base_nutrition_records() -> list[dict[str, Any]]:
    payload = _load_json(_local_knowledge_dir() / "base_nutrition_db.json") or {}
    return list(payload.get("records", []))


@lru_cache(maxsize=1)
def _common_dish_priors() -> list[dict[str, Any]]:
    payload = _load_json(_local_knowledge_dir() / "common_dish_priors_tw.json") or {}
    return list(payload.get("records", []))


def _match_exact_keywords(profile: dict[str, Any], lowered: str) -> list[str]:
    hits: list[str] = []
    for keyword in profile.get("keywords", []):
        normalized = _normalize_lower(str(keyword))
        if normalized and normalized in lowered:
            hits.append(f"keyword:{keyword}")
    return hits


def _match_patterns(profile: dict[str, Any], text: str) -> list[str]:
    hits: list[str] = []
    for pattern in profile.get("patterns", []):
        raw = str(pattern).strip()
        if not raw:
            continue
        try:
            if re.search(raw, text, flags=re.IGNORECASE):
                hits.append(f"pattern:{raw}")
        except re.error:
            continue
    return hits


def _match_shop_aliases(profile: dict[str, Any], lowered: str) -> list[str]:
    hits: list[str] = []
    for alias in profile.get("shop_aliases", []):
        normalized = _normalize_lower(str(alias))
        if normalized and normalized in lowered:
            hits.append(f"shop:{alias}")
    return hits


def _extract_portion_clues(user_input: str, profiles: list[dict[str, Any]]) -> dict[str, Any]:
    matched: list[str] = []
    review_focus: list[str] = []
    lowered = _normalize_lower(user_input)
    for profile in profiles:
        for clue in profile.get("portion_clues", []):
            normalized = _normalize_lower(str(clue))
            if normalized and normalized in lowered:
                matched.append(str(clue))
                review_focus.append(f"注意份量詞：{clue}")
    return {
        "matched": list(dict.fromkeys(matched)),
        "review_focus": list(dict.fromkeys(review_focus)),
    }


def build_gate_packet(user_input: str, *, components: list[str] | None = None) -> dict[str, Any]:
    text = _normalize(user_input)
    lowered = text.lower()
    risk_flags: list[str] = []
    review_focus: list[str] = []
    must_ask_if_uncertain: list[str] = []
    required_checks: dict[str, list[dict[str, Any]]] = {}
    private_only = False
    risk_match_reasons: dict[str, list[str]] = {}

    profiles = _risk_profiles()
    for profile in profiles:
        reasons = (
            _match_exact_keywords(profile, lowered)
            + _match_patterns(profile, text)
            + _match_shop_aliases(profile, lowered)
        )
        if not reasons:
            continue
        risk_key = str(profile["risk_key"])
        risk_flags.append(risk_key)
        risk_match_reasons[risk_key] = reasons
        review_focus.extend(str(item) for item in profile.get("review_focus", []))
        must_ask_if_uncertain.extend(str(item) for item in profile.get("must_ask_if_uncertain", []))
        required_checks[risk_key] = list(profile.get("required_checks", []))
        private_only = private_only or bool(profile.get("private_only"))

    portion_clues = _extract_portion_clues(text, profiles)
    review_focus.extend(portion_clues["review_focus"])

    return {
        "risk_flags": list(dict.fromkeys(risk_flags)),
        "review_focus": list(dict.fromkeys(review_focus)),
        "must_ask_if_uncertain": list(dict.fromkeys(must_ask_if_uncertain)),
        "portion_clues": portion_clues,
        "required_checks": required_checks,
        "components_seen": [item.strip() for item in (components or []) if isinstance(item, str) and item.strip()],
        "private_only": private_only,
        "risk_match_reasons": risk_match_reasons,
        "schema_version": "v10.1-risk-gate.v2",
    }


def match_meal_template(user_input: str, risk_packet: dict[str, Any] | None = None) -> dict[str, Any] | None:
    text = _normalize(user_input)
    lowered = text.lower()
    risk_flags = set((risk_packet or {}).get("risk_flags", []))
    best: tuple[int, dict[str, Any]] | None = None
    for template in _meal_templates():
        score = 0
        category = str(template.get("category", "")).strip()
        if category and category in risk_flags:
            score += 6
        for keyword in template.get("trigger_keywords", []):
            normalized = _normalize_lower(str(keyword))
            if normalized and normalized in lowered:
                score += 5
        for alias in template.get("aliases", []):
            normalized = _normalize_lower(str(alias))
            if normalized and normalized in lowered:
                score += 6
        for pattern in template.get("trigger_patterns", []):
            raw = str(pattern).strip()
            if not raw:
                continue
            try:
                if re.search(raw, text, flags=re.IGNORECASE):
                    score += 4
            except re.error:
                continue
        if score <= 0:
            continue
        if best is None or score > best[0]:
            best = (score, template)
    if best is None:
        return None
    return dict(best[1])


def _compact_text(parts: list[str]) -> str:
    return " ".join(part.strip() for part in parts if isinstance(part, str) and part.strip())


def _format_kcal_band(value: Any) -> str | None:
    if not isinstance(value, (int, float)):
        return None
    rounded = round(float(value), 1)
    if rounded.is_integer():
        return f"{int(rounded)} kcal"
    return f"{rounded} kcal"


def _parse_kcal_band_value(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value or "").strip().lower()
    if not text:
        return None
    match = re.search(r"(\d+(?:\.\d+)?)", text)
    if not match:
        return None
    try:
        return float(match.group(1))
    except ValueError:
        return None


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


def _brand_alias_variants(brand: str) -> list[str]:
    normalized = _normalize(str(brand))
    if not normalized:
        return []
    variants = [normalized]
    replacements = {
        "五十嵐": ["50嵐", "５０嵐"],
        "50嵐": ["五十嵐", "５０嵐"],
        "５０嵐": ["五十嵐", "50嵐"],
    }
    for item in replacements.get(normalized, []):
        if item not in variants:
            variants.append(item)
    return variants


def _expand_aliases(*, title: str, aliases: list[str], brand: str) -> list[str]:
    raw_aliases = [str(item).strip() for item in [title, *aliases] if str(item).strip()]
    expanded: list[str] = []
    brand_variants = _brand_alias_variants(brand)
    brand_keys = [_lookup_key(item) for item in brand_variants if _lookup_key(item)]
    for alias in raw_aliases:
        normalized = _normalize(alias)
        if not normalized:
            continue
        candidates = {
            normalized,
            re.sub(r"[()（）]", "", normalized).strip(),
        }
        alias_key = _lookup_key(normalized)
        for brand_variant, brand_key in zip(brand_variants, brand_keys):
            if brand_variant and brand_variant not in candidates and normalized.startswith(brand_variant):
                stripped = normalized[len(brand_variant) :].strip(" -_")
                if stripped:
                    candidates.add(stripped)
            if brand_key and alias_key.startswith(brand_key):
                stripped_key = alias_key[len(brand_key) :]
                if stripped_key:
                    candidates.add(stripped_key)
        for candidate in candidates:
            cleaned = candidate.strip()
            if cleaned and cleaned not in expanded:
                expanded.append(cleaned)
    for brand_variant in brand_variants:
        if brand_variant and brand_variant not in expanded:
            expanded.append(brand_variant)
    return expanded


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
                content=_compact_text(
                    [
                        portion_label,
                        kcal_band or "",
                        str(record.get("notes", "")),
                    ]
                ),
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


@lru_cache(maxsize=1)
def _exact_item_signal_tokens() -> set[str]:
    tokens: set[str] = set()
    for card in _exact_item_cards():
        for field in (
            str(card.get("brand", "")),
            str(card.get("title", "")),
            *[str(item) for item in card.get("aliases", []) if isinstance(item, str)],
        ):
            tokens.update(_normalize_tokens(field))
    return tokens


@lru_cache(maxsize=1)
def _exact_item_brand_keys() -> set[str]:
    keys: set[str] = set()
    for card in _exact_item_cards():
        brand = _lookup_key(str(card.get("brand", "")))
        if brand:
            keys.add(brand)
    return keys


@lru_cache(maxsize=1)
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


def _match_metadata(doc: dict[str, Any], query: str, user_input: str, query_tokens: list[str]) -> dict[str, Any]:
    query_key = _lookup_key(query)
    user_key = _lookup_key(user_input)
    title_key = _lookup_key(str(doc.get("title", "")))
    alias_keys = {_lookup_key(item) for item in doc.get("aliases", []) if _lookup_key(item)}
    brand_key = _lookup_key(str(doc.get("brand", "")))
    exact_brand_keys = _exact_item_brand_keys()
    _query_token_keys = [_lookup_key(t) for t in query_tokens if len(_lookup_key(t)) >= 2]
    _user_token_keys = [_lookup_key(t) for t in (_normalize_tokens(user_input) if user_input else []) if len(_lookup_key(t)) >= 2]
    query_brand_keys = {key for key in exact_brand_keys if key and (key in query_key or key in user_key or any(len(tk) >= 2 and tk in key for tk in _query_token_keys) or any(len(tk) >= 2 and tk in key for tk in _user_token_keys))}
    brand_in_query = bool(brand_key and (brand_key in query_key or brand_key in user_key or any(len(tk) >= 2 and tk in brand_key for tk in _query_token_keys) or any(len(tk) >= 2 and tk in brand_key for tk in _user_token_keys)))
    key_pool = {title_key, *alias_keys}
    key_pool.discard("")

    if title_key and (query_key == title_key or user_key == title_key):
        return {"match_confidence": "high", "match_path": "exact_title", "brand_conflict": False}
    if query_key and query_key in alias_keys or user_key and user_key in alias_keys:
        return {"match_confidence": "high", "match_path": "exact_alias", "brand_conflict": False}

    if doc.get("source_type") == "exact_item_card" and query_brand_keys and not brand_in_query:
        return {"match_confidence": "none", "match_path": "brand_conflict", "brand_conflict": True}

    # --- Identity Gate: Core Food Noun Protection ---
    modifiers = {"大杯", "中杯", "小杯", "微糖", "半糖", "少糖", "全糖", "正常糖", "無糖", "去冰", "微冰", "少冰", "正常冰", "冰", "熱", "溫"}
    
    def get_clean_core(text: str, brand: str) -> set[str]:
        tokens = _normalize_tokens(text)
        b_key = _normalize_lower(brand)
        clean = set()
        for t in tokens:
            cleaned = t
            # 1. Strip brand
            if b_key and b_key in cleaned:
                cleaned = cleaned.replace(b_key, "").strip()
            # 2. Strip modifiers
            for mod in modifiers:
                if mod in cleaned:
                    cleaned = cleaned.replace(mod, "").strip()
            if len(cleaned) >= 1:
                clean.add(cleaned)
        return clean

    doc_core = get_clean_core(str(doc.get("title", "")), str(doc.get("brand", "")))
    user_core = get_clean_core(user_input, str(doc.get("brand", "")))
    query_core = get_clean_core(query, str(doc.get("brand", "")))

    core_overlap = False
    if not doc_core:
        core_overlap = True # No identifiable core, pass through to fuzzy
    else:
        # Must match at least one core noun string exactly or as a significant overlapping substring
        for dc in doc_core:
            if any((dc in uc or uc in dc) for uc in user_core) or any((dc in qc or qc in dc) for qc in query_core):
                core_overlap = True
                break
    
    if not core_overlap:
        return {"match_confidence": "none", "match_path": "core_identity_mismatch", "brand_conflict": False}

    # --- Fuzzy Match Logic ---
    for key in key_pool:
        if key and len(key) >= 4 and ((query_key and key in query_key) or (user_key and key in user_key) or (query_key and query_key in key) or (user_key and user_key in key)):
            if brand_in_query:
                return {"match_confidence": "high", "match_path": "brand_plus_alias_partial", "brand_conflict": False}
            return {"match_confidence": "medium", "match_path": "alias_partial", "brand_conflict": False}

    if brand_in_query:
        if doc_core and any(any(sc in uc or uc in sc for uc in user_core) for sc in doc_core):
             return {"match_confidence": "medium", "match_path": "brand_plus_core_token", "brand_conflict": False}
        return {"match_confidence": "low", "match_path": "brand_only", "brand_conflict": False}

    if query_tokens and any(token in " ".join(doc.get("aliases", [])).lower() for token in query_tokens):
        return {"match_confidence": "low", "match_path": "token_overlap", "brand_conflict": False}

    return {"match_confidence": "none", "match_path": "no_match", "brand_conflict": False}


def _score_doc(doc: dict[str, Any], query: str, user_input: str, query_tokens: list[str], user_tokens: list[str], risk_flags: list[str]) -> tuple[int, dict[str, Any]]:
    haystack = " ".join(
        [
            str(doc.get("title", "")),
            " ".join(doc.get("aliases", [])),
            str(doc.get("brand", "")),
            str(doc.get("category", "")),
            str(doc.get("content", "")),
            " ".join(doc.get("common_components", [])),
            str(doc.get("portion_notes", "")),
            str(doc.get("kcal_band", "")),
        ]
    ).lower()
    score = 0
    title = str(doc.get("title", "")).lower()
    aliases = [item.lower() for item in doc.get("aliases", [])]
    title_alias_query_hits = 0
    exact_title_alias_hits = 0
    exact_signal_tokens = _exact_item_signal_tokens()
    query_has_exact_item_signal = any(token in exact_signal_tokens for token in query_tokens)
    match_meta = _match_metadata(doc, query, user_input, query_tokens)

    for token in query_tokens:
        if token == title or any(token == alias for alias in aliases):
            score += 20
            title_alias_query_hits += 1
            exact_title_alias_hits += 1
        elif token in title:
            score += 10
            title_alias_query_hits += 1
        elif any(token in alias for alias in aliases):
            score += 8
            title_alias_query_hits += 1
        elif token in haystack:
            score += 3

    for token in user_tokens:
        if token in title:
            score += 4
        elif token in haystack:
            score += 1

    if doc.get("source_type") == "exact_item_card":
        if match_meta["brand_conflict"]:
            return 0, match_meta
        confidence_score = {"high": 24, "medium": 12, "low": 1, "none": -8}
        score += confidence_score.get(str(match_meta["match_confidence"]), 0)
        if match_meta["match_confidence"] == "none":
            return 0, match_meta
        if query_has_exact_item_signal:
            score += 8
    elif doc.get("source_type") == "base_nutrition":
        score += 5
        if exact_title_alias_hits:
            score += 8
        if query_has_exact_item_signal and not title_alias_query_hits:
            score -= 10
    elif doc.get("source_type") == "common_dish_prior":
        score += 8
        if exact_title_alias_hits:
            score += 12
        elif title_alias_query_hits:
            score += 6
    elif query_has_exact_item_signal and doc.get("source_type") in {"convenience_archetype", "ramen_shop_profile"}:
        score -= 4
    if doc.get("evidence_role") == "exact_truth":
        score += 6
        score += _modifier_alignment_score(query=query, user_input=user_input, doc=doc)
    if doc.get("category") in risk_flags:
        score += 3
    if doc.get("confidence") == "high":
        score += 2
    return score, match_meta


def _modifier_alignment_score(*, query: str, user_input: str, doc: dict[str, Any]) -> int:
    haystack = " ".join(
        [
            str(doc.get("title", "")),
            " ".join(str(item) for item in doc.get("aliases", []) if str(item).strip()),
        ]
    )
    score = 0
    query_text = f"{query} {user_input}"
    query_has_ice = any(token in query_text for token in ("冰", "iced", "cold"))
    query_has_hot = any(token in query_text for token in ("熱", "hot"))
    doc_has_ice = any(token in haystack for token in ("冰", "iced", "cold"))
    doc_has_hot = any(token in haystack for token in ("熱", "hot"))

    if query_has_ice and doc_has_ice:
        score += 10
    if query_has_hot and doc_has_hot:
        score += 10
    if query_has_ice and doc_has_hot and not doc_has_ice:
        score -= 12
    if query_has_hot and doc_has_ice and not doc_has_hot:
        score -= 12
    return score


def search_local_knowledge(
    query: str,
    *,
    user_input: str = "",
    risk_flags: list[str] | None = None,
    limit: int = 4,
) -> list[dict[str, Any]]:
    docs = load_retrieval_documents()
    query_tokens = _normalize_tokens(query)
    user_tokens = _normalize_tokens(user_input)
    flags = risk_flags or []

    scored: list[tuple[int, dict[str, Any]]] = []
    for doc in docs:
        score, match_meta = _score_doc(doc, query, user_input, query_tokens, user_tokens, flags)
        if score > 0:
            scored.append((score, doc | match_meta))
    scored.sort(key=lambda item: item[0], reverse=True)
    normalized_results: list[dict[str, Any]] = []
    for score, doc in scored[:limit]:
        identity_confidence = str(doc.get("match_confidence") or "none")
        if doc.get("source_type") == "common_dish_prior" and identity_confidence == "none":
            title_hits = 0
            title = str(doc.get("title", "")).lower()
            aliases = [str(item).lower() for item in doc.get("aliases", [])]
            for token in query_tokens:
                if token == title or any(token == alias for alias in aliases):
                    title_hits += 2
                elif token in title or any(token in alias for alias in aliases):
                    title_hits += 1
            if title_hits >= 2:
                identity_confidence = "medium"
            elif title_hits == 1:
                identity_confidence = "low"
        normalized_results.append(
            doc
            | {
                "score": score,
                "identity_confidence": identity_confidence,
                "provenance": {
                    "source_type": doc.get("source_type"),
                    "source_url": doc.get("source_url"),
                    "source_name": doc.get("title"),
                },
                "conflict_status": "none" if identity_confidence != "none" else "shadowed",
                "selected": False,
                "drop_reason": None,
            }
        )
    return normalized_results


def resolve_exact_item(
    query: str,
    *,
    active_brand_context: str | None = None,
    required_slots: list[str] | None = None,
    limit: int = 5,
) -> list[dict[str, Any]]:
    search_query = query.strip()
    if active_brand_context and active_brand_context not in search_query:
        search_query = f"{active_brand_context} {search_query}".strip()
    candidates = search_local_knowledge(search_query, user_input=search_query, limit=limit)
    exact_candidates = [
        item
        | {
            "tool_name": "resolve_exact_item",
            "required_slots": list(required_slots or []),
            "source_class": item.get("source_class", "exact_item_db"),
        }
        for item in candidates
        if item.get("evidence_role") == "exact_truth"
    ]
    return exact_candidates


def resolve_ingredient_anchors(
    component_list: list[str],
    *,
    portion_hints: list[str] | None = None,
    limit: int = 8,
) -> list[dict[str, Any]]:
    query = " ".join(str(item).strip() for item in component_list if str(item).strip())
    anchors = search_local_knowledge(query, user_input=query, limit=limit)
    anchor_candidates = []
    for item in anchors:
        if item.get("evidence_role") not in {"ingredient_anchor", "dish_prior"}:
            continue
        anchor_candidates.append(
            item
            | {
                "tool_name": "resolve_ingredient_anchors",
                "portion_hints": list(portion_hints or []),
                "source_class": item.get("source_class", "base_nutrition_db"),
            }
        )
    return anchor_candidates
