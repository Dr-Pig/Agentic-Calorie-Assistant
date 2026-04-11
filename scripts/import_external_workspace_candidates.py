from __future__ import annotations

import argparse
import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
APP_KNOWLEDGE = ROOT / "app" / "knowledge"

EXACT_TARGET_FILES = {
    "burgerking_candidates.json",
    "city_cafe_candidates.json",
    "kfc_candidates.json",
    "mcdonalds_candidates.json",
    "mos_candidates.json",
    "newtaipei_brand_candidates.json",
    "pizzahut_candidates.json",
    "starbucks_candidates.json",
    "subway_candidates.json",
}
BASE_TARGET_FILES = {
    "tfda_base_candidates.json",
}
EXTRA_EXACT_SOURCE_FILES = {
    "starbucks_food_extracted.json",
}
MOJIBAKE_CHARS = set("?暻瘥蝢憭銝撌拇寥寞")
CARD_CATEGORIES = {
    "burger": "fast_food",
    "fast_food": "fast_food",
    "breakfast": "breakfast_chain",
    "dessert": "dessert",
    "beverage": "drink_chain",
    "drink": "drink_chain",
    "coffee": "drink_chain",
}
BRAND_ALIAS_MAP = {
    "全家便利商店股份有限公司": ["全家", "FamilyMart", "FamiMart"],
    "臺灣菸酒股份有限公司": ["台酒", "臺酒", "TTL"],
    "Starbucks": ["星巴克"],
}


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _slugify(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "-", text)
    text = re.sub(r"-{2,}", "-", text)
    return text.strip("-") or "unknown"


