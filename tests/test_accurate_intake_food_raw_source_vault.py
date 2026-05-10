from __future__ import annotations

import json
from pathlib import Path

from openpyxl import Workbook

from app.nutrition.application.food_raw_source_vault import build_food_raw_source_vault


def test_raw_source_vault_ingests_registered_json_csv_and_xlsx_without_truth(tmp_path: Path) -> None:
    (tmp_path / "openfoodfacts_taiwan_small.json").write_text(
        json.dumps(
            {
                "products": [
                    {
                        "code": "471001",
                        "product_name": "Oat Drink",
                        "nutriments": {"energy-kcal_100g": 45},
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (tmp_path / "188_2.csv").write_text(
        "\n".join(
            [
                "company_name,product_name,kcal_per_serving,serving_size",
                "Tea Co,Brown Sugar Milk Tea,150,250 ml",
            ]
        ),
        encoding="utf-8",
    )
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["category", "label", "aliases", "kcal", "corrected_kcal"])
    sheet.append(["drink", "Soy Milk", "soy beverage", 55, 54])
    workbook.save(tmp_path / "FDA_food_nutrition_2024.xlsx")

    vault = build_food_raw_source_vault(scan_roots=[tmp_path])

    assert vault["artifact_type"] == "accurate_intake_food_raw_source_vault"
    assert vault["claim_scope"] == "raw_source_vault_only"
    assert vault["runtime_truth"] is False
    assert vault["food_kb_truth_updated"] is False
    assert vault["packet_truth_created"] is False
    assert vault["pipeline_stage_boundary"]["implemented_stage"] == "raw_source_vault"
    assert vault["vault_summary"]["present_source_count"] == 3
    assert vault["vault_summary"]["raw_record_count"] == 3

    serialized = json.dumps(vault, ensure_ascii=False)
    assert str(tmp_path) not in serialized
    assert "candidate_id" not in serialized

    records = vault["raw_records"]
    assert "packet_ready" not in json.dumps(records, ensure_ascii=False)
    by_source = {record["source_id"]: record for record in records}
    off_record = by_source["openfoodfacts_taiwan_small"]
    assert off_record["candidate_role"] == "user_contributed_packaged_candidate"
    assert off_record["runtime_truth_allowed_default"] is False
    assert off_record["macro_truth_allowed_default"] is False
    assert off_record["raw_record_hash"]
    assert off_record["record_id"] == "471001"
    assert off_record["raw_record"]["product_name"] == "Oat Drink"

    csv_record = by_source["local_tw_packaged_extract_188_2"]
    assert csv_record["record_id"] is None
    assert csv_record["raw_record"]["product_name"] == "Brown Sugar Milk Tea"

    tfda_record = by_source["tfda_fda_food_nutrition_2024"]
    assert tfda_record["record_kind"] == "raw_source_row"
    assert tfda_record["raw_record"]["label"] == "Soy Milk"
    assert tfda_record["source_class"] == "taiwan_tfda_open_data"


def test_raw_source_vault_builder_writes_local_artifact_without_touching_truth(
    tmp_path: Path,
) -> None:
    (tmp_path / "openfoodfacts_taiwan_small.json").write_text(
        json.dumps({"records": [{"code": "1", "product_name": "A"}]}),
        encoding="utf-8",
    )
    output = tmp_path / "raw_vault.json"
    protected_truth = [
        Path("app/knowledge/small_anchor_store_tw.json"),
        Path("app/knowledge/exact_item_cards_tw.json"),
        Path("app/knowledge/tfda_per100g_source_evidence_tw.json"),
    ]
    before = {
        path.as_posix(): path.read_bytes() if path.exists() else b""
        for path in protected_truth
    }

    from scripts.build_accurate_intake_food_raw_source_vault import main

    assert main(["--scan-root", str(tmp_path), "--output", str(output)]) == 0

    artifact = json.loads(output.read_text(encoding="utf-8"))
    assert artifact["claim_scope"] == "raw_source_vault_only"
    assert artifact["vault_summary"]["raw_record_count"] == 1
    assert artifact["raw_records"][0]["runtime_truth_allowed_default"] is False
    after = {
        path.as_posix(): path.read_bytes() if path.exists() else b""
        for path in protected_truth
    }
    assert after == before
