from __future__ import annotations

import json

from data_build.wide_research.base_nutrition_v2_2 import (
    BASE_NUTRITION_SHARDS,
    SCHEMA_VERSION,
    aggregate_run,
    render_child_prompt,
    scaffold_run,
    validate_run,
)


def test_base_nutrition_manifest_has_expected_shards() -> None:
    shard_ids = [shard["id"] for shard in BASE_NUTRITION_SHARDS]
    assert shard_ids == [
        "grains_and_rice",
        "noodles_and_pasta",
        "proteins_eggs_and_meats",
        "vegetables_roots_and_basic_produce",
        "sauces_spreads_and_oils",
        "beverages_and_liquid_basics",
    ]


def test_v2_2_prompt_mentions_canonical_row_selection() -> None:
    prompt = render_child_prompt(BASE_NUTRITION_SHARDS[0], "run")
    assert "canonical row selection" in prompt
    assert "White rice and purple rice should not both be excluded" in prompt


def test_v2_2_sauces_prompt_mentions_verified_reference_fallback() -> None:
    prompt = render_child_prompt(BASE_NUTRITION_SHARDS[4], "run")
    assert "verified_reference fallback" in prompt
    assert "official_brand_product_page" in prompt
    assert "Dongquan chili sauce" in prompt


def test_base_nutrition_scaffold_creates_layout_and_prompt_files(tmp_path) -> None:
    run_dir = scaffold_run(tmp_path, run_id="base-nutrition-v2-test", schema_signature="sig")
    assert (run_dir / "manifest.json").exists()
    assert (run_dir / "notes.json").exists()
    assert (run_dir / "prompts" / "grains_and_rice.md").exists()
    assert (run_dir / "dry_run.ps1").exists()
    assert (run_dir / "run_all.ps1").exists()


def test_base_nutrition_validate_run_catches_bad_fields(tmp_path) -> None:
    run_dir = scaffold_run(tmp_path, run_id="base-nutrition-v2-test")
    payload = {
        "schema_version": SCHEMA_VERSION,
        "shard_id": "grains_and_rice",
        "records": [
            {
                "id": "bad rice",
                "title": "Rice",
                "aliases": ["白飯"],
                "category": "rice",
                "serving_basis": {"unit_type": "plate", "amount": -1, "label": ""},
                "nutrition": {"protein_g": -1, "carb_g": 1, "fat_g": 0, "kcal": 10, "sodium_mg": None},
                "portion_equivalents": [],
                "source_type": "blog_reference",
                "source_name": "bad",
                "source_url": "https://example.com",
                "confidence": "low",
                "last_verified_at": "20260330",
                "notes": ""
            }
        ],
        "excluded_candidates": []
    }
    (run_dir / "child_outputs" / "grains_and_rice.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    report = validate_run(run_dir)
    codes = {issue["code"] for issue in report["issues"]}
    assert "bad_id" in codes
    assert "bad_unit_type" in codes
    assert "bad_source_type" in codes
    assert "bad_confidence" in codes
    assert "bad_last_verified_at" in codes
    assert "missing_output" in codes


def test_base_nutrition_aggregate_dedupes_duplicate_ids(tmp_path) -> None:
    run_dir = scaffold_run(tmp_path, run_id="base-nutrition-v2-test")
    payload_a = {
        "schema_version": SCHEMA_VERSION,
        "shard_id": "grains_and_rice",
        "records": [
            {
                "id": "white-rice",
                "title": "White Rice",
                "aliases": ["白飯"],
                "category": "rice",
                "serving_basis": {"unit_type": "g", "amount": 100, "label": "100 g"},
                "nutrition": {"protein_g": 2.6, "carb_g": 28.0, "fat_g": 0.3, "kcal": 130, "sodium_mg": 1},
                "portion_equivalents": [],
                "source_type": "government_nutrition",
                "source_name": "TFDA",
                "source_url": "https://example.gov.tw/rice",
                "confidence": "high",
                "last_verified_at": "2026-03-30",
                "notes": ""
            }
        ],
        "excluded_candidates": []
    }
    payload_b = {
        "schema_version": SCHEMA_VERSION,
        "shard_id": "noodles_and_pasta",
        "records": [
            {
                "id": "white-rice",
                "title": "White Rice Duplicate",
                "aliases": ["白飯"],
                "category": "rice",
                "serving_basis": {"unit_type": "g", "amount": 100, "label": "100 g"},
                "nutrition": {"protein_g": 2.6, "carb_g": 28.0, "fat_g": 0.3, "kcal": 130, "sodium_mg": 1},
                "portion_equivalents": [],
                "source_type": "government_nutrition",
                "source_name": "TFDA",
                "source_url": "https://example.gov.tw/rice",
                "confidence": "high",
                "last_verified_at": "2026-03-30",
                "notes": ""
            }
        ],
        "excluded_candidates": []
    }
    (run_dir / "child_outputs" / "grains_and_rice.json").write_text(json.dumps(payload_a, ensure_ascii=False, indent=2), encoding="utf-8")
    (run_dir / "child_outputs" / "noodles_and_pasta.json").write_text(json.dumps(payload_b, ensure_ascii=False, indent=2), encoding="utf-8")
    aggregated = aggregate_run(run_dir)
    assert len(aggregated["candidates"]["records"]) == 1
