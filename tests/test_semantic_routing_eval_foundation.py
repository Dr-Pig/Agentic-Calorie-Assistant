from __future__ import annotations

import json
from pathlib import Path

from scripts import run_semantic_routing_eval as semantic_eval


ROOT = Path(__file__).resolve().parents[1]
PROVISIONAL_PACK_PATH = ROOT / "docs" / "quality" / "benchmarks" / "semantic_routing" / "semantic_routing_founder_fit_pack_v1.json"
OFFICIAL_PACK_PATH = ROOT / "docs" / "quality" / "benchmarks" / "semantic_routing" / "semantic_routing_official_canonical_pack_v1.json"
CANDIDATE_QUEUE_PATH = ROOT / "docs" / "quality" / "benchmarks" / "semantic_routing" / "semantic_routing_candidate_review_queue_v1.json"


def test_semantic_routing_pack_has_required_shape() -> None:
    payload = json.loads(PROVISIONAL_PACK_PATH.read_text(encoding="utf-8"))

    assert payload["pack_id"] == "semantic_routing_founder_fit_pack_v1"
    assert payload["version"] >= 2
    assert payload["pack_mode"] == "provisional_smoke"
    assert payload["authority_level"] == "non_canonical"
    assert payload["approval_status"] == "exploratory_only"
    assert "must not be treated as product-approved benchmark truth" in payload["purpose"]
    assert "does not represent official product benchmark truth" in payload["non_canonical_note"]
    assert payload["style_personalization_extension_note"]["conversation_style_profile_defined"] is False
    assert "sour.md" in payload["style_personalization_extension_note"]["note"]

    cases = payload["cases"]
    assert len(cases) >= 14

    families = {case["expected_semantic_family"] for case in cases}
    assert {
        "proposal_accept",
        "proposal_reject",
        "proposal_defer",
        "proposal_adjust_shorter",
        "proposal_adjust_longer",
        "proposal_explain_request",
        "proposal_general_inquiry",
        "followup_completion",
        "followup_refinement",
        "new_topic_or_new_workflow",
    }.issubset(families)

    case_families = {case["case_family"] for case in cases}
    assert {"structured_action_equivalence", "workflow_boundary_discrimination", "ambiguity_bucket"}.issubset(case_families)

    drift_clusters = {case["drift_cluster"] for case in cases}
    assert {"rescue_action_family", "intake_followup_continuation", "boundary_discrimination_drift"}.issubset(drift_clusters)

    for case in cases:
        assert case["title"]
        assert case["utterance"]
        assert case["origin"]
        assert "state_pack_summary" in case
        assert "active_open_rescue_proposal" in case["state_pack_summary"]
        assert "pending_intake_followup" in case["state_pack_summary"]
        assert "latest_linked_ids" in case["state_pack_summary"]
        assert "recent_message_summaries" in case["state_pack_summary"]
        assert "thin_reason_bridge" in case["state_pack_summary"]
        assert case["expected_target_workflow_family"] in {"intake", "rescue", "general_chat"}
        assert case["expected_target_object_type"] in {"proposal", "meal_thread", "none"}
        assert case["expected_disposition"] in {
            "create",
            "continue",
            "correct",
            "accept",
            "reject",
            "defer",
            "adjust",
            "answer_only",
            "open_new_workflow",
        }
        assert case["expected_ambiguity_posture"] in {"none", "allow_uncertain"}
        assert case["state_pack_sufficiency_hint"] in {"sufficient", "possibly_insufficient_for_disambiguation"}
        assert case["provisional_hypothesis"] in {
            "prompt_issue",
            "taxonomy_issue",
            "state_pack_insufficiency",
            "inherently_ambiguous_case",
        }


