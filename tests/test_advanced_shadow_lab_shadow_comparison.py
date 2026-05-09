from __future__ import annotations

import json

from app.advanced_shadow_lab.shadow_comparison import (
    build_advanced_shadow_comparison_artifact,
)


def test_shadow_comparison_aggregates_fixture_dogfood_and_live_diagnostic() -> None:
    artifact = build_advanced_shadow_comparison_artifact(
        fixture_chain_artifact=_fixture_chain(),
        dogfood_replay_artifact=_dogfood_replay(),
        recommendation_copy_live_diagnostic_artifact=_live_diagnostic(),
        rescue_copy_live_diagnostic_artifact=_rescue_live_diagnostic(),
    )
    serialized = json.dumps(artifact, ensure_ascii=False)

    assert artifact["artifact_type"] == "advanced_shadow_comparison_artifact"
    assert artifact["status"] == "pass"
    assert artifact["source_statuses"] == {
        "fixture_chain": "pass",
        "dogfood_replay": "pass",
        "recommendation_copy_live_diagnostic": "pass",
        "rescue_copy_live_diagnostic": "pass",
    }
    assert artifact["surface_status_rows"] == [
        {
            "surface": "terminal_no_send_review_sink",
            "fixture_status": "pass",
            "dogfood_status": "pass",
            "live_status": "not_applicable",
            "finding": "no_drift",
        },
        {
            "surface": "terminal_no_send_control_paths",
            "fixture_status": "pass",
            "dogfood_status": "pass",
            "live_status": "not_applicable",
            "finding": "control_paths_match",
        },
        {
            "surface": "recommendation_prompt_reason_copy",
            "fixture_status": "not_applicable",
            "dogfood_status": "not_applicable",
            "live_status": "pass",
            "finding": "live_diagnostic_passed",
        },
        {
            "surface": "rescue_proposal_copy_posture",
            "fixture_status": "not_applicable",
            "dogfood_status": "not_applicable",
            "live_status": "pass",
            "finding": "live_diagnostic_passed",
        },
    ]
    assert artifact["activation_invariant_summary"]["observed_true_flags"] == []
    assert artifact["live_diagnostic_signals"] == {
        "recommendation_copy_live_diagnostic": {
            "live_invoked": True,
            "live_provider_used": True,
            "provider_mode": "builderspace_live_diagnostic",
            "output_guard_status": "pass",
        },
        "rescue_copy_live_diagnostic": {
            "live_invoked": True,
            "live_provider_used": True,
            "provider_mode": "builderspace_live_diagnostic",
            "output_guard_status": "pass",
        },
    }
    assert artifact["no_send_control_path_comparison"] == {
        "fixture_status": "pass",
        "dogfood_status": "pass",
        "configured_paths_match": True,
        "observed_actions_match": True,
        "next_signal_required_match": True,
        "finding": "control_paths_match",
    }
    assert artifact["mainline_runtime_connected"] is False
    assert artifact["delivery_attempted"] is False
    assert artifact["recommendation_served"] is False
    assert artifact["proactive_sent"] is False
    assert artifact["mutation_changed"] is False
    assert artifact["user_facing_behavior_changed"] is False
    assert "private dogfood wording" not in serialized
    assert "Consider the FamilyMart" not in serialized
    assert "Recover the rest of the week" not in serialized


def test_shadow_comparison_blocks_activation_claim_drift() -> None:
    dogfood = _dogfood_replay()
    dogfood["delivery_attempted"] = True
    live = _live_diagnostic()
    live["recommendation_served"] = True
    rescue_live = _rescue_live_diagnostic()
    rescue_live["proposal_committed"] = True

    artifact = build_advanced_shadow_comparison_artifact(
        fixture_chain_artifact=_fixture_chain(),
        dogfood_replay_artifact=dogfood,
        recommendation_copy_live_diagnostic_artifact=live,
        rescue_copy_live_diagnostic_artifact=rescue_live,
    )

    assert artifact["status"] == "blocked"
    assert artifact["blockers"] == [
        "advanced_shadow_dogfood_replay_artifact.delivery_attempted",
        "advanced_shadow_recommendation_copy_live_diagnostic_artifact.recommendation_served",
        "advanced_shadow_rescue_copy_live_diagnostic_artifact.proposal_committed",
    ]
    assert artifact["activation_invariant_summary"]["observed_true_flags"] == [
        {
            "source": "advanced_shadow_dogfood_replay_artifact",
            "flag": "delivery_attempted",
        },
        {
            "source": "advanced_shadow_recommendation_copy_live_diagnostic_artifact",
            "flag": "recommendation_served",
        },
        {
            "source": "advanced_shadow_rescue_copy_live_diagnostic_artifact",
            "flag": "proposal_committed",
        },
    ]
    assert artifact["delivery_attempted"] is False
    assert artifact["recommendation_served"] is False
    assert artifact["user_facing_behavior_changed"] is False


