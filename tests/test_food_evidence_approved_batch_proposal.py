from __future__ import annotations

import json
from pathlib import Path

from app.nutrition.application.food_evidence_approved_batch_proposal import (
    build_food_evidence_approved_batch_proposal,
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
                    {
                        "candidate_id": "food_gap_breakfast_001",
                        "gap_family": "breakfast_combo",
                        "required_evidence_type": ["generic_anchor"],
                    }
                ],
            },
            {
                "gap_family": "bubble_tea_sugar_size_modifier",
                "status": "review_packet_only",
                "promotion_allowed": False,
                "candidates": [
                    {
                        "candidate_id": "food_gap_tea_001",
                        "gap_family": "bubble_tea_sugar_size_modifier",
                        "required_evidence_type": ["drink_base_anchor"],
                    }
                ],
            },
            {
                "gap_family": "luwei_listed_components",
                "status": "review_packet_only",
                "promotion_allowed": False,
                "candidates": [
                    {
                        "candidate_id": "food_gap_dinner_basket_001",
                        "gap_family": "luwei_listed_components",
                        "required_evidence_type": ["basket_component_anchor"],
                    }
                ],
            },
        ],
    }


def _decision(candidate_id: str, disposition: str, *, promotion_stage: str = "review_metadata_only") -> dict:
    return {
        "candidate_id": candidate_id,
        "disposition": disposition,
        "source_class": "taiwan_tfda_open_data",
        "source_provenance_decision": {
            "complete": True,
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
            "review_note": "range remains proposal metadata",
        },
        "macro_decision": {
            "macro_visibility_decision": "macro_null_allowed",
            "macro_null_reason": "generic source lacks validated serving macros",
            "macro_source_basis": "unknown",
            "macro_confidence": "unknown",
        },
        "promotion_stage": promotion_stage,
        "review_note": f"{disposition} as proposal metadata only",
        "runtime_truth_allowed": False,
        "promotion_allowed_by_validator": False,
    }


def _review_decision_artifact(*, status: str = "valid_review_metadata") -> dict:
    return {
        "artifact_type": "accurate_intake_food_evidence_human_review_decision",
        "artifact_schema_version": "1.0",
        "status": status,
        "claim_scope": "human_review_metadata_only",
        "reviewer_id": "founder-local-review",
        "reviewed_at_utc": "2026-05-10T08:00:00Z",
        "summary": {
            "decision_count": 3,
            "approved_count": 1,
            "rejected_count": 1,
            "deferred_count": 1,
            "invalid_count": 0,
        },
        "blockers": [],
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
        "food_kb_truth_updated": False,
        "runtime_truth_changed": False,
        "packet_truth_created": False,
    }


def test_approved_batch_proposal_filters_only_approved_decisions_without_truth_promotion() -> None:
    proposal = build_food_evidence_approved_batch_proposal(
        review_pack=_review_pack(),
        review_decision_artifact=_review_decision_artifact(),
    )

    assert proposal["artifact_type"] == "accurate_intake_food_evidence_approved_batch_proposal"
    assert proposal["status"] == "valid_promotion_blocked_proposal"
    assert proposal["claim_scope"] == "approved_food_evidence_batch_proposal_no_truth_promotion"
    assert proposal["promotion_blocked_by_default"] is True
    assert proposal["runtime_truth_changed"] is False
    assert proposal["food_kb_truth_updated"] is False
    assert proposal["packet_truth_created"] is False
    assert proposal["manager_or_appshell_behavior_changed"] is False
    assert proposal["summary"] == {
        "approved_candidate_count": 1,
        "rejected_candidate_count": 1,
        "deferred_candidate_count": 1,
        "blocked_candidate_count": 0,
    }
    assert [item["candidate_id"] for item in proposal["approved_candidates"]] == [
        "food_gap_breakfast_001"
    ]
    approved = proposal["approved_candidates"][0]
    assert approved["runtime_truth_allowed"] is False
    assert approved["promotion_allowed_by_proposal"] is False
    assert approved["source_class"] == "taiwan_tfda_open_data"
    assert approved["source_provenance_refs"] == ["tfda-row-001"]
    assert approved["serving_portion_decision"]["serving_basis"] == "common_serving"
    assert approved["kcal_decision"]["kcal_point"] == 320
    assert approved["macro_decision"]["macro_visibility_decision"] == "macro_null_allowed"
    assert approved["macro_decision"]["macro_null_reason"] == (
        "generic source lacks validated serving macros"
    )
    assert proposal["excluded_decisions"] == [
        {"candidate_id": "food_gap_tea_001", "disposition": "reject"},
        {"candidate_id": "food_gap_dinner_basket_001", "disposition": "defer"},
    ]
    assert "no_runtime_truth_promotion" in proposal["non_claims"]


def test_approved_batch_proposal_fails_closed_for_blocked_or_runtime_truth_decision() -> None:
    decision_artifact = _review_decision_artifact(status="blocked")
    decision_artifact["decisions"][0] = _decision(
        "food_gap_breakfast_001",
        "approve",
        promotion_stage="runtime_truth",
    )
    decision_artifact["runtime_truth_changed"] = True

    proposal = build_food_evidence_approved_batch_proposal(
        review_pack=_review_pack(),
        review_decision_artifact=decision_artifact,
    )

    assert proposal["status"] == "blocked"
    assert "review_decision_artifact_not_valid" in proposal["blockers"]
    assert "runtime_truth_claim_present" in proposal["blockers"]
    assert "promotion_stage_claims_runtime_truth:food_gap_breakfast_001" in proposal["blockers"]
    assert proposal["approved_candidates"] == []


def test_approved_batch_proposal_rejects_stale_or_missing_candidate_reference() -> None:
    decision_artifact = _review_decision_artifact()
    decision_artifact["decisions"][0] = _decision("food_gap_not_in_review_pack", "approve")

    proposal = build_food_evidence_approved_batch_proposal(
        review_pack=_review_pack(),
        review_decision_artifact=decision_artifact,
    )

    assert proposal["status"] == "blocked"
    assert "approved_candidate_not_in_review_pack:food_gap_not_in_review_pack" in proposal["blockers"]
    assert proposal["approved_candidates"] == []


def test_approved_batch_proposal_builder_script_writes_metadata_only_artifact(tmp_path: Path) -> None:
    review_pack = tmp_path / "review_pack.json"
    decision_artifact = tmp_path / "review_decision.json"
    output = tmp_path / "approved_batch_proposal.json"
    review_pack.write_text(json.dumps(_review_pack(), ensure_ascii=False), encoding="utf-8")
    decision_artifact.write_text(
        json.dumps(_review_decision_artifact(), ensure_ascii=False),
        encoding="utf-8",
    )

    from scripts.build_accurate_intake_food_evidence_approved_batch_proposal import main

    assert main(
        [
            "--review-pack",
            str(review_pack),
            "--review-decision",
            str(decision_artifact),
            "--output",
            str(output),
        ]
    ) == 0

    artifact = json.loads(output.read_text(encoding="utf-8"))
    assert artifact["status"] == "valid_promotion_blocked_proposal"
    assert artifact["promotion_blocked_by_default"] is True
    assert sorted(path.name for path in tmp_path.iterdir()) == [
        "approved_batch_proposal.json",
        "review_decision.json",
        "review_pack.json",
    ]