def test_semantic_routing_summary_and_triage_contract() -> None:
    results = [
        {
            "case_id": "accept_ok",
            "expected": {
                "semantic_family": "proposal_accept",
                "target_object_type": "proposal",
                "target_object_id": 1,
                "target_workflow_family": "rescue",
                "disposition": "accept",
                "workflow_effect": "accept_and_apply_current_proposal",
            },
            "predicted": {
                "semantic_family": "proposal_accept",
                "target_object_type": "proposal",
                "target_object_id": 1,
                "target_workflow_family": "rescue",
                "disposition": "accept",
                "ambiguity_posture": "none",
                "workflow_effect": "accept_and_apply_current_proposal",
            },
            "oracle": {"passed": True},
            "triage": {
                "semantic_failure_cluster": "rescue_action_family",
                "routing_mismatch_types": [],
                "ambiguity_posture": "none",
                "state_pack_sufficiency": "sufficient",
                "provisional_hypothesis": "prompt_issue",
            },
        },
        {
            "case_id": "accept_fail",
            "expected": {
                "semantic_family": "proposal_accept",
                "target_object_type": "proposal",
                "target_object_id": 2,
                "target_workflow_family": "rescue",
                "disposition": "accept",
                "workflow_effect": "accept_and_apply_current_proposal",
            },
            "predicted": {
                "semantic_family": "proposal_general_inquiry",
                "target_object_type": "proposal",
                "target_object_id": 2,
                "target_workflow_family": "rescue",
                "disposition": "answer_only",
                "ambiguity_posture": "none",
                "workflow_effect": "answer_current_object",
            },
            "oracle": {
                "passed": False,
                "matched_target_workflow_family": True,
                "matched_target_object_type": True,
                "matched_target_object_id": True,
                "matched_disposition": False,
                "matched_workflow_effect": False,
                "matched_semantic_family": False,
            },
            "triage": {
                "semantic_failure_cluster": "rescue_action_family",
                "routing_mismatch_types": ["disposition_mismatch", "workflow_effect_mismatch", "secondary_semantic_family_mismatch"],
                "ambiguity_posture": "none",
                "state_pack_sufficiency": "sufficient",
                "provisional_hypothesis": "prompt_issue",
            },
        },
        {
            "case_id": "ambiguity_fail",
            "expected": {
                "semantic_family": "proposal_general_inquiry",
                "target_object_type": "meal_thread",
                "target_object_id": 806,
                "target_workflow_family": "intake",
                "disposition": "answer_only",
                "workflow_effect": "no_state_change_soft_hold",
            },
            "predicted": {
                "semantic_family": "followup_refinement",
                "target_object_type": "proposal",
                "target_object_id": 88,
                "target_workflow_family": "rescue",
                "disposition": "continue",
                "ambiguity_posture": "allow_uncertain",
                "workflow_effect": "continue_followup_lane",
            },
            "oracle": {
                "passed": False,
                "matched_target_workflow_family": False,
                "matched_target_object_type": False,
                "matched_target_object_id": False,
                "matched_disposition": False,
                "matched_workflow_effect": False,
                "matched_semantic_family": False,
            },
            "triage": {
                "semantic_failure_cluster": "boundary_discrimination_drift",
                "routing_mismatch_types": [
                    "target_workflow_family_mismatch",
                    "attachment_mismatch",
                    "disposition_mismatch",
                    "workflow_effect_mismatch",
                    "secondary_semantic_family_mismatch",
                ],
                "ambiguity_posture": "allow_uncertain",
                "state_pack_sufficiency": "possibly_insufficient_for_disambiguation",
                "provisional_hypothesis": "inherently_ambiguous_case",
            },
        },
    ]

    summary = semantic_eval._build_summary(
        results,
        pack_id="semantic_routing_founder_fit_pack_v1",
        provider_name="mock_semantic_routing",
        pack_mode="provisional_smoke",
        authority_level="non_canonical",
        approval_status="exploratory_only",
    )
    triage = semantic_eval._build_drift_triage(
        results,
        pack_id="semantic_routing_founder_fit_pack_v1",
        provider_name="mock_semantic_routing",
        pack_mode="provisional_smoke",
        authority_level="non_canonical",
    )

    assert summary["pack_id"] == "semantic_routing_founder_fit_pack_v1"
    assert summary["pack_mode"] == "provisional_smoke"
    assert summary["authority_level"] == "non_canonical"
    assert summary["approval_status"] == "exploratory_only"
    assert summary["provider"] == "mock_semantic_routing"
    assert summary["total_cases"] == 3
    assert summary["passed_cases"] == 1
    assert summary["failed_cases"] == 2
    assert summary["by_disposition"]["accept"] == {"total": 2, "passed": 1, "failed": 1}
    assert summary["by_semantic_family_secondary"]["proposal_accept"] == {"total": 2, "passed": 1, "failed": 1}

    assert triage["pack_id"] == "semantic_routing_founder_fit_pack_v1"
    assert triage["pack_mode"] == "provisional_smoke"
    assert triage["authority_level"] == "non_canonical"
    assert triage["provider"] == "mock_semantic_routing"
    assert triage["total_failures"] == 2
    clusters = {item["semantic_failure_cluster"]: item for item in triage["failure_clusters"]}
    assert set(clusters) == {"boundary_discrimination_drift", "rescue_action_family"}
    assert clusters["rescue_action_family"]["routing_mismatch_types"]["disposition_mismatch"] == 1
    assert clusters["boundary_discrimination_drift"]["ambiguity_postures"]["allow_uncertain"] == 1
    assert clusters["boundary_discrimination_drift"]["state_pack_sufficiency"]["possibly_insufficient_for_disambiguation"] == 1