def test_shadow_comparison_treats_live_guard_block_as_quality_finding() -> None:
    live = _live_diagnostic(status="blocked", output_guard_status="blocked")

    artifact = build_advanced_shadow_comparison_artifact(
        fixture_chain_artifact=_fixture_chain(),
        dogfood_replay_artifact=_dogfood_replay(),
        recommendation_copy_live_diagnostic_artifact=live,
        rescue_copy_live_diagnostic_artifact=_rescue_live_diagnostic(),
    )

    assert artifact["status"] == "blocked"
    assert artifact["source_statuses"]["recommendation_copy_live_diagnostic"] == "blocked"
    assert artifact["surface_status_rows"][2] == {
        "surface": "recommendation_prompt_reason_copy",
        "fixture_status": "not_applicable",
        "dogfood_status": "not_applicable",
        "live_status": "blocked",
        "finding": "live_diagnostic_model_output_blocked",
    }
    assert artifact["blockers"] == [
        "recommendation_copy_live_diagnostic.status_blocked"
    ]


def test_shadow_comparison_treats_rescue_live_guard_block_as_quality_finding() -> None:
    rescue_live = _rescue_live_diagnostic(status="blocked", output_guard_status="blocked")

    artifact = build_advanced_shadow_comparison_artifact(
        fixture_chain_artifact=_fixture_chain(),
        dogfood_replay_artifact=_dogfood_replay(),
        recommendation_copy_live_diagnostic_artifact=_live_diagnostic(),
        rescue_copy_live_diagnostic_artifact=rescue_live,
    )

    assert artifact["status"] == "blocked"
    assert artifact["source_statuses"]["rescue_copy_live_diagnostic"] == "blocked"
    assert artifact["surface_status_rows"][3] == {
        "surface": "rescue_proposal_copy_posture",
        "fixture_status": "not_applicable",
        "dogfood_status": "not_applicable",
        "live_status": "blocked",
        "finding": "live_diagnostic_model_output_blocked",
    }
    assert artifact["blockers"] == ["rescue_copy_live_diagnostic.status_blocked"]


def test_shadow_comparison_blocks_required_source_status_failures() -> None:
    dogfood = _dogfood_replay()
    dogfood["status"] = "blocked"

    artifact = build_advanced_shadow_comparison_artifact(
        fixture_chain_artifact=_fixture_chain(),
        dogfood_replay_artifact=dogfood,
        recommendation_copy_live_diagnostic_artifact=_live_diagnostic(),
        rescue_copy_live_diagnostic_artifact=_rescue_live_diagnostic(),
    )

    assert artifact["status"] == "blocked"
    assert artifact["blockers"] == ["dogfood_replay.status_blocked"]
    assert artifact["source_statuses"]["dogfood_replay"] == "blocked"
    assert artifact["product_readiness_claimed"] is False
    assert artifact["user_facing_behavior_changed"] is False


def test_shadow_comparison_blocks_missing_no_send_control_evidence() -> None:
    fixture = _fixture_chain()
    fixture["terminal_review_sink"] = {"status": "pass", "record_count": 2}

    artifact = build_advanced_shadow_comparison_artifact(
        fixture_chain_artifact=fixture,
        dogfood_replay_artifact=_dogfood_replay(),
        recommendation_copy_live_diagnostic_artifact=_live_diagnostic(),
        rescue_copy_live_diagnostic_artifact=_rescue_live_diagnostic(),
    )

    assert artifact["status"] == "blocked"
    assert artifact["surface_status_rows"][1] == {
        "surface": "terminal_no_send_control_paths",
        "fixture_status": "missing",
        "dogfood_status": "pass",
        "live_status": "not_applicable",
        "finding": "control_path_evidence_missing",
    }
    assert artifact["blockers"] == [
        "terminal_no_send_control_paths.fixture_control_evidence_missing"
    ]
    assert artifact["user_facing_behavior_changed"] is False


