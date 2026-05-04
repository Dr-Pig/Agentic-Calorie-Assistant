from __future__ import annotations

import json
from pathlib import Path

from app.nutrition.application.food_evidence_candidate_validation import (
    build_food_evidence_candidate_validation_artifact,
)


def _candidate(
    candidate_id: str,
    label: str,
    *,
    source_id: str = "tfda_base_review_candidates",
    source_class: str = "taiwan_tfda_open_data",
    evidence_role: str = "generic_anchor_candidate",
    kcal: float = 250,
    aliases: list[str] | None = None,
    source_file: str = "tfda_base_review_candidates.json",
) -> dict:
    return {
        "candidate_id": candidate_id,
        "source_id": source_id,
        "source_class": source_class,
        "source_role": "staging_candidate_only",
        "evidence_role": evidence_role,
        "promotion_status": "candidate",
        "runtime_truth_allowed": False,
        "canonical_label": label,
        "aliases": aliases or [],
        "brand": None,
        "category": "test",
        "serving_basis": {"unit_type": "g", "amount": 100, "label": "per_100g"},
        "kcal_point": kcal,
        "kcal_range": None,
        "source_provenance": {
            "source_id": source_id,
            "source_file": source_file,
            "row_index": 1,
            "record_id": candidate_id,
            "source_url": "https://example.test/source",
            "raw_row_hash": "hash",
        },
        "quality_flags": [],
    }


def _candidate_artifact(candidates: list[dict], *, reports: list[dict] | None = None) -> dict:
    return {
        "artifact_schema_version": "1.0",
        "artifact_type": "accurate_intake_food_evidence_candidates",
        "claim_scope": "food_evidence_candidate_normalization_only",
        "food_kb_truth_updated": False,
        "nutrition_seed_created": False,
        "exact_card_created": False,
        "packet_truth_created": False,
        "canonical_eval_promoted": False,
        "runtime_truth_changed": False,
        "candidate_summary": {
            "candidate_count": len(candidates),
            "rejected_count": 0,
            "parse_error_count": 0,
        },
        "source_reports": reports or [],
        "candidates": candidates,
        "rejections": [],
    }


def _gap_register() -> dict:
    return {
        "artifact_type": "accurate_intake_food_kb_gap_register",
        "food_gap_candidates": [
            {
                "candidate_id": "food_gap_breakfast_001",
                "gap_family": "breakfast_combo",
                "status": "review_candidate",
                "promotion_allowed": False,
            },
            {
                "candidate_id": "food_gap_lunch_001",
                "gap_family": "chicken_bento_rice_modifier",
                "status": "review_candidate",
                "promotion_allowed": False,
            },
            {
                "candidate_id": "food_gap_tea_001",
                "gap_family": "bubble_tea_sugar_size_modifier",
                "status": "review_candidate",
                "promotion_allowed": False,
            },
            {
                "candidate_id": "food_gap_dinner_basket_001",
                "gap_family": "luwei_listed_components",
                "status": "review_candidate",
                "promotion_allowed": False,
            },
        ],
    }


def test_validator_passes_schema_provenance_unit_kcal_and_source_class() -> None:
    artifact = build_food_evidence_candidate_validation_artifact(
        candidate_artifact=_candidate_artifact(
            [_candidate("c1", "\u86cb\u9905", aliases=["danbing"])]
        ),
        gap_register=None,
    )

    assert artifact["claim_scope"] == "food_evidence_candidate_validation_only"
    assert artifact["food_kb_truth_updated"] is False
    assert artifact["packet_truth_created"] is False
    assert artifact["runtime_truth_changed"] is False
    assert artifact["summary"]["validator_passed_count"] == 1
    result = artifact["validated_candidates"][0]
    assert result["validation_status"] == "validator_passed"
    assert result["candidate_id"] == "c1"
    assert result["runtime_truth_allowed"] is False
    assert result["packet_ready"] is False


def test_validator_accepts_tfda_listed_component_candidate_without_truth_promotion() -> None:
    artifact = build_food_evidence_candidate_validation_artifact(
        candidate_artifact=_candidate_artifact(
            [
                _candidate(
                    "dougan",
                    "豆干",
                    evidence_role="listed_component_anchor_candidate",
                )
            ]
        ),
        gap_register=None,
    )

    result = artifact["validated_candidates"][0]
    assert result["validation_status"] == "validator_passed"
    assert result["evidence_role"] == "listed_component_anchor_candidate"
    assert result["promotion_status"] == "validator_passed"
    assert result["runtime_truth_allowed"] is False
    assert artifact["packet_truth_created"] is False
    assert artifact["runtime_truth_changed"] is False