def test_normalized_state_pack_exposes_canonical_target_vocabulary() -> None:
    normalized = semantic_eval._normalize_state_pack(
        {
            "active_open_rescue_proposal": {
                "proposal_container_id": 501,
                "proposal_status": "open",
            },
            "pending_intake_followup": {
                "meal_log_id": 801,
                "lane_family": "estimate_with_followup",
                "pending_question": "是哪一家、什麼大小、還有沒有加點？",
            },
            "latest_linked_ids": {
                "proposal_container_id": 501,
                "meal_log_id": 801,
            },
            "recent_message_summaries": [],
            "proposal_metadata": {"proposal_type": "rescue"},
            "thin_reason_bridge": None,
        }
    )

    assert normalized["target_vocabulary"]["target_workflow_family"] == [
        "intake",
        "rescue",
        "calibration",
        "recommendation",
        "body_observation",
        "general_chat",
    ]
    assert normalized["target_vocabulary"]["target_object_type"] == [
        "meal_thread",
        "proposal",
        "body_observation",
        "none",
    ]
    assert normalized["target_vocabulary"]["disposition"] == [
        "create",
        "continue",
        "correct",
        "accept",
        "reject",
        "defer",
        "adjust",
        "answer_only",
        "open_new_workflow",
    ]
    assert len(normalized["active_objects"]) == 2
    assert normalized["active_objects"][0]["workflow_family"] == "rescue"
    assert normalized["active_objects"][0]["recency_rank"] == 2
    assert normalized["active_objects"][0]["allowed_dispositions"] == ["accept", "reject", "defer", "adjust", "answer_only"]
    assert normalized["active_objects"][1]["workflow_family"] == "intake"
    assert normalized["active_objects"][1]["recency_rank"] == 1
    assert normalized["active_objects"][1]["family_hint"] == "followup_refinement"
    assert normalized["active_objects"][1]["selection_hint"] == "prefer_this_lane_for_untargeted_soft_stop"
    assert normalized["active_objects"][1]["allowed_dispositions"] == ["create", "continue", "correct", "answer_only"]
    assert "routing_priors" in normalized
    assert any("open a new workflow" in note for note in normalized["routing_priors"])
    assert any("short untargeted soft-stop" in note for note in normalized["routing_priors"])
    assert "raw_state_pack_summary" in normalized


