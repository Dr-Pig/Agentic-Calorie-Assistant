from __future__ import annotations

import json
from pathlib import Path

from app.nutrition.application.food_evidence_review_decision import (
    build_food_evidence_review_decision_artifact,
)


def _review_pack() -> dict:
    return {
        "artifact_type": "accurate_intake_food_evidence_human_review_pack",
        "artifact_schema_version": "1.0",
        "claim_scope": "human_review_pack_before_fooddb_truth_promotion",
        "review_packets": [
            {
                "gap_family": "breakfast_combo",
                "status": "review_packet_only",
                "promotion_allowed": False,
                "candidates": [
                    {"candidate_id": "food_gap_breakfast_001", "gap_family": "breakfast_combo"}
                ],
            },
            {
                "gap_family": "bubble_tea_sugar_size_modifier",
                "status": "review_packet_only",
                "promotion_allowed": False,
                "candidates": [
                    {"candidate_id": "food_gap_tea_001", "gap_family": "bubble_tea_sugar_size_modifier"}
                ],
            },
            {
                "gap_family": "luwei_listed_components",
                "status": "review_packet_only",
                "promotion_allowed": False,
                "candidates": [
                    {"candidate_id": "food_gap_dinner_basket_001", "gap_family": "luwei_listed_components"}
                ],
            },
        ],
        "food_kb_truth_updated": False,
        "packet_truth_created": False,
    }


def _decision(
    candidate_id: str,
    disposition: str,
    *,
    promotion_stage: str = "review_metadata_only",
    source_provenance_complete: bool = True,
    macro_visibility_decision: str = "macro_null_allowed",
    macro_null_reason: str | None = "generic source does not provide validated serving macros",
) -> dict:
    return {
        "candidate_id": candidate_id,
        "disposition": disposition,
        "source_class": "taiwan_tfda_open_data",
        "source_provenance_decision": {
            "complete": source_provenance_complete,
            "source_refs": ["tfda-row-001"],
            "review_note": "source class reviewed",
        },
        "serving_portion_decision": {
            "serving_basis": "common_serving",
            "portion_basis": {"portion_unit": "serving", "portion_quantity": 1},
            "review_note": "common serving needs later anchor proposal",
        },
        "kcal_decision": {
            "kcal_point": 320,
            "kcal_range": [280, 380],
            "review_note": "range remains review metadata",
        },
        "macro_decision": {
            "macro_visibility_decision": macro_visibility_decision,
            "macro_null_reason": macro_null_reason,
            "macro_source_basis": "unknown",
            "macro_confidence": "unknown",
        },
        "promotion_stage": promotion_stage,
        "review_note": f"{disposition} as review metadata only",
    }


def _decision_payload() -> dict:
    return {
        "artifact_type": "accurate_intake_food_evidence_human_review_decision_input",
        "reviewer_id": "founder-local-review",
        "reviewed_at_utc": "2026-05-10T08:00:00Z",
        "decisions": [
            _decision("food_gap_breakfast_001", "approve"),
            _decision("food_gap_tea_001", "reject"),
            _decision("food_gap_dinner_basket_001", "defer"),
        ],
        "non_claims": [
            "no_fooddb_truth_promoted",
            "no_runtime_truth_changed",
            "no_anchor_update",
            "no_packet_truth_created",
            "no_manager_or_appshell_behavior_change",
            "no_eval_oracle_created",
            "no_mutation_authority",
        ],
    }