def _looks_mojibake(text: str) -> bool:
    text = str(text or "").strip()
    if not text:
        return True
    cjk_chars = sum(1 for ch in text if "\u4e00" <= ch <= "\u9fff")
    ascii_letters = sum(1 for ch in text if ("a" <= ch.lower() <= "z"))
    suspicious = sum(1 for ch in text if ch in MOJIBAKE_CHARS)
    pua_chars = sum(1 for ch in text if "\ue000" <= ch <= "\uf8ff")
    question_marks = text.count("?")
    if cjk_chars >= 2:
        return pua_chars > 0 or question_marks >= 2
    if ascii_letters >= 4 and suspicious == 0:
        return pua_chars > 0 or question_marks >= 2
    if pua_chars > 0:
        return True
    if question_marks >= 2:
        return True
    return suspicious >= max(1, len(text) // 8)


def _safe_text(text: Any) -> str:
    return str(text or "").strip()


def _brand_aliases(brand: str) -> list[str]:
    normalized = _safe_text(brand)
    if not normalized:
        return []
    aliases = [normalized]
    for alias in BRAND_ALIAS_MAP.get(normalized, []):
        cleaned = _safe_text(alias)
        if cleaned and cleaned not in aliases:
            aliases.append(cleaned)
    return aliases


def _title_aliases(title: str) -> list[str]:
    cleaned = _safe_text(title)
    if not cleaned:
        return []
    aliases = [cleaned]
    stripped_prefix = re.sub(r"^[0-9a-zA-Z.*xX公升毫升MLmlL升罐盒瓶包入裝*×()/-]+", "", cleaned).strip(" -_")
    if stripped_prefix and stripped_prefix not in aliases:
        aliases.append(stripped_prefix)
    no_pack_prefix = re.sub(r"^(?:\d+(?:\.\d+)?(?:公升|毫升|ml|ML|L|升)[*xX×]?\d*(?:罐裝|罐|盒裝|盒|瓶裝|瓶|包裝|包)?)+", "", cleaned).strip(" -_")
    if no_pack_prefix and no_pack_prefix not in aliases:
        aliases.append(no_pack_prefix)
    normalized_dash = cleaned.replace("-", " ").strip()
    if normalized_dash and normalized_dash not in aliases:
        aliases.append(normalized_dash)
    return aliases


def _build_aliases(title: str, variant: str, brand: str) -> list[str]:
    aliases: list[str] = []
    title_variants = _title_aliases(title)
    brand_variants = _brand_aliases(brand)
    variant_clean = _safe_text(variant)
    for item in title_variants:
        if item and item not in aliases:
            aliases.append(item)
    for brand_variant in brand_variants:
        if brand_variant and brand_variant not in aliases:
            aliases.append(brand_variant)
        for title_variant in title_variants:
            combined = f"{brand_variant} {title_variant}".strip()
            if combined and combined not in aliases:
                aliases.append(combined)
            if variant_clean:
                combined_with_variant = f"{brand_variant} {title_variant} {variant_clean}".strip()
                if combined_with_variant and combined_with_variant not in aliases:
                    aliases.append(combined_with_variant)
    if variant_clean:
        for title_variant in title_variants:
            combined = f"{title_variant} {variant_clean}".strip()
            if combined and combined not in aliases:
                aliases.append(combined)
    return aliases


def _normalize_card_category(raw_category: str) -> str:
    value = _safe_text(raw_category).lower()
    for key, normalized in CARD_CATEGORIES.items():
        if key in value:
            return normalized
    return "chain_menu"


def _map_exact_record(record: dict[str, Any]) -> dict[str, Any] | None:
    brand = _safe_text(record.get("brand"))
    title = _safe_text(record.get("title"))
    variant = _safe_text(record.get("variant"))
    if _looks_mojibake(title) or _looks_mojibake(brand):
        return None
    display_title = title if not variant else f"{title} {variant}".strip()
    kcal = record.get("kcal")
    if not isinstance(kcal, (int, float)) or kcal <= 0:
        return None
    source_url = _safe_text(record.get("source_url"))
    source_type = _safe_text(record.get("source_type")) or "curated_reference"
    confidence = _safe_text(record.get("confidence")) or "medium"
    return {
        "card_id": _slugify(f"{brand}-{display_title}"),
        "source_type": "exact_item_card",
        "brand": brand,
        "title": display_title,
        "aliases": _build_aliases(title=title, variant=variant, brand=brand),
        "category": _normalize_card_category(_safe_text(record.get("category"))),
        "common_components": [],
        "portion_notes": _safe_text((record.get("serving_basis") or {}).get("label")) or "Imported from external workspace candidate.",
        "kcal_band": f"{int(round(float(kcal)))} kcal",
        "must_ask_if_uncertain": [],
        "confidence": "high" if confidence == "high" else "medium",
        "source_note": f"Imported from external workspace ({source_type})",
        "source_url": source_url or None,
        "evidence_role": "exact_truth",
        "record_role": "external_exact_candidate",
        "macro_completeness": "kcal_only",
        "estimate_eligibility": "exact",
        "portion_basis_quality": "medium",
    }


def _map_base_record(record: dict[str, Any]) -> dict[str, Any] | None:
    title = _safe_text(record.get("title"))
    brand = _safe_text(record.get("brand"))
    if _looks_mojibake(title) or _looks_mojibake(brand):
        return None
    protein_g = record.get("protein_g")
    carb_g = record.get("carb_g")
    fat_g = record.get("fat_g")
    if not all(isinstance(value, (int, float)) for value in [protein_g, carb_g, fat_g]):
        return None
    kcal = record.get("kcal")
    if not isinstance(kcal, (int, float)) or kcal <= 0:
        return None
    serving_basis = record.get("serving_basis") or {}
    amount = serving_basis.get("amount") if isinstance(serving_basis.get("amount"), (int, float)) else 1
    unit_type = _safe_text(serving_basis.get("unit_type")) or "serving"
    label = _safe_text(serving_basis.get("label")) or "1 serving"
    return {
        "id": _slugify(f"{brand}-{title}"),
        "title": title,
        "aliases": [item for item in [title, brand] if item],
        "category": _safe_text(record.get("category")) or "external_dataset",
        "serving_basis": {
            "unit_type": unit_type,
            "amount": amount,
            "label": label,
        },
        "nutrition": {
            "protein_g": float(protein_g),
            "carb_g": float(carb_g),
            "fat_g": float(fat_g),
            "kcal": float(kcal),
            "sodium_mg": None,
        },
        "portion_equivalents": [],
        "source_type": "verified_reference",
        "source_name": _safe_text(record.get("source_name")) or "External workspace import",
        "source_url": _safe_text(record.get("source_url")),
        "confidence": _safe_text(record.get("confidence")) or "medium",
        "last_verified_at": None,
        "notes": "Imported from external workspace staging candidate.",
    }


def _merge_unique(items: list[dict[str, Any]], new_items: list[dict[str, Any]], *, key: str) -> tuple[list[dict[str, Any]], int]:
    merged = deepcopy(items)
    index = {str(item.get(key)): idx for idx, item in enumerate(merged)}
    inserted = 0
    for item in new_items:
        item_key = str(item.get(key))
        if item_key in index:
            merged[index[item_key]] = item
        else:
            merged.append(item)
            index[item_key] = len(merged) - 1
            inserted += 1
    return merged, inserted


def import_workspace(workspace: Path, *, write: bool) -> dict[str, Any]:
    staging_dir = workspace / "raw_data" / "staging"
    validation_path = staging_dir / "staging_validation_report.json"
    validation = _load_json(validation_path)

    exact_payload = _load_json(APP_KNOWLEDGE / "exact_item_cards_tw.json")
    base_payload = _load_json(APP_KNOWLEDGE / "base_nutrition_db.json")

    exact_new: list[dict[str, Any]] = []
    base_new: list[dict[str, Any]] = []
    file_reports: list[dict[str, Any]] = []

    processed_files: set[str] = set()
    for file_info in validation.get("files", []):
        name = str(file_info.get("file") or "")
        processed_files.add(name)
        if not file_info.get("ready_for_review"):
            file_reports.append({"file": name, "status": "skipped_not_ready"})
            continue
        if name not in EXACT_TARGET_FILES and name not in BASE_TARGET_FILES:
            file_reports.append({"file": name, "status": "skipped_out_of_scope"})
            continue
        path = staging_dir / name
        if not path.exists():
            file_reports.append({"file": name, "status": "missing"})
            continue
        payload = _load_json(path)
        records = payload.get("records") or []
        imported = 0
        rejected = 0
        for record in records:
            mapped = _map_exact_record(record) if name in EXACT_TARGET_FILES else _map_base_record(record)
            if mapped is None:
                rejected += 1
                continue
            if name in EXACT_TARGET_FILES:
                exact_new.append(mapped)
            else:
                base_new.append(mapped)
            imported += 1
        file_reports.append(
            {
                "file": name,
                "status": "processed",
                "records_seen": len(records),
                "records_importable": imported,
                "records_rejected": rejected,
            }
        )

    for name in sorted(EXTRA_EXACT_SOURCE_FILES):
        if name in processed_files:
            continue
        path = staging_dir / name
        if not path.exists():
            file_reports.append({"file": name, "status": "missing_extra_source"})
            continue
        payload = _load_json(path)
        records = payload.get("records") or []
        imported = 0
        rejected = 0
        for record in records:
            mapped = _map_exact_record(record)
            if mapped is None:
                rejected += 1
                continue
            exact_new.append(mapped)
            imported += 1
        file_reports.append(
            {
                "file": name,
                "status": "processed_extra_source",
                "records_seen": len(records),
                "records_importable": imported,
                "records_rejected": rejected,
            }
        )

    merged_exact, exact_inserted = _merge_unique(exact_payload.get("cards", []), exact_new, key="card_id")
    merged_base, base_inserted = _merge_unique(base_payload.get("records", []), base_new, key="id")

    if write:
        exact_payload["cards"] = merged_exact
        base_payload["records"] = merged_base
        (APP_KNOWLEDGE / "exact_item_cards_tw.json").write_text(
            json.dumps(exact_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        (APP_KNOWLEDGE / "base_nutrition_db.json").write_text(
            json.dumps(base_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    return {
        "workspace": str(workspace),
        "write": write,
        "exact_candidates_seen": len(exact_new),
        "base_candidates_seen": len(base_new),
        "exact_inserted_or_updated": exact_inserted,
        "base_inserted_or_updated": base_inserted,
        "final_exact_count": len(merged_exact),
        "final_base_count": len(merged_base),
        "files": file_reports,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Import external staging candidates into app/knowledge with mojibake filtering.")
    parser.add_argument("--workspace", required=True, help="Path to the external workspace root.")
    parser.add_argument("--report-out", help="Optional path to save an import report JSON.")
    parser.add_argument("--write", action="store_true", help="Write merged results back into app/knowledge.")
    args = parser.parse_args()

    report = import_workspace(Path(args.workspace).resolve(), write=args.write)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if args.report_out:
        out = Path(args.report_out).resolve()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
