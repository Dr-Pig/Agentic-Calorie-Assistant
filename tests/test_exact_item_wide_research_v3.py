import json
from datetime import datetime

from data_build.wide_research import exact_item_v3


def test_manifest_contains_expected_shards():
    manifest = exact_item_v3.build_manifest("exact-item-v3-test")
    shard_ids = [shard["id"] for shard in manifest["shards"]]
    assert shard_ids == [
        "mcdonalds_tw",
        "seven_eleven_tw",
        "familymart_tw",
        "packaged_beverages_tw",
        "drink_chains_tw",
        "other_fast_food_tw",
    ]


def test_scaffold_creates_exact_item_prompt_files(tmp_path):
    run_dir = exact_item_v3.scaffold_run(tmp_path, run_id="exact-item-v3-test", schema_signature="sig-v3")
    text = (run_dir / "prompts" / "mcdonalds_tw.md").read_text(encoding="utf-8")
    assert "McDonald's Taiwan" in text
    assert "Do not merge sibling variants into one record." in text


def test_validate_child_payload_accepts_minimal_valid_record():
    payload = {
        "schema_version": exact_item_v3.SCHEMA_VERSION,
        "shard_id": "mcdonalds_tw",
        "records": [
            {
                "id": "mcdonalds-medium-fries",
                "brand": "McDonald's Taiwan",
                "title": "中份薯條",
                "aliases": ["中薯", "medium fries"],
                "category": "fast_food",
                "variant_tokens": ["medium", "fries"],
                "serving_basis": {"label": "1 serving", "unit_type": "serving", "amount": 1},
                "nutrition": {
                    "protein_g": 4,
                    "carb_g": 43,
                    "fat_g": 16,
                    "kcal": 350,
                    "sodium_mg": 200,
                    "saturated_fat_g": 2,
                    "sugars_g": 0,
                },
                "common_components": ["potato", "oil", "salt"],
                "official_serving_text": "1 serving",
                "source_type": "official_menu_nutrition_page",
                "source_name": "McDonald's Taiwan Nutrition Calculator",
                "source_url": "https://www.mcdonalds.com/tw/zh-tw/sustainability/good-food/nutrition.html",
                "confidence": "high",
                "last_verified_at": "2026-03-30",
                "notes": "Official nutrition row.",
            }
        ],
        "excluded_candidates": [],
    }
    assert exact_item_v3.validate_child_payload(payload, {"id": "mcdonalds_tw"}) == []


def test_validate_child_payload_rejects_bad_source_type():
    payload = {
        "schema_version": exact_item_v3.SCHEMA_VERSION,
        "shard_id": "mcdonalds_tw",
        "records": [
            {
                "id": "bad-item",
                "brand": "McDonald's Taiwan",
                "title": "Bad",
                "aliases": [],
                "category": "fast_food",
                "variant_tokens": [],
                "serving_basis": {"label": "1", "unit_type": "serving", "amount": 1},
                "nutrition": {
                    "protein_g": 1,
                    "carb_g": 1,
                    "fat_g": 1,
                    "kcal": 1,
                    "sodium_mg": None,
                    "saturated_fat_g": None,
                    "sugars_g": None,
                },
                "common_components": [],
                "official_serving_text": "1",
                "source_type": "forum_post",
                "source_name": "bad",
                "source_url": "https://example.com",
                "confidence": "medium",
                "last_verified_at": "2026-03-30",
                "notes": "bad",
            }
        ],
        "excluded_candidates": [],
    }
    issues = exact_item_v3.validate_child_payload(payload, {"id": "mcdonalds_tw"})
    assert any(issue.code == "bad_source_type" for issue in issues)