def test_mock_semantic_routing_distinguishes_rescue_inquiry_from_reject() -> None:
    inquiry = semantic_eval._mock_predict(
        utterance="這樣也太硬了吧。",
        state_pack={
            "active_open_rescue_proposal": {"proposal_container_id": 123},
            "pending_intake_followup": None,
        },
    )
    reject = semantic_eval._mock_predict(
        utterance="不要這次，我先照原本節奏就好。",
        state_pack={
            "active_open_rescue_proposal": {"proposal_container_id": 123},
            "pending_intake_followup": None,
        },
    )

    assert inquiry["disposition"] == "answer_only"
    assert reject["disposition"] == "reject"


def test_mock_semantic_routing_allows_ask_clarify_for_ambiguous_case() -> None:
    predicted = semantic_eval._mock_predict(
        utterance="先這樣吧。",
        state_pack={
            "active_open_rescue_proposal": {"proposal_container_id": 510},
            "pending_intake_followup": {"meal_log_id": 806, "lane_family": "estimate_with_followup"},
        },
    )

    assert predicted["target_workflow_family"] == "intake"
    assert predicted["target_object_type"] == "meal_thread"
    assert predicted["disposition"] == "answer_only"
    assert predicted["ambiguity_posture"] == "allow_uncertain"
    assert predicted["workflow_effect"] == "no_state_change_soft_hold"


def test_run_case_uses_normalized_state_pack_in_output() -> None:
    payload = json.loads(PROVISIONAL_PACK_PATH.read_text(encoding="utf-8"))
    case = next(item for item in payload["cases"] if item["case_id"] == "semantic_routing_rescue_accept_001")

    result = __import__("asyncio").run(
        semantic_eval._run_case(case, provider=semantic_eval.MockSemanticRoutingProvider())
    )

    assert "target_vocabulary" in result["state_pack_summary"]
    assert result["source_state_pack_summary"]["active_open_rescue_proposal"]["proposal_container_id"] == 501
    assert result["predicted"]["target_workflow_family"] == "rescue"


def test_official_pack_starts_empty_and_canonical() -> None:
    payload = json.loads(OFFICIAL_PACK_PATH.read_text(encoding="utf-8"))

    assert payload["pack_id"] == "semantic_routing_official_canonical_pack_v1"
    assert payload["pack_mode"] == "official_canonical"
    assert payload["authority_level"] == "canonical"
    assert payload["approval_status"] == "awaiting_user_case_approval"
    assert payload["canonical_primary_oracle_fields"] == [
        "expected_target_object_type",
        "expected_target_workflow_family",
        "expected_disposition",
        "expected_workflow_effect",
    ]
    assert payload["secondary_fields_policy"]["expected_semantic_family"] == "optional_secondary_diagnostic_only"
    assert payload["cases"] == []


def test_candidate_review_queue_has_pending_cases() -> None:
    payload = json.loads(CANDIDATE_QUEUE_PATH.read_text(encoding="utf-8"))

    assert payload["authority_level"] == "candidate_only"
    assert payload["approval_status"] == "pending_user_review"
    assert payload["review_unit"] == "per_case_primary_outcome"
    assert payload["required_user_approval_fields"] == [
        "candidate_target_object_type",
        "candidate_target_workflow_family",
        "candidate_disposition",
        "candidate_workflow_effect",
    ]
    assert len(payload["cases"]) >= 5
    for case in payload["cases"]:
        assert case["review_status"] == "pending_user_approval"
        assert case["candidate_target_object_type"] in {"proposal", "meal_thread", "none"}
        assert case["candidate_target_workflow_family"] in {"rescue", "intake"}
        assert case["candidate_disposition"] in {"accept", "reject", "defer", "continue", "open_new_workflow"}
        assert case["candidate_workflow_effect"]


def test_pack_config_maps_modes_to_distinct_authority_lanes() -> None:
    provisional = semantic_eval._pack_config("provisional_smoke")
    official = semantic_eval._pack_config("official_canonical")

    assert provisional["path"] == semantic_eval.PROVISIONAL_PACK_PATH
    assert provisional["pack_mode"] == "provisional_smoke"
    assert official["path"] == semantic_eval.OFFICIAL_PACK_PATH
    assert official["pack_mode"] == "official_canonical"
