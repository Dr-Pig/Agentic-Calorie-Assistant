from __future__ import annotations

import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from openpyxl import Workbook

from app.nutrition.application.food_raw_source_inventory import (
    build_food_raw_source_inventory,
    build_food_raw_source_registry,
)


def test_raw_source_registry_contains_expected_sources_and_non_claim_flags() -> None:
    registry = build_food_raw_source_registry()
    sources = {source["source_id"]: source for source in registry["sources"]}

    assert registry["artifact_type"] == "accurate_intake_food_raw_source_registry"
    assert registry["food_kb_truth_updated"] is False
    assert registry["nutrition_seed_created"] is False
    assert registry["exact_card_created"] is False
    assert registry["packet_truth_created"] is False
    assert registry["canonical_eval_promoted"] is False

    assert sources["tfda_fda_food_nutrition_2024"]["filename"] == "FDA_food_nutrition_2024.xlsx"
    assert sources["tfda_fda_food_nutrition_2024"]["source_class"] == "taiwan_tfda_open_data"
    assert sources["tfda_fda_food_nutrition_2024"]["intended_roles"] == [
        "generic_anchor",
        "listed_component_anchor",
    ]
    assert sources["tfda_tnfcds_consumer_detail"]["filename"] == "tnfcds_consumer_detail.xlsx"
    assert sources["tfda_tnfcds_consumer_items"]["filename"] == "tnfcds_consumer_items.xlsx"
    assert sources["newtaipei_brand_candidates"]["source_class"] == "official_brand_chain_page"
    assert sources["newtaipei_brand_candidates"]["intended_roles"] == ["exact_card_candidate"]
    assert sources["local_tw_packaged_extract_188_2"]["filename"] == "188_2.csv"
    assert (
        sources["local_tw_packaged_extract_188_2"]["source_class"]
        == "local_taiwan_packaged_extract"
    )
    assert sources["local_tw_packaged_extract_188_2"]["source_role"] == "staging_candidate_only"
    assert sources["local_tw_packaged_extract_188_2"]["intended_roles"] == [
        "exact_card_candidate"
    ]
    assert sources["openfoodfacts_taiwan_small"]["source_class"] == "open_food_facts"
    assert sources["usda_food_list_sample"]["source_class"] == "usda_fallback"
    assert sources["base_nutrition_db"]["intended_roles"] == ["alias_coverage_prior"]
    assert sources["tfda_base_candidates"]["source_role"] == "staging_candidate_only"
    assert sources["tfda_base_review_candidates"]["source_role"] == "staging_candidate_only"


def test_tracked_raw_source_registry_doc_has_no_local_paths() -> None:
    registry_path = Path("docs/quality/accurate_intake_food_raw_source_registry.json")
    registry_doc = json.loads(registry_path.read_text(encoding="utf-8"))
    registry_json = json.dumps(registry_doc, ensure_ascii=False)

    assert registry_doc == build_food_raw_source_registry()
    assert "C:\\Users\\User" not in registry_json
    assert "Documents/Playground" not in registry_json
    assert "local_path" not in registry_json


def test_raw_source_inventory_scans_json_without_absolute_paths(tmp_path: Path) -> None:
    source = tmp_path / "openfoodfacts_taiwan_small.json"
    source.write_text(
        json.dumps(
            {
                "records": [
                    {"code": "1", "product_name": "A", "brands": "B"},
                    {"code": "2", "product_name": "C", "nutriments": {"energy-kcal_100g": 1}},
                ]
            }
        ),
        encoding="utf-8",
    )

    inventory = build_food_raw_source_inventory(scan_roots=[tmp_path])
    entry = _entry(inventory, "openfoodfacts_taiwan_small")

    assert entry["local_path_present"] is True
    assert entry["filename"] == "openfoodfacts_taiwan_small.json"
    assert entry["source_class"] == "open_food_facts"
    assert entry["row_count"] == 2
    assert entry["schema_keys"] == ["brands", "code", "nutriments", "product_name"]
    assert entry["schema_fingerprint"]
    assert entry["relative_to_scan_root"] == "openfoodfacts_taiwan_small.json"
    assert "C:\\Users\\User" not in json.dumps(inventory)
    assert str(tmp_path) not in json.dumps(inventory)


