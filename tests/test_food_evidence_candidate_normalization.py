from __future__ import annotations

import json
from pathlib import Path

from openpyxl import Workbook

from app.nutrition.application.food_evidence_candidate_normalization import (
    build_food_evidence_candidate_artifact,
)


def test_candidate_normalization_maps_staging_json_without_truth_promotion(
    tmp_path: Path,
) -> None:
    source = tmp_path / "tfda_base_review_candidates.json"
    source.write_text(
        json.dumps(
            {
                "records": [
                    {
                        "id": "tfda_00001",
                        "brand": "小薏仁",
                        "title": "大麥仁",
                        "variant": "",
                        "category": "主食/穀物",
                        "serving_basis": {"label": "每100g", "unit_type": "g", "amount": 100},
                        "kcal": 346.7,
                        "source_url": "https://data.gov.tw/dataset/8543",
                        "source_file": "FDA_food_nutrition_2024.xlsx",
                        "confidence": "high",
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    artifact = build_food_evidence_candidate_artifact(scan_roots=[tmp_path])

    assert artifact["claim_scope"] == "food_evidence_candidate_normalization_only"
    assert artifact["food_kb_truth_updated"] is False
    assert artifact["nutrition_seed_created"] is False
    assert artifact["exact_card_created"] is False
    assert artifact["packet_truth_created"] is False
    assert artifact["candidate_summary"]["candidate_count"] == 1
    candidate = artifact["candidates"][0]
    assert candidate["candidate_id"].startswith("cand_tfda_base_review_candidates_")
    assert candidate["source_id"] == "tfda_base_review_candidates"
    assert candidate["source_class"] == "taiwan_tfda_open_data"
    assert candidate["promotion_status"] == "candidate"
    assert candidate["runtime_truth_allowed"] is False
    assert candidate["evidence_role"] == "generic_anchor_candidate"
    assert candidate["canonical_label"] == "大麥仁"
    assert candidate["aliases"] == ["小薏仁"]
    assert candidate["kcal_point"] == 346.7
    assert candidate["serving_basis"]["amount"] == 100
    assert "C:\\Users\\User" not in json.dumps(artifact, ensure_ascii=False)
    assert str(tmp_path) not in json.dumps(artifact, ensure_ascii=False)


def test_candidate_normalization_maps_tfda_xlsx_rows(tmp_path: Path) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "nutrition"
    sheet.append(["本資料庫所列數值單位均為每100 g可食部分之含量。"])
    sheet.append(["食品分類", "樣品名稱", "俗名", "熱量(kcal)", "修正熱量(kcal)"])
    sheet.append(["穀物類", "大麥仁", "小薏仁,洋薏仁", 364.6, 346.7])
    source = tmp_path / "FDA_food_nutrition_2024.xlsx"
    workbook.save(source)

    artifact = build_food_evidence_candidate_artifact(scan_roots=[tmp_path])

    assert artifact["candidate_summary"]["candidate_count"] == 1
    candidate = artifact["candidates"][0]
    assert candidate["source_id"] == "tfda_fda_food_nutrition_2024"
    assert candidate["canonical_label"] == "大麥仁"
    assert candidate["aliases"] == ["小薏仁", "洋薏仁"]
    assert candidate["kcal_point"] == 346.7
    assert candidate["serving_basis"] == {
        "unit_type": "g",
        "amount": 100,
        "label": "per_100g_edible_portion",
    }
    assert candidate["source_provenance"]["row_index"] == 3
    assert candidate["source_provenance"]["source_file"] == "FDA_food_nutrition_2024.xlsx"


def test_candidate_normalization_applies_listed_component_policy_to_tfda_xlsx_rows(
    tmp_path: Path,
) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "nutrition"
    sheet.append(["食品營養成分資料庫(每100 g可食部分)"])
    sheet.append(["樣品類別", "食品名稱", "俗名", "熱量(kcal)", "修正熱量(kcal)"])
    sheet.append(["豆類", "豆干", "滷味豆干", 170, 160])
    sheet.append(["魚類", "高麗馬加鰆", "", 120, 118])
    source = tmp_path / "FDA_food_nutrition_2024.xlsx"
    workbook.save(source)

    artifact = build_food_evidence_candidate_artifact(scan_roots=[tmp_path])
    by_label = {candidate["canonical_label"]: candidate for candidate in artifact["candidates"]}

    assert by_label["豆干"]["evidence_role"] == "listed_component_anchor_candidate"
    assert by_label["高麗馬加鰆"]["evidence_role"] == "generic_anchor_candidate"


def test_candidate_normalization_infers_listed_component_role_for_tfda_labels(
    tmp_path: Path,
) -> None:
    source = tmp_path / "tfda_base_review_candidates.json"
    source.write_text(
        json.dumps(
            {
                "records": [
                    {"id": "dougan", "title": "豆干", "kcal": 160},
                    {"id": "haidai", "title": "海帶", "kcal": 28},
                    {"id": "gongwan", "title": "貢丸", "kcal": 210},
                    {"id": "gaolicai", "title": "高麗菜", "kcal": 23},
                    {"id": "sijidou", "title": "四季豆", "kcal": 31},
                    {"id": "bubble-tea", "title": "珍珠奶茶", "kcal": 190},
                    {"id": "danbing", "title": "蛋餅", "kcal": 280},
                    {"id": "fish", "title": "高麗馬加鰆", "kcal": 118},
                    {"id": "drink", "title": "維生素強化飲料(胡蘿蔔素)", "kcal": 39},
                    {"id": "cake", "title": "冷藏廣式蘿蔔糕", "kcal": 109},
                    {"id": "egg", "title": "蒸蛋(市售)", "kcal": 31},
                    {"id": "dried-cabbage", "title": "甘藍乾", "kcal": 188},
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    artifact = build_food_evidence_candidate_artifact(scan_roots=[tmp_path])
    by_label = {candidate["canonical_label"]: candidate for candidate in artifact["candidates"]}

    assert by_label["豆干"]["evidence_role"] == "listed_component_anchor_candidate"
    assert by_label["海帶"]["evidence_role"] == "listed_component_anchor_candidate"
    assert by_label["貢丸"]["evidence_role"] == "listed_component_anchor_candidate"
    assert by_label["高麗菜"]["evidence_role"] == "listed_component_anchor_candidate"
    assert by_label["四季豆"]["evidence_role"] == "listed_component_anchor_candidate"
    assert by_label["珍珠奶茶"]["evidence_role"] == "generic_anchor_candidate"
    assert by_label["蛋餅"]["evidence_role"] == "generic_anchor_candidate"
    assert by_label["高麗馬加鰆"]["evidence_role"] == "generic_anchor_candidate"
    assert by_label["維生素強化飲料(胡蘿蔔素)"]["evidence_role"] == "generic_anchor_candidate"
    assert by_label["冷藏廣式蘿蔔糕"]["evidence_role"] == "generic_anchor_candidate"
    assert by_label["蒸蛋(市售)"]["evidence_role"] == "generic_anchor_candidate"
    assert by_label["甘藍乾"]["evidence_role"] == "generic_anchor_candidate"
    assert all(candidate["runtime_truth_allowed"] is False for candidate in by_label.values())


def test_candidate_normalization_maps_off_and_usda_samples(tmp_path: Path) -> None:
    off = tmp_path / "openfoodfacts_taiwan_small.json"
    off.write_text(
        json.dumps(
            {
                "records": [
                    {
                        "code": "471000000001",
                        "product_name": "台灣包裝豆漿",
                        "brands": "示範品牌",
                        "nutriments": {"energy-kcal_100g": 55},
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    usda = tmp_path / "usda_food_list_sample.json"
    usda.write_text(
        json.dumps(
            [
                {
                    "fdcId": 123,
                    "description": "Soy milk, plain",
                    "dataType": "Foundation",
                    "foodNutrients": [
                        {"nutrientName": "Energy", "unitName": "KCAL", "value": 54}
                    ],
                }
            ]
        ),
        encoding="utf-8",
    )

    artifact = build_food_evidence_candidate_artifact(scan_roots=[tmp_path])
    by_source = {candidate["source_id"]: candidate for candidate in artifact["candidates"]}

    assert by_source["openfoodfacts_taiwan_small"]["evidence_role"] == "packaged_candidate"
    assert by_source["openfoodfacts_taiwan_small"]["canonical_label"] == "台灣包裝豆漿"
    assert by_source["openfoodfacts_taiwan_small"]["brand"] == "示範品牌"
    assert by_source["openfoodfacts_taiwan_small"]["kcal_point"] == 55
    assert by_source["usda_food_list_sample"]["evidence_role"] == "fallback_anchor_candidate"
    assert by_source["usda_food_list_sample"]["canonical_label"] == "Soy milk, plain"
    assert by_source["usda_food_list_sample"]["kcal_point"] == 54


def test_candidate_normalization_maps_local_extracted_csv_packaged_rows(tmp_path: Path) -> None:
    source = tmp_path / "188_2.csv"
    source.write_text(
        "\n".join(
            [
                "company_name,product_name,package_size,serving_size,kcal_per_serving,kcal_per_100g,kcal_per_100ml,image_url",
                "Tea Co,Brown Sugar Milk Tea,500 ml,250 ml,150,,60,https://example.test/milk-tea.jpg",
                "Snack Co,Crispy Seaweed,36 g,18 g,,520,,https://example.test/seaweed.jpg",
                "Juice Co,Lemon Juice,900 ml,,,,44,https://example.test/lemon-juice.jpg",
            ]
        ),
        encoding="utf-8",
    )

    artifact = build_food_evidence_candidate_artifact(scan_roots=[tmp_path])
    by_label = {candidate["canonical_label"]: candidate for candidate in artifact["candidates"]}

    milk_tea = by_label["Brown Sugar Milk Tea"]
    assert milk_tea["source_id"] == "local_tw_packaged_extract_188_2"
    assert milk_tea["source_class"] == "local_taiwan_packaged_extract"
    assert milk_tea["evidence_role"] == "exact_card_candidate"
    assert milk_tea["brand"] == "Tea Co"
    assert milk_tea["serving_basis"] == {
        "unit_type": "ml",
        "amount": 250,
        "label": "per_serving",
    }
    assert milk_tea["kcal_point"] == 150
    assert milk_tea["runtime_truth_allowed"] is False
    assert milk_tea["source_provenance"]["package_size"] == "500 ml"
    assert milk_tea["source_provenance"]["nutrition_basis"] == "per_serving"
    assert milk_tea["source_provenance"]["image_urls"] == ["https://example.test/milk-tea.jpg"]
    assert milk_tea["source_provenance"]["basis_candidates"] == {
        "per_serving": 150.0,
        "per_100ml": 60.0,
    }

    seaweed = by_label["Crispy Seaweed"]
    assert seaweed["serving_basis"] == {
        "unit_type": "g",
        "amount": 100,
        "label": "per_100g",
    }
    assert seaweed["kcal_point"] == 520
    assert seaweed["source_provenance"]["nutrition_basis"] == "per_100g"

    lemon_juice = by_label["Lemon Juice"]
    assert lemon_juice["serving_basis"] == {
        "unit_type": "ml",
        "amount": 100,
        "label": "per_100ml",
    }
    assert lemon_juice["kcal_point"] == 44
    assert lemon_juice["source_provenance"]["nutrition_basis"] == "per_100ml"
    assert all(candidate["runtime_truth_allowed"] is False for candidate in by_label.values())


def test_candidate_normalization_prefers_explicit_normalized_basis_when_serving_size_is_missing(
    tmp_path: Path,
) -> None:
    source = tmp_path / "188_2.csv"
    source.write_text(
        "\n".join(
            [
                "公司名稱,產品名稱,包裝規格,每一份量,每份熱量,每100公克熱量,每100毫升熱量,正面外包裝照片",
                "Tea Co,Brown Sugar Milk Tea,500 ml,,150,60,,https://example.test/milk-tea.jpg",
                "Tea Co,Lemon Juice,900 ml,,120,,44,https://example.test/lemon-juice.jpg",
            ]
        ),
        encoding="utf-8",
    )

    artifact = build_food_evidence_candidate_artifact(scan_roots=[tmp_path])
    by_label = {candidate["canonical_label"]: candidate for candidate in artifact["candidates"]}

    milk_tea = by_label["Brown Sugar Milk Tea"]
    assert milk_tea["serving_basis"] == {
        "unit_type": "g",
        "amount": 100,
        "label": "per_100g",
    }
    assert milk_tea["kcal_point"] == 60
    assert milk_tea["source_provenance"]["nutrition_basis"] == "per_100g"

    lemon_juice = by_label["Lemon Juice"]
    assert lemon_juice["serving_basis"] == {
        "unit_type": "ml",
        "amount": 100,
        "label": "per_100ml",
    }
    assert lemon_juice["kcal_point"] == 44
    assert lemon_juice["source_provenance"]["nutrition_basis"] == "per_100ml"


def test_candidate_normalization_reports_parse_errors_and_rejections(
    tmp_path: Path,
) -> None:
    (tmp_path / "openfoodfacts_taiwan_small.json").write_text(
        "<!DOCTYPE html><html>blocked</html>",
        encoding="utf-8",
    )
    (tmp_path / "base_nutrition_db.json").write_text(
        json.dumps([{"title": "no kcal"}]),
        encoding="utf-8",
    )

    artifact = build_food_evidence_candidate_artifact(scan_roots=[tmp_path])
    source_reports = {report["source_id"]: report for report in artifact["source_reports"]}

    assert source_reports["openfoodfacts_taiwan_small"]["parse_error"] == "JSONDecodeError"
    assert source_reports["base_nutrition_db"]["rejected_count"] == 1
    assert artifact["candidate_summary"]["rejected_count"] == 1
    assert artifact["candidate_summary"]["parse_error_count"] == 1
    rejection = artifact["rejections"][0]
    assert rejection["source_id"] == "base_nutrition_db"
    assert "missing_kcal" in rejection["reasons"]
    assert artifact["candidates"] == []


def test_candidate_builder_preserves_fooddb_truth_files(tmp_path: Path) -> None:
    (tmp_path / "base_nutrition_db.json").write_text(
        json.dumps(
            [
                {
                    "id": "white-rice",
                    "title": "白飯",
                    "aliases": ["白米飯"],
                    "serving_basis": {"unit_type": "g", "amount": 100, "label": "100g"},
                    "nutrition": {"kcal": 183},
                    "source_url": "https://consumer.fda.gov.tw/Food/TFND.aspx",
                }
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    protected_truth = [
        Path("app/knowledge/small_anchor_store_tw.json"),
        Path("app/knowledge/exact_item_cards_tw.json"),
    ]
    before = {path.as_posix(): path.read_bytes() for path in protected_truth}

    artifact = build_food_evidence_candidate_artifact(scan_roots=[tmp_path])

    after = {path.as_posix(): path.read_bytes() for path in protected_truth}
    assert after == before
    assert artifact["candidate_summary"]["candidate_count"] == 1
    assert artifact["food_kb_truth_updated"] is False
    assert artifact["runtime_truth_changed"] is False


def test_candidate_builder_cli_writes_roundtrippable_artifact(tmp_path: Path) -> None:
    (tmp_path / "usda_food_list_sample.json").write_text(
        json.dumps(
            [
                {
                    "fdcId": 456,
                    "description": "Tea egg",
                    "foodNutrients": [
                        {"nutrientName": "Energy", "unitName": "KCAL", "value": 150}
                    ],
                }
            ]
        ),
        encoding="utf-8",
    )
    output = tmp_path / "candidates.json"

    from app.shared.infra.json_artifacts import read_json_artifact
    from scripts.build_accurate_intake_food_evidence_candidates import main

    assert main(["--scan-root", str(tmp_path), "--output", str(output)]) == 0
    artifact = read_json_artifact(output)

    assert artifact["claim_scope"] == "food_evidence_candidate_normalization_only"
    assert artifact["candidate_summary"]["candidate_count"] == 1
    assert artifact["candidates"][0]["canonical_label"] == "Tea egg"
