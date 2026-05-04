from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.nutrition.application.food_evidence_candidate_triage_report import build_food_evidence_candidate_triage_report  # noqa: E402


def _validated_candidate(
    candidate_id: str,
    label: str,
    *,
    source_class: str,
    evidence_role: str,
    status: str = "validator_passed",
) -> dict:
    return {
        "candidate_id": candidate_id,
        "source_id": f"{candidate_id}_source",
        "source_class": source_class,
        "evidence_role": evidence_role,
        "canonical_label": label,
        "aliases": [f"{label}-alt"],
        "kcal_point": 123,
        "validation_status": status,
        "validation_reasons": [] if status == "validator_passed" else ["needs_review"],
        "runtime_truth_allowed": False,
        "packet_ready": False,
        "promotion_status": status,
    }


def _validation_artifact() -> dict:
    validated_candidates = [
        _validated_candidate(
            "tfda_generic",
            "tfda drink",
            source_class="taiwan_tfda_open_data",
            evidence_role="generic_anchor_candidate",
        ),
        _validated_candidate(
            "official_exact",
            "official dessert",
            source_class="official_brand_chain_page",
            evidence_role="exact_card_candidate",
        ),
        _validated_candidate(
            "repair_entry",
            "repair me",
            source_class="taiwan_tfda_open_data",
            evidence_role="generic_anchor_candidate",
            status="needs_source_repair",
        ),
        _validated_candidate(
            "rejected_entry",
            "reject me",
            source_class="open_food_facts",
            evidence_role="packaged_candidate",
            status="rejected",
        ),
    ]
    return {
        "artifact_type": "accurate_intake_food_evidence_candidate_validation",
        "claim_scope": "food_evidence_candidate_validation_only",
        "summary": {
            "candidate_count": 4,
            "validator_passed_count": 2,
            "rejected_count": 1,
            "needs_source_repair_count": 1,
            "source_parse_error_count": 1,
        },
        "validated_candidates": validated_candidates,
        "source_repair_report": [
            {
                "source_id": "tfda_parse_issue",
                "repair_status": "needs_source_repair",
                "reason": "parse_error:sheet mismatch",
            }
        ],
        "pr110_coverage_report": {
            "truth_promotion_allowed": False,
            "gap_family_coverage": [],
        },
    }


def _auto_eligible_artifact() -> dict:
    return {
        "artifact_type": "accurate_intake_food_auto_eligible_candidate_batch",
        "claim_scope": "food_evidence_auto_eligible_candidates_only",
        "summary": {
            "validated_candidate_count": 4,
            "auto_eligible_count": 2,
            "exception_count": 2,
            "sample_audit_group_count": 2,
        },
        "auto_eligible_candidates": [
            {
                "candidate_id": "tfda_generic",
                "source_id": "tfda_generic_source",
                "source_class": "taiwan_tfda_open_data",
                "evidence_role": "generic_anchor_candidate",
                "canonical_label": "tfda drink",
                "aliases": ["tfda drink-alt"],
                "kcal_point": 123,
                "validation_status": "validator_passed",
                "promotion_status": "auto_eligible_packet_candidate",
                "runtime_truth_allowed": False,
                "packet_ready": False,
            },
            {
                "candidate_id": "official_exact",
                "source_id": "official_exact_source",
                "source_class": "official_brand_chain_page",
                "evidence_role": "exact_card_candidate",
                "canonical_label": "official dessert",
                "aliases": ["official dessert-alt"],
                "kcal_point": 123,
                "validation_status": "validator_passed",
                "promotion_status": "auto_eligible_packet_candidate",
                "runtime_truth_allowed": False,
                "packet_ready": False,
            },
        ],
        "exception_report": [
            {
                "candidate_id": "repair_entry",
                "source_id": "repair_entry_source",
                "source_class": "taiwan_tfda_open_data",
                "evidence_role": "generic_anchor_candidate",
                "validation_status": "needs_source_repair",
                "validation_reasons": ["needs_review"],
                "exception_reason": "validation_not_passed",
                "runtime_truth_allowed": False,
                "packet_ready": False,
            },
            {
                "candidate_id": "rejected_entry",
                "source_id": "rejected_entry_source",
                "source_class": "open_food_facts",
                "evidence_role": "packaged_candidate",
                "validation_status": "rejected",
                "validation_reasons": ["needs_review"],
                "exception_reason": "validation_not_passed",
                "runtime_truth_allowed": False,
                "packet_ready": False,
            },
        ],
        "sample_audit_report": [
            {
                "sample_group": "taiwan_tfda_open_data/generic_anchor_candidate",
                "available_count": 1,
                "sample_size": 1,
                "sample_only_not_approved": True,
                "approval_granted": False,
                "samples": [
                    {
                        "candidate_id": "tfda_generic",
                        "canonical_label": "tfda drink",
                        "source_id": "tfda_generic_source",
                        "kcal_point": 123,
                        "runtime_truth_allowed": False,
                    }
                ],
            },
            {
                "sample_group": "official_brand_chain_page/exact_card_candidate",
                "available_count": 1,
                "sample_size": 1,
                "sample_only_not_approved": True,
                "approval_granted": False,
                "samples": [
                    {
                        "candidate_id": "official_exact",
                        "canonical_label": "official dessert",
                        "source_id": "official_exact_source",
                        "kcal_point": 123,
                        "runtime_truth_allowed": False,
                    }
                ],
            },
        ],
        "source_validation_summary": _validation_artifact()["summary"],
        "pr110_coverage_report": {"truth_promotion_allowed": False, "gap_family_coverage": []},
    }