def test_raw_source_inventory_reports_malformed_json_per_entry(tmp_path: Path) -> None:
    source = tmp_path / "openfoodfacts_taiwan_small.json"
    source.write_text("{not valid json", encoding="utf-8")

    inventory = build_food_raw_source_inventory(scan_roots=[tmp_path])
    entry = _entry(inventory, "openfoodfacts_taiwan_small")

    assert entry["local_path_present"] is True
    assert entry["parse_error"] == "JSONDecodeError"
    assert entry["row_count"] is None
    assert inventory["scan_summary"]["present_count"] == 1


def test_raw_source_inventory_scans_extracted_csv_without_absolute_paths(tmp_path: Path) -> None:
    source = tmp_path / "188_2.csv"
    source.write_text(
        "\n".join(
            [
                "company_name,product_name,package_size,serving_size,kcal_per_serving,image_url",
                "Tea Co,Brown Sugar Milk Tea,500 ml,250 ml,150,https://example.test/milk-tea.jpg",
                "Snack Co,Crispy Seaweed,36 g,18 g,95,https://example.test/seaweed.jpg",
            ]
        ),
        encoding="utf-8",
    )

    inventory = build_food_raw_source_inventory(scan_roots=[tmp_path])
    entry = _entry(inventory, "local_tw_packaged_extract_188_2")

    assert entry["local_path_present"] is True
    assert entry["filename"] == "188_2.csv"
    assert entry["extension"] == ".csv"
    assert entry["source_class"] == "local_taiwan_packaged_extract"
    assert entry["row_count"] == 2
    assert entry["schema_keys"] == [
        "company_name",
        "image_url",
        "kcal_per_serving",
        "package_size",
        "product_name",
        "serving_size",
    ]
    assert entry["schema_fingerprint"]
    assert entry["relative_to_scan_root"] == "188_2.csv"
    assert str(tmp_path) not in json.dumps(inventory, ensure_ascii=False)


def test_raw_source_inventory_scans_xlsx_without_absolute_paths(tmp_path: Path) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "nutrition"
    sheet.append(["食品名稱", "熱量", "蛋白質"])
    sheet.append(["飯糰", 250, 6])
    sheet.append(["豆漿", 120, 8])
    source = tmp_path / "FDA_food_nutrition_2024.xlsx"
    workbook.save(source)

    inventory = build_food_raw_source_inventory(scan_roots=[tmp_path])
    entry = _entry(inventory, "tfda_fda_food_nutrition_2024")

    assert entry["local_path_present"] is True
    assert entry["extension"] == ".xlsx"
    assert entry["sheet_count"] == 1
    assert entry["sheets"][0]["title"] == "nutrition"
    assert entry["sheets"][0]["max_row"] == 3
    assert entry["sheets"][0]["max_column"] == 3
    assert entry["sheets"][0]["header_row"] == ["食品名稱", "熱量", "蛋白質"]
    assert entry["row_count"] == 2
    assert entry["relative_to_scan_root"] == "FDA_food_nutrition_2024.xlsx"
    assert str(tmp_path) not in json.dumps(inventory, ensure_ascii=False)


def test_raw_source_inventory_reports_malformed_xlsx_per_entry(tmp_path: Path) -> None:
    source = tmp_path / "FDA_food_nutrition_2024.xlsx"
    source.write_bytes(b"not an xlsx workbook")

    inventory = build_food_raw_source_inventory(scan_roots=[tmp_path])
    entry = _entry(inventory, "tfda_fda_food_nutrition_2024")

    assert entry["local_path_present"] is True
    assert "parse_error" in entry
    assert entry["row_count"] is None
    assert inventory["scan_summary"]["present_count"] == 1


