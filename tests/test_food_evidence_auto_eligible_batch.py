from __future__ import annotations

import json
from pathlib import Path

from app.nutrition.application.food_evidence_auto_eligible_batch import (
    build_food_evidence_auto_eligible_batch,
)


def _validated_candidate(
    candidate_id: str,
    label: str,
    *,
    source_class: str = "taiwan_tfda_open_data",
    source_id: str = "tfda_base_review_candidates",
    evidence_role: str = "generic_anchor_candidate",
    status: str = "validator_passed",
    reasons: list[str] | None = None,
) -> dict:
    return {
        "candidate_id": candidate_id,
        "source_id": source_id,
        "source_class": source_class,
        "evidence_role": evidence_role,
        "canonical_label": label,
        "aliases": [],
        "kcal_point": 250,
        "validation_status": status,
        "validation_reasons": reasons or [],
        "runtime_truth_allowed": False,
        "packet_ready": False,
        "promotion_status": "validator_passed" if status == "validator_passed" else status,
    }


def _validation_artifact(candidates: list[dict]) -> dict:
    return {
        "artifact_type": "accurate_intake_food_evidence_candidate_validation",
        "claim_scope": "food_evidence_candidate_validation_only",
        "food_kb_truth_updated": False,
        "nutrition_seed_created": False,
        "exact_card_created": False,
        "packet_truth_created": False,
        "canonical_eval_promoted": False,
        "runtime_truth_changed": False,
        "summary": {
            "candidate_count": len(candidates),
            "validator_passed_count": sum(
                1 for item in candidates if item["validation_status"] == "validator_passed"
            ),
        },
        "validated_candidates": candidates,
        "source_repair_report": [],
        "pr110_coverage_report": {
            "truth_promotion_allowed": False,
            "gap_family_coverage": [
                {"gap_family": "breakfast_combo", "coverage_status": "covered"}
            ],
        },
    }


def test_auto_eligible_batch_adds_approval_metadata_without_runtime_truth() -> None:
    artifact = build_food_evidence_auto_eligible_batch(
        validation_artifact=_validation_artifact(
            [_validated_candidate("c1", "\u86cb\u9905")]
        ),
        sample_size_per_group=2,
    )

    assert artifact["claim_scope"] == "food_evidence_auto_eligible_candidates_only"
    assert artifact["food_kb_truth_updated"] is False
    assert artifact["packet_truth_created"] is False
    assert artifact["runtime_truth_changed"] is False
    assert artifact["summary"]["auto_eligible_count"] == 1
    candidate = artifact["auto_eligible_candidates"][0]
    assert candidate["candidate_id"] == "c1"
    assert candidate["promotion_status"] == "auto_eligible_packet_candidate"
    assert candidate["runtime_truth_allowed"] is False
    assert candidate["packet_ready"] is False
    assert candidate["approval_metadata"] == {
        "approval_mode": "batch_policy_pending",
        "approval_scope": "source_class_and_semantic_role_batch",
        "policy_version": "food_evidence_mvp_auto_eligible_v1",
        "approved_by": None,
        "approved_at": None,
        "runtime_truth_allowed": False,
    }


def test_auto_eligible_includes_validated_tfda_listed_component_candidates() -> None:
    artifact = build_food_evidence_auto_eligible_batch(
        validation_artifact=_validation_artifact(
            [
                _validated_candidate(
                    "dougan",
                    "豆干",
                    evidence_role="listed_component_anchor_candidate",
                )
            ]
        ),
        sample_size_per_group=2,
    )

    assert artifact["summary"]["auto_eligible_count"] == 1
    candidate = artifact["auto_eligible_candidates"][0]
    assert candidate["evidence_role"] == "listed_component_anchor_candidate"
    assert candidate["promotion_status"] == "auto_eligible_packet_candidate"
    assert candidate["runtime_truth_allowed"] is False
    assert candidate["packet_ready"] is False