def test_candidate_triage_report_classifies_lanes_and_stop_rules() -> None:
    report = build_food_evidence_candidate_triage_report(
        validation_artifact=_validation_artifact(),
        auto_eligible_artifact=_auto_eligible_artifact(),
    )

    assert report["artifact_type"] == "accurate_intake_food_candidate_triage_report"
    assert report["generated_at_utc"] is None
    assert report["claim_scope"] == "food_candidate_triage_report_only"
    assert report["runtime_truth_changed"] is False
    assert report["packet_truth_changed"] is False
    assert report["shared_contract_changed"] is False
    assert report["live_provider_used"] is False
    assert report["coverage_stop_rule"] == {
        "common_serving_anchor_max_before_activation": 80,
        "listed_basket_components_max_before_activation": 60,
    }
    assert report["validation_summary_compact"] == {
        "candidate_count": 4,
        "validator_passed_count": 2,
        "rejected_count": 1,
        "needs_source_repair_count": 1,
        "source_parse_error_count": 1,
    }
    assert report["auto_eligible_summary_compact"] == {
        "validated_candidate_count": 4,
        "auto_eligible_count": 2,
        "exception_count": 2,
        "sample_audit_group_count": 2,
    }
    assert report["summary"] == {
        "tfda_generic_auto_eligible_count": 1,
        "official_exact_candidate_only_count": 1,
        "source_repair_required_count": 1,
        "rejected_count": 1,
    }
    assert report["auto_eligible_group_counts"] == [
        {
            "source_class": "official_brand_chain_page",
            "evidence_role": "exact_card_candidate",
            "count": 1,
        },
        {
            "source_class": "taiwan_tfda_open_data",
            "evidence_role": "generic_anchor_candidate",
            "count": 1,
        },
    ]
    tfda_lane = report["lane_map"]["tfda_generic_runtime_batch_candidates"]
    exact_lane = report["lane_map"]["official_exact_candidate_only"]
    repair_lane = report["lane_map"]["source_repair_required"]
    rejected_lane = report["lane_map"]["rejected"]

    assert tfda_lane["lane_count"] == 1
    assert tfda_lane["candidate_ids"] == ["tfda_generic"]
    assert tfda_lane["runtime_truth_allowed"] is False
    assert tfda_lane["next_action"] == "runtime-batch-plan"

    assert exact_lane["lane_count"] == 1
    assert exact_lane["candidate_ids"] == ["official_exact"]
    assert exact_lane["runtime_truth_allowed"] is False
    assert exact_lane["next_action"] == "exact-candidate-review"

    assert repair_lane["lane_count"] == 1
    assert repair_lane["candidate_ids"] == ["repair_entry"]
    assert repair_lane["source_ids"] == ["tfda_parse_issue"]
    assert repair_lane["next_action"] == "source-repair"

    assert rejected_lane["lane_count"] == 1
    assert rejected_lane["candidate_ids"] == ["rejected_entry"]
    assert rejected_lane["next_action"] == "do-not-promote"


def test_candidate_triage_report_separates_repair_and_rejected_entries() -> None:
    report = build_food_evidence_candidate_triage_report(
        validation_artifact=_validation_artifact(),
        auto_eligible_artifact=_auto_eligible_artifact(),
    )

    repair_lane = report["lane_map"]["source_repair_required"]
    rejected_lane = report["lane_map"]["rejected"]

    assert repair_lane["candidate_ids"] == ["repair_entry"]
    assert rejected_lane["candidate_ids"] == ["rejected_entry"]
    assert report["source_repair_cluster_summary"] == {
        "cluster_count": 1,
        "clusters": [
            {
                "repair_cluster": "parse_error",
                "count": 1,
                "source_ids": ["tfda_parse_issue"],
                "source_repair_reason": "parse_error:sheet mismatch",
            }
        ],
    }
    assert all(
        item["validation_status"] == "needs_source_repair"
        for item in report["lane_map"]["source_repair_required"]["records"]
    )
    assert all(
        item["validation_status"] == "rejected"
        for item in report["lane_map"]["rejected"]["records"]
    )


def test_candidate_triage_report_cli_writes_roundtrippable_artifact(tmp_path: Path) -> None:
    validation_path = tmp_path / "validation.json"
    auto_path = tmp_path / "auto.json"
    output_path = tmp_path / "triage.json"
    validation_path.write_text(
        json.dumps(_validation_artifact(), ensure_ascii=False),
        encoding="utf-8",
    )
    auto_path.write_text(
        json.dumps(_auto_eligible_artifact(), ensure_ascii=False),
        encoding="utf-8",
    )

    from app.shared.infra.json_artifacts import read_json_artifact
    from scripts.build_accurate_intake_food_candidate_triage_report import main

    assert (
        main(
            [
                "--validation-json",
                str(validation_path),
                "--auto-eligible-json",
                str(auto_path),
                "--output",
                str(output_path),
            ]
        )
        == 0
    )

    artifact = read_json_artifact(output_path)
    assert artifact["summary"]["tfda_generic_auto_eligible_count"] == 1
    assert artifact["summary"]["official_exact_candidate_only_count"] == 1
    assert artifact["coverage_stop_rule"]["common_serving_anchor_max_before_activation"] == 80
    assert artifact["non_claims"] == [
        "no_packet_truth_claim",
        "no_runtime_truth_claim",
        "no_shared_contract_change",
        "no_live_provider_call",
        "report_only",
    ]