def test_validator_rejects_missing_provenance_invalid_kcal_and_unsupported_source() -> None:
    missing_provenance = _candidate("missing_provenance", "bad")
    missing_provenance["source_provenance"] = {}
    invalid_kcal = _candidate("invalid_kcal", "bad kcal", kcal=-10)
    unsupported = _candidate(
        "unsupported",
        "unsupported source",
        source_id="blog_source",
        source_class="blog",
    )

    artifact = build_food_evidence_candidate_validation_artifact(
        candidate_artifact=_candidate_artifact([missing_provenance, invalid_kcal, unsupported]),
        gap_register=None,
    )

    by_id = {item["candidate_id"]: item for item in artifact["validated_candidates"]}
    assert by_id["missing_provenance"]["validation_status"] == "rejected"
    assert "missing_source_provenance" in by_id["missing_provenance"]["validation_reasons"]
    assert by_id["invalid_kcal"]["validation_status"] == "rejected"
    assert "invalid_kcal_point" in by_id["invalid_kcal"]["validation_reasons"]
    assert by_id["unsupported"]["validation_status"] == "rejected"
    assert "unsupported_source_class" in by_id["unsupported"]["validation_reasons"]
    assert artifact["summary"]["rejected_count"] == 3


def test_validator_marks_duplicate_or_alias_collision_as_source_repair() -> None:
    artifact = build_food_evidence_candidate_validation_artifact(
        candidate_artifact=_candidate_artifact(
            [
                _candidate("c1", "\u62ff\u9435", aliases=["latte"]),
                _candidate("c2", "latte", aliases=[]),
            ]
        ),
        gap_register=None,
    )

    by_id = {item["candidate_id"]: item for item in artifact["validated_candidates"]}
    assert by_id["c1"]["validation_status"] == "needs_source_repair"
    assert by_id["c2"]["validation_status"] == "needs_source_repair"
    assert "duplicate_or_alias_collision" in by_id["c1"]["validation_reasons"]
    assert artifact["summary"]["needs_source_repair_count"] == 2


def test_validator_reports_parse_error_sources_as_source_repair() -> None:
    artifact = build_food_evidence_candidate_validation_artifact(
        candidate_artifact=_candidate_artifact(
            [],
            reports=[
                {
                    "source_id": "openfoodfacts_taiwan_small",
                    "parse_error": "JSONDecodeError",
                }
            ],
        ),
        gap_register=None,
    )

    assert artifact["source_repair_report"] == [
        {
            "source_id": "openfoodfacts_taiwan_small",
            "repair_status": "needs_source_repair",
            "reason": "parse_error:JSONDecodeError",
        }
    ]
    assert artifact["summary"]["source_parse_error_count"] == 1


def test_validator_builds_pr110_gap_coverage_from_gap_register_and_candidates() -> None:
    artifact = build_food_evidence_candidate_validation_artifact(
        candidate_artifact=_candidate_artifact(
            [
                _candidate("danbing", "\u86cb\u9905"),
                _candidate("latte", "\u62ff\u9435"),
                _candidate("bento", "\u96de\u817f\u4fbf\u7576"),
                _candidate("rice", "\u767d\u98ef"),
                _candidate("bubble_tea", "\u73cd\u73e0\u5976\u8336"),
                _candidate("dougan", "\u8c46\u5e72"),
                _candidate("haidai", "\u6d77\u5e36"),
                _candidate("gongwan", "\u8ca2\u4e38"),
            ]
        ),
        gap_register=_gap_register(),
    )

    coverage = {
        item["gap_family"]: item
        for item in artifact["pr110_coverage_report"]["gap_family_coverage"]
    }
    assert coverage["breakfast_combo"]["coverage_status"] == "covered"
    assert coverage["chicken_bento_rice_modifier"]["coverage_status"] == "covered"
    assert coverage["bubble_tea_sugar_size_modifier"]["coverage_status"] == "covered"
    assert coverage["luwei_listed_components"]["coverage_status"] == "partial"
    assert coverage["luwei_listed_components"]["missing_keywords"] == ["\u9752\u83dc"]
    assert artifact["pr110_coverage_report"]["truth_promotion_allowed"] is False


def test_validator_cli_writes_roundtrippable_validation_artifact(tmp_path: Path) -> None:
    candidates_path = tmp_path / "candidates.json"
    gaps_path = tmp_path / "gaps.json"
    output_path = tmp_path / "validation.json"
    candidates_path.write_text(
        json.dumps(
            _candidate_artifact([_candidate("c1", "\u86cb\u9905")]),
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    gaps_path.write_text(json.dumps(_gap_register(), ensure_ascii=False), encoding="utf-8")

    from app.shared.infra.json_artifacts import read_json_artifact
    from scripts.build_accurate_intake_food_evidence_validation import main

    assert main(
        [
            "--candidate-json",
            str(candidates_path),
            "--food-gap-register",
            str(gaps_path),
            "--output",
            str(output_path),
        ]
    ) == 0
    artifact = read_json_artifact(output_path)

    assert artifact["summary"]["validator_passed_count"] == 1
    assert artifact["pr110_coverage_report"]["truth_promotion_allowed"] is False