def test_shadow_comparison_blocks_no_send_control_variance() -> None:
    dogfood = _dogfood_replay()
    control = dict(dogfood["terminal_review_sink_summary"]["control_path_evidence"])  # type: ignore[index]
    control["configured_paths"] = {"dismiss": True, "snooze": False, "undo": True}
    dogfood["terminal_review_sink_summary"] = {
        "status": "pass",
        "record_count": 2,
        "control_path_evidence": control,
    }

    artifact = build_advanced_shadow_comparison_artifact(
        fixture_chain_artifact=_fixture_chain(),
        dogfood_replay_artifact=dogfood,
        recommendation_copy_live_diagnostic_artifact=_live_diagnostic(),
        rescue_copy_live_diagnostic_artifact=_rescue_live_diagnostic(),
    )

    assert artifact["status"] == "blocked"
    assert artifact["no_send_control_path_comparison"]["finding"] == (
        "control_path_variance"
    )
    assert artifact["blockers"] == [
        "terminal_no_send_control_paths.configured_paths_mismatch"
    ]
    assert artifact["proactive_sent"] is False


def test_shadow_comparison_allows_rescue_live_diagnostic_to_be_absent() -> None:
    artifact = build_advanced_shadow_comparison_artifact(
        fixture_chain_artifact=_fixture_chain(),
        dogfood_replay_artifact=_dogfood_replay(),
        recommendation_copy_live_diagnostic_artifact=_live_diagnostic(),
    )

    assert artifact["status"] == "pass"
    assert artifact["source_statuses"]["rescue_copy_live_diagnostic"] == "not_run"
    assert artifact["surface_status_rows"][3] == {
        "surface": "rescue_proposal_copy_posture",
        "fixture_status": "not_applicable",
        "dogfood_status": "not_applicable",
        "live_status": "not_run",
        "finding": "live_diagnostic_not_run",
    }
    assert artifact["live_diagnostic_signals"]["rescue_copy_live_diagnostic"] == {
        "live_invoked": False,
        "live_provider_used": False,
        "provider_mode": "not_run",
        "output_guard_status": "not_run",
    }
    assert artifact["blockers"] == []


def test_shadow_comparison_blocks_unsupported_source_artifact_type() -> None:
    fixture = _fixture_chain()
    fixture["artifact_type"] = "legacy_fixture_report"

    artifact = build_advanced_shadow_comparison_artifact(
        fixture_chain_artifact=fixture,
        dogfood_replay_artifact=_dogfood_replay(),
        recommendation_copy_live_diagnostic_artifact=_live_diagnostic(),
        rescue_copy_live_diagnostic_artifact=_rescue_live_diagnostic(),
    )

    assert artifact["status"] == "blocked"
    assert artifact["blockers"] == [
        "fixture_chain.unsupported_artifact_type:legacy_fixture_report"
    ]
    assert artifact["source_statuses"]["fixture_chain"] == "unsupported"
    assert artifact["delivery_attempted"] is False
    assert artifact["user_facing_behavior_changed"] is False


def test_shadow_comparison_pairs_baseline_and_advanced_case_artifacts() -> None:
    artifact = build_advanced_shadow_comparison_artifact(
        fixture_chain_artifact=_fixture_chain(),
        dogfood_replay_artifact=_dogfood_replay(),
        recommendation_copy_live_diagnostic_artifact=_live_diagnostic(),
        rescue_copy_live_diagnostic_artifact=_rescue_live_diagnostic(),
        baseline_case_artifacts=[_case_artifact("case-1", "baseline_intake_trace")],
        advanced_case_artifacts=[_case_artifact("case-1", "advanced_shadow_trace")],
    )

    assert artifact["status"] == "pass"
    assert artifact["pairing_summary"] == {
        "status": "pairable",
        "baseline_case_count": 1,
        "advanced_case_count": 1,
        "paired_case_count": 1,
        "schema_gaps": [],
        "activation_violations": [],
    }
    assert artifact["paired_case_rows"] == [
        {
            "case_id": "case-1",
            "baseline_artifact_type": "baseline_intake_trace",
            "advanced_artifact_type": "advanced_shadow_trace",
            "baseline_status": "pass",
            "advanced_status": "pass",
            "finding": "pairable_no_activation_drift",
        }
    ]
    assert artifact["runtime_connected"] is False
    assert artifact["mutation_changed"] is False
    assert artifact["user_facing_behavior_changed"] is False


def test_shadow_comparison_reports_pairing_gaps_without_readiness_claims() -> None:
    advanced = _case_artifact("case-2", "advanced_shadow_trace")
    advanced["delivery_attempted"] = True

    artifact = build_advanced_shadow_comparison_artifact(
        fixture_chain_artifact=_fixture_chain(),
        dogfood_replay_artifact=_dogfood_replay(),
        recommendation_copy_live_diagnostic_artifact=_live_diagnostic(),
        baseline_case_artifacts=[_case_artifact("case-1", "baseline_intake_trace")],
        advanced_case_artifacts=[advanced],
    )

    assert artifact["status"] == "blocked"
    assert artifact["pairing_summary"]["status"] == "not_pairable"
    assert artifact["pairing_summary"]["schema_gaps"] == [
        "case-1.missing_advanced_artifact",
        "case-2.missing_baseline_artifact",
    ]
    assert artifact["pairing_summary"]["activation_violations"] == [
        "case-2.advanced.delivery_attempted"
    ]
    assert artifact["product_readiness_claimed"] is False
    assert artifact["user_facing_behavior_changed"] is False


