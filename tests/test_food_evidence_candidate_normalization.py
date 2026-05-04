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