def test_aggregate_dedupes_records(tmp_path):
    run_dir = exact_item_v3.scaffold_run(tmp_path, run_id=exact_item_v3.make_run_id(datetime(2026, 3, 30, 12, 0, 0)))
    record = {
        "id": "mcdonalds-medium-fries",
        "brand": "McDonald's Taiwan",
        "title": "中份薯條",
        "aliases": ["中薯"],
        "category": "fast_food",
        "variant_tokens": ["medium"],
        "serving_basis": {"label": "1 serving", "unit_type": "serving", "amount": 1},
        "nutrition": {
            "protein_g": 4,
            "carb_g": 43,
            "fat_g": 16,
            "kcal": 350,
            "sodium_mg": 200,
            "saturated_fat_g": 2,
            "sugars_g": 0,
        },
        "common_components": ["potato", "oil"],
        "official_serving_text": "1 serving",
        "source_type": "official_menu_nutrition_page",
        "source_name": "McDonald's Taiwan Nutrition Calculator",
        "source_url": "https://www.mcdonalds.com/tw/zh-tw/sustainability/good-food/nutrition.html",
        "confidence": "high",
        "last_verified_at": "2026-03-30",
        "notes": "Official row.",
    }
    for shard_id in ["mcdonalds_tw", "seven_eleven_tw"]:
        out = {
            "schema_version": exact_item_v3.SCHEMA_VERSION,
            "shard_id": shard_id,
            "records": [record],
            "excluded_candidates": [],
        }
        (run_dir / "child_outputs" / f"{shard_id}.json").write_text(json.dumps(out), encoding="utf-8")
    aggregated = exact_item_v3.aggregate_run(run_dir)
    assert len(aggregated["candidates"]["records"]) == 1


def test_normalize_child_payload_lifts_misnested_fields():
    payload = {
        "schema_version": exact_item_v3.SCHEMA_VERSION,
        "shard_id": "packaged_beverages_tw",
        "records": [
            {
                "id": "pocari-sweat-580ml",
                "brand": "寶礦力水得",
                "title": "寶礦力水得 580ml",
                "aliases": ["Pocari Sweat 580ml"],
                "category": "sports_drink",
                "variant_tokens": ["580ml"],
                "serving_basis": {"label": "1 bottle", "unit_type": "bottle", "amount": 580},
                "nutrition": {
                    "protein_g": 0,
                    "carb_g": 36,
                    "fat_g": 0,
                    "kcal": 144,
                    "sodium_mg": 284,
                    "saturated_fat_g": 0,
                    "sugars_g": 34,
                    "common_components": ["water", "sugar"],
                    "official_serving_text": "per bottle",
                    "source_type": "official_retailer_product_page",
                    "source_name": "PXGo",
                    "source_url": "https://example.com/pocari",
                    "confidence": "high",
                    "last_verified_at": "2026-03-30",
                    "notes": "Lift these fields out.",
                },
            }
        ],
        "excluded_candidates": [],
    }
    normalized = exact_item_v3.normalize_child_payload(payload)
    record = normalized["records"][0]
    assert record["source_type"] == "official_retailer_product_page"
    assert record["common_components"] == ["water", "sugar"]
    assert "source_type" not in record["nutrition"]


def test_normalize_child_payload_drops_record_without_kcal():
    payload = {
        "schema_version": exact_item_v3.SCHEMA_VERSION,
        "shard_id": "packaged_beverages_tw",
        "records": [
            {
                "id": "tea-1230ml",
                "brand": "Brand",
                "title": "Tea 1230ml",
                "aliases": [],
                "category": "tea",
                "variant_tokens": ["1230ml"],
                "serving_basis": {"label": "1 bottle", "unit_type": "bottle", "amount": 1230},
                "nutrition": {
                    "protein_g": None,
                    "carb_g": None,
                    "fat_g": None,
                    "kcal": None,
                    "sodium_mg": None,
                    "saturated_fat_g": None,
                    "sugars_g": None,
                },
                "common_components": [],
                "official_serving_text": "unknown",
                "source_type": "official_chain_product_page",
                "source_name": "Brand Page",
                "source_url": "https://example.com/tea",
                "confidence": "medium",
                "last_verified_at": "2026-03-30",
                "notes": "No calorie panel.",
            }
        ],
        "excluded_candidates": [],
    }
    normalized = exact_item_v3.normalize_child_payload(payload)
    assert normalized["records"] == []
    assert len(normalized["excluded_candidates"]) == 1