def test_raw_source_inventory_reports_lazy_sheet_xml_parse_error_per_entry(
    tmp_path: Path,
) -> None:
    source = tmp_path / "FDA_food_nutrition_2024.xlsx"
    _write_xlsx_with_malformed_sheet_xml(source)

    inventory = build_food_raw_source_inventory(scan_roots=[tmp_path])
    entry = _entry(inventory, "tfda_fda_food_nutrition_2024")

    assert entry["local_path_present"] is True
    assert entry["parse_error"] == "ParseError"
    assert entry["row_count"] is None
    assert inventory["scan_summary"]["present_count"] == 1
    source.unlink()
    assert not source.exists()


def test_raw_source_inventory_reports_missing_sources_as_absent(tmp_path: Path) -> None:
    inventory = build_food_raw_source_inventory(scan_roots=[tmp_path / "missing"])

    assert all(entry["local_path_present"] is False for entry in inventory["inventory_entries"])
    assert inventory["scan_summary"]["present_count"] == 0
    assert inventory["scan_summary"]["absent_count"] == len(inventory["inventory_entries"])


def test_raw_source_inventory_preserves_non_claim_flags(tmp_path: Path) -> None:
    inventory = build_food_raw_source_inventory(scan_roots=[tmp_path])

    assert inventory["food_kb_truth_updated"] is False
    assert inventory["nutrition_seed_created"] is False
    assert inventory["exact_card_created"] is False
    assert inventory["packet_truth_created"] is False
    assert inventory["canonical_eval_promoted"] is False
    assert inventory["claim_scope"] == "raw_source_inventory_only"


def test_raw_source_inventory_builder_writes_local_artifact_without_touching_fooddb_truth(
    tmp_path: Path,
) -> None:
    source = tmp_path / "base_nutrition_db.json"
    source.write_text(json.dumps([{"name": "banana", "kcal": 89}]), encoding="utf-8")
    output = tmp_path / "raw_inventory.json"
    protected_truth = [
        Path("app/knowledge/small_anchor_store_tw.json"),
        Path("app/knowledge/exact_item_cards_tw.json"),
    ]
    before = {
        path.as_posix(): path.read_bytes() if path.exists() else b""
        for path in protected_truth
    }

    from scripts.build_accurate_intake_food_raw_source_inventory import main

    assert main(["--scan-root", str(tmp_path), "--output", str(output)]) == 0

    artifact = json.loads(output.read_text(encoding="utf-8"))
    assert artifact["claim_scope"] == "raw_source_inventory_only"
    assert _entry(artifact, "base_nutrition_db")["local_path_present"] is True
    after = {
        path.as_posix(): path.read_bytes() if path.exists() else b""
        for path in protected_truth
    }
    assert after == before


def _write_xlsx_with_malformed_sheet_xml(path: Path) -> None:
    with ZipFile(path, "w", ZIP_DEFLATED) as archive:
        archive.writestr(
            "[Content_Types].xml",
            """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
</Types>""",
        )
        archive.writestr(
            "_rels/.rels",
            """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>""",
        )
        archive.writestr(
            "xl/workbook.xml",
            """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
  xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets>
    <sheet name="nutrition" sheetId="1" r:id="rId1"/>
  </sheets>
</workbook>""",
        )
        archive.writestr(
            "xl/_rels/workbook.xml.rels",
            """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
</Relationships>""",
        )
        archive.writestr("xl/worksheets/sheet1.xml", "<worksheet><sheetData><row>")


def _entry(inventory: dict[str, object], source_id: str) -> dict[str, object]:
    entries = inventory["inventory_entries"]
    assert isinstance(entries, list)
    for entry in entries:
        assert isinstance(entry, dict)
        if entry["source_id"] == source_id:
            return entry
    raise AssertionError(f"missing source entry: {source_id}")