def test_auto_eligible_blocks_validator_failures_and_non_auto_sources() -> None:
    artifact = build_food_evidence_auto_eligible_batch(
        validation_artifact=_validation_artifact(
            [
                _validated_candidate("tfda", "\u86cb\u9905"),
                _validated_candidate(
                    "off",
                    "packaged",
                    source_class="open_food_facts",
                    source_id="openfoodfacts_taiwan_small",
                    evidence_role="packaged_candidate",
                ),
                _validated_candidate(
                    "local_exact",
                    "local packaged exact",
                    source_class="local_taiwan_packaged_extract",
                    source_id="local_tw_packaged_extract_188_2",
                    evidence_role="exact_card_candidate",
                ),
                _validated_candidate(
                    "usda",
                    "fallback",
                    source_class="usda_fallback",
                    source_id="usda_food_list_sample",
                    evidence_role="fallback_anchor_candidate",
                ),
                _validated_candidate(
                    "old",
                    "old seed",
                    source_class="existing_repo_seed",
                    source_id="base_nutrition_db",
                    evidence_role="alias_coverage_prior",
                ),
                _validated_candidate(
                    "repair",
                    "collision",
                    status="needs_source_repair",
                    reasons=["duplicate_or_alias_collision"],
                ),
            ]
        ),
        sample_size_per_group=2,
    )

    assert artifact["summary"]["auto_eligible_count"] == 1
    exceptions = {item["candidate_id"]: item for item in artifact["exception_report"]}
    assert exceptions["off"]["exception_reason"] == "source_class_not_auto_eligible"
    assert exceptions["local_exact"]["exception_reason"] == "source_class_not_auto_eligible"
    assert exceptions["usda"]["exception_reason"] == "source_class_not_auto_eligible"
    assert exceptions["old"]["exception_reason"] == "source_class_not_auto_eligible"
    assert exceptions["repair"]["exception_reason"] == "validation_not_passed"
    assert all(item["runtime_truth_allowed"] is False for item in artifact["exception_report"])


def test_auto_eligible_sample_audit_is_limited_and_not_approval() -> None:
    artifact = build_food_evidence_auto_eligible_batch(
        validation_artifact=_validation_artifact(
            [
                _validated_candidate(f"c{index}", f"item {index}")
                for index in range(5)
            ]
        ),
        sample_size_per_group=2,
    )

    audit = artifact["sample_audit_report"][0]
    assert audit["sample_group"] == "taiwan_tfda_open_data/generic_anchor_candidate"
    assert audit["sample_size"] == 2
    assert audit["sample_only_not_approved"] is True
    assert audit["approval_granted"] is False
    assert len(audit["samples"]) == 2


def test_auto_eligible_preserves_fooddb_truth_files(tmp_path: Path) -> None:
    protected_truth = [
        Path("app/knowledge/small_anchor_store_tw.json"),
        Path("app/knowledge/exact_item_cards_tw.json"),
    ]
    before = {path.as_posix(): path.read_bytes() for path in protected_truth}

    artifact = build_food_evidence_auto_eligible_batch(
        validation_artifact=_validation_artifact(
            [_validated_candidate("c1", "\u86cb\u9905")]
        ),
        sample_size_per_group=2,
    )

    after = {path.as_posix(): path.read_bytes() for path in protected_truth}
    assert after == before
    assert artifact["summary"]["auto_eligible_count"] == 1
    assert artifact["food_kb_truth_updated"] is False
    assert artifact["runtime_truth_changed"] is False


def test_auto_eligible_cli_writes_roundtrippable_report(tmp_path: Path) -> None:
    validation_path = tmp_path / "validation.json"
    output_path = tmp_path / "auto_eligible.json"
    validation_path.write_text(
        json.dumps(
            _validation_artifact([_validated_candidate("c1", "\u86cb\u9905")]),
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    from app.shared.infra.json_artifacts import read_json_artifact
    from scripts.build_accurate_intake_food_auto_eligible_batch import main

    assert main(
        [
            "--validation-json",
            str(validation_path),
            "--output",
            str(output_path),
            "--sample-size-per-group",
            "2",
        ]
    ) == 0
    artifact = read_json_artifact(output_path)

    assert artifact["summary"]["auto_eligible_count"] == 1
    assert artifact["auto_eligible_candidates"][0]["runtime_truth_allowed"] is False