def test_review_decision_artifact_records_approve_reject_defer_without_truth_promotion() -> None:
    artifact = build_food_evidence_review_decision_artifact(
        review_pack=_review_pack(),
        decision_payload=_decision_payload(),
    )

    assert artifact["artifact_type"] == "accurate_intake_food_evidence_human_review_decision"
    assert artifact["status"] == "valid_review_metadata"
    assert artifact["claim_scope"] == "human_review_metadata_only"
    assert artifact["reviewer_id"] == "founder-local-review"
    assert artifact["summary"] == {
        "decision_count": 3,
        "approved_count": 1,
        "rejected_count": 1,
        "deferred_count": 1,
        "invalid_count": 0,
    }
    assert artifact["food_kb_truth_updated"] is False
    assert artifact["nutrition_seed_created"] is False
    assert artifact["exact_card_created"] is False
    assert artifact["packet_truth_created"] is False
    assert artifact["runtime_truth_changed"] is False
    assert artifact["canonical_eval_promoted"] is False
    assert artifact["manager_or_appshell_behavior_changed"] is False
    assert artifact["review_policy"]["truth_owner"] == "human_reviewer"
    assert artifact["review_policy"]["deterministic_role"] == "validate_shape_refs_and_non_claims_only"
    assert artifact["review_policy"]["validator_success_promotes_truth"] is False
    dispositions = {decision["candidate_id"]: decision["disposition"] for decision in artifact["decisions"]}
    assert dispositions == {
        "food_gap_breakfast_001": "approve",
        "food_gap_tea_001": "reject",
        "food_gap_dinner_basket_001": "defer",
    }
    assert all(decision["runtime_truth_allowed"] is False for decision in artifact["decisions"])


def test_review_decision_rejects_unknown_candidate_id() -> None:
    payload = _decision_payload()
    payload["decisions"][0] = _decision("food_gap_unknown", "approve")

    artifact = build_food_evidence_review_decision_artifact(
        review_pack=_review_pack(),
        decision_payload=payload,
    )

    assert artifact["status"] == "blocked"
    assert "unknown_candidate_id:food_gap_unknown" in artifact["blockers"]


def test_review_decision_rejects_missing_provenance_or_macro_reason() -> None:
    payload = _decision_payload()
    payload["decisions"][0] = _decision(
        "food_gap_breakfast_001",
        "approve",
        source_provenance_complete=False,
    )
    payload["decisions"][1] = _decision(
        "food_gap_tea_001",
        "reject",
        macro_visibility_decision="macro_null_allowed",
        macro_null_reason=None,
    )

    artifact = build_food_evidence_review_decision_artifact(
        review_pack=_review_pack(),
        decision_payload=payload,
    )

    assert artifact["status"] == "blocked"
    assert "missing_provenance_decision:food_gap_breakfast_001" in artifact["blockers"]
    assert "missing_macro_visibility_or_null_reason:food_gap_tea_001" in artifact["blockers"]


def test_review_decision_rejects_runtime_truth_promotion_or_missing_non_claims() -> None:
    payload = _decision_payload()
    payload["decisions"][0] = _decision(
        "food_gap_breakfast_001",
        "approve",
        promotion_stage="runtime_truth",
    )
    payload["non_claims"] = []

    artifact = build_food_evidence_review_decision_artifact(
        review_pack=_review_pack(),
        decision_payload=payload,
    )

    assert artifact["status"] == "blocked"
    assert "promotion_stage_claims_runtime_truth:food_gap_breakfast_001" in artifact["blockers"]
    assert "artifact_missing_non_claims" in artifact["blockers"]


def test_review_decision_builder_script_writes_metadata_only_artifact(tmp_path: Path) -> None:
    review_pack = tmp_path / "review_pack.json"
    decisions = tmp_path / "decisions.json"
    output = tmp_path / "review_decision.json"
    review_pack.write_text(json.dumps(_review_pack(), ensure_ascii=False), encoding="utf-8")
    decisions.write_text(json.dumps(_decision_payload(), ensure_ascii=False), encoding="utf-8")

    from scripts.build_accurate_intake_food_evidence_review_decision import main

    assert main(
        [
            "--review-pack",
            str(review_pack),
            "--decision-payload",
            str(decisions),
            "--output",
            str(output),
        ]
    ) == 0

    artifact = json.loads(output.read_text(encoding="utf-8"))
    assert artifact["status"] == "valid_review_metadata"
    assert artifact["claim_scope"] == "human_review_metadata_only"
    assert sorted(path.name for path in tmp_path.iterdir()) == [
        "decisions.json",
        "review_decision.json",
        "review_pack.json",
    ]