def _fixture_chain() -> dict[str, object]:
    return {
        "artifact_type": "advanced_shadow_e2e_fixture_chain_artifact",
        "status": "pass",
        "terminal_review_sink": {
            "status": "pass",
            "record_count": 2,
            "control_path_evidence": _control_evidence(),
        },
        "mainline_runtime_connected": False,
        "delivery_attempted": False,
        "scheduler_enabled": False,
        "recommendation_served": False,
        "proactive_sent": False,
        "mutation_changed": False,
        "user_facing_behavior_changed": False,
    }


def _dogfood_replay() -> dict[str, object]:
    return {
        "artifact_type": "advanced_shadow_dogfood_replay_artifact",
        "status": "pass",
        "advanced_fixture_chain_status": "pass",
        "terminal_review_sink_summary": {
            "status": "pass",
            "record_count": 2,
            "control_path_evidence": _control_evidence(include_count=False),
        },
        "dogfood_case_summaries": [
            {"case_id": "dogfood-1", "raw_text": "private dogfood wording"}
        ],
        "mainline_runtime_connected": False,
        "delivery_attempted": False,
        "scheduler_enabled": False,
        "recommendation_served": False,
        "proactive_sent": False,
        "mutation_changed": False,
        "user_facing_behavior_changed": False,
    }


def _live_diagnostic(
    *,
    status: str = "pass",
    output_guard_status: str = "pass",
) -> dict[str, object]:
    return {
        "artifact_type": "advanced_shadow_recommendation_copy_live_diagnostic_artifact",
        "status": status,
        "target_surface": "recommendation_prompt_reason_copy",
        "provider_mode": "builderspace_live_diagnostic",
        "live_invoked": True,
        "live_provider_used": True,
        "output_guard": {"status": output_guard_status},
        "model_output_summary": {
            "draft_prompt_present": True,
            "diagnostic_copy_preview": "Consider the FamilyMart option",
        },
        "mainline_runtime_connected": False,
        "delivery_attempted": False,
        "scheduler_enabled": False,
        "recommendation_served": False,
        "proactive_sent": False,
        "mutation_changed": False,
        "user_facing_behavior_changed": False,
    }


def _rescue_live_diagnostic(
    *,
    status: str = "pass",
    output_guard_status: str = "pass",
) -> dict[str, object]:
    return {
        "artifact_type": "advanced_shadow_rescue_copy_live_diagnostic_artifact",
        "status": status,
        "target_surface": "rescue_proposal_copy_posture",
        "provider_mode": "builderspace_live_diagnostic",
        "live_invoked": True,
        "live_provider_used": True,
        "output_guard": {"status": output_guard_status},
        "model_output_summary": {
            "proposal_headline_present": True,
            "diagnostic_copy_preview": "Recover the rest of the week",
        },
        "mainline_runtime_connected": False,
        "delivery_attempted": False,
        "scheduler_enabled": False,
        "rescue_committed": False,
        "proposal_committed": False,
        "proactive_sent": False,
        "mutation_changed": False,
        "user_facing_behavior_changed": False,
    }


def _case_artifact(case_id: str, artifact_type: str) -> dict[str, object]:
    return {
        "case_id": case_id,
        "artifact_type": artifact_type,
        "status": "pass",
        "observable_output_summary": {"status": "pass"},
        "runtime_connected": False,
        "delivery_attempted": False,
        "recommendation_served": False,
        "rescue_committed": False,
        "proposal_committed": False,
        "mutation_changed": False,
        "user_facing_behavior_changed": False,
        "product_readiness_claimed": False,
    }


def _control_evidence(*, include_count: bool = True) -> dict[str, object]:
    evidence: dict[str, object] = {
        "status": "pass",
        "all_candidates_have_required_controls": True,
        "configured_paths": {"dismiss": True, "snooze": True, "undo": True},
        "interaction_actions_observed": ["dismiss", "snooze"],
        "observed_all_interaction_actions": False,
        "next_signal_required_present": True,
    }
    if include_count:
        evidence["candidate_count"] = 2
    return evidence
