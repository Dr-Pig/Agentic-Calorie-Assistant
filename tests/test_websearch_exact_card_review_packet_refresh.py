from __future__ import annotations

from pathlib import Path

from app.nutrition.application.websearch_exact_card_review_packet_refresh import (
    build_websearch_exact_card_review_packet_refresh,
)


def _candidate_plan(*, status: str = "pass") -> dict:
    return {
        "artifact_type": "accurate_intake_websearch_exact_card_candidate_plan_v1",
        "status": status,
        "classification": "deterministic_exact_card_candidate_plan_only",
        "claim_scope": "websearch_exact_card_candidate_plan_without_truth_promotion",
        "runtime_truth_changed": False,
        "mutation_changed": False,
        "runtime_mutation_allowed": False,
        "websearch_runtime_truth_allowed": False,
        "runtime_web_activation_approved": False,
        "runtime_web_activation_recommended": False,
        "manager_context_changed": False,
        "packetizer_format_changed": False,
        "shared_contract_changed": False,
        "live_provider_used": False,
        "live_websearch_used": False,
        "readiness_claimed": False,
        "exact_card_created": False,
        "planned_candidates": [
            {
                "candidate_id": "exact_card_candidate_plan:websearch_live_extract_trace_clean",
                "candidate_role": "exact_card_candidate_plan",
                "promotion_status": "review_candidate_only",
                "source_type": "websearch_live_extract_trace",
                "source_post_extract_status": "clear_for_exact_card_candidate_planning",
                "source_extract_report_status": "trace_only_extract_canary_clean",
                "source_extract_report_selected_option": "trace_only_extract_canary_continues",
                "evidence_basis": {
                    "extract_report_case_count": 1,
                    "extract_report_failure_count": 0,
                    "extract_port_used": True,
                    "live_extract_used": True,
                },
                "planning_scope": {
                    "allowed_next_artifact": "exact_card_review_packet_refresh",
                    "allowed_record_type": "review_candidate_only",
                    "runtime_exact_card_creation_allowed": False,
                },
                "approval_metadata": {
                    "approval_mode": "none",
                    "approval_scope": "exact_card_candidate_plan_only",
                    "policy_version": "websearch_exact_card_candidate_plan_v1",
                    "runtime_truth_allowed": False,
                },
                "runtime_truth_allowed": False,
                "websearch_runtime_truth_allowed": False,
                "packet_ready_truth_allowed": False,
                "promotion_allowed": False,
                "exact_card_created": False,
                "runtime_mutation_allowed": False,
                "manager_visible_role": "review_plan_only_not_manager_truth",
                "required_before_runtime_truth": [
                    "exact_identity_variant_match",
                    "serving_basis_confirmation",
                    "kcal_value_confirmation",
                    "source_license_confirmation",
                    "explicit_exact_card_approval",
                    "exact_card_runtime_gate",
                ],
            }
        ]
        if status == "pass"
        else [],
        "summary": {
            "planned_candidate_count": 1 if status == "pass" else 0,
            "runtime_truth_allowed_count": 0,
            "exact_card_created_count": 0,
            "promotion_allowed_count": 0,
        },
        "approval_boundary": {
            "planning_artifact_can_create_exact_card": False,
            "planning_artifact_can_create_runtime_truth": False,
            "planning_artifact_can_mutate_ledger": False,
            "required_approval_mode_before_runtime_truth": "explicit_exact_card_approval",
        },
        "next_required_slice": (
            "websearch_exact_card_review_packet_refresh"
            if status == "pass"
            else "inspect_websearch_exact_card_candidate_plan_blockers"
        ),
    }


def test_exact_card_review_packet_refresh_is_review_only() -> None:
    artifact = build_websearch_exact_card_review_packet_refresh(
        exact_card_candidate_plan=_candidate_plan()
    )

    assert artifact["artifact_type"] == "accurate_intake_websearch_exact_card_review_packet_refresh_v1"
    assert artifact["status"] == "pass"
    assert artifact["classification"] == "deterministic_exact_card_review_packet_refresh_only"
    assert artifact["runtime_truth_changed"] is False
    assert artifact["runtime_mutation_allowed"] is False
    assert artifact["websearch_runtime_truth_allowed"] is False
    assert artifact["exact_card_created"] is False
    assert artifact["readiness_claimed"] is False
    assert artifact["summary"]["review_packet_count"] == 1
    assert artifact["summary"]["runtime_truth_allowed_count"] == 0
    assert artifact["summary"]["exact_card_created_count"] == 0
    assert artifact["summary"]["approval_allowed_count"] == 0
    assert artifact["next_required_slice"] == "websearch_exact_card_candidate_approval_wall"


def test_exact_card_review_packet_refresh_preserves_review_fields_without_truth() -> None:
    artifact = build_websearch_exact_card_review_packet_refresh(
        exact_card_candidate_plan=_candidate_plan()
    )
    packet = artifact["review_packets"][0]

    assert packet["packet_type"] == "ExactCardReviewPacketRefresh"
    assert packet["truth_level"] == "review_candidate"
    assert packet["packet_role"] == "review_only_exact_card_candidate"
    assert packet["source_plan_candidate_id"] == (
        "exact_card_candidate_plan:websearch_live_extract_trace_clean"
    )
    assert set(packet["evidence_basis"]) == {
        "extract_report_case_count",
        "extract_report_failure_count",
        "extract_port_used",
        "live_extract_used",
    }
    assert packet["approval_checklist"]["explicit_exact_card_approval_required"] is True
    assert packet["approval_allowed_by_this_packet"] is False
    assert packet["runtime_truth_allowed"] is False
    assert packet["websearch_runtime_truth_allowed"] is False
    assert packet["packet_ready_truth_allowed"] is False
    assert packet["promotion_allowed"] is False
    assert packet["exact_card_created"] is False
    assert packet["runtime_mutation_allowed"] is False
    assert packet["raw_content_included"] is False
    assert packet["raw_source_rows_included"] is False


def test_exact_card_review_packet_refresh_blocks_without_clear_candidate_plan() -> None:
    artifact = build_websearch_exact_card_review_packet_refresh(
        exact_card_candidate_plan=_candidate_plan(status="blocked")
    )

    assert artifact["status"] == "blocked"
    assert "candidate_plan_not_pass:blocked" in artifact["blockers"]
    assert artifact["review_packets"] == []
    assert artifact["next_required_slice"] == "inspect_websearch_exact_card_review_packet_refresh_blockers"


def test_exact_card_review_packet_refresh_blocks_plan_truth_or_shared_contract_overclaims() -> None:
    expected = {
        "runtime_truth_changed": "candidate_plan_changed_runtime_truth",
        "mutation_changed": "candidate_plan_changed_mutation",
        "runtime_mutation_allowed": "candidate_plan_allowed_runtime_mutation",
        "websearch_runtime_truth_allowed": "candidate_plan_allowed_websearch_runtime_truth",
        "runtime_web_activation_approved": "candidate_plan_approved_runtime_web_activation",
        "runtime_web_activation_recommended": "candidate_plan_recommended_runtime_web_activation",
        "packet_ready_truth_allowed": "candidate_plan_allowed_packet_ready_truth",
        "promotion_allowed": "candidate_plan_allowed_promotion",
        "approval_allowed_by_this_packet": "candidate_plan_allowed_approval",
        "readiness_claimed": "candidate_plan_claimed_readiness",
        "shared_contract_changed": "candidate_plan_changed_shared_contract",
        "manager_context_changed": "candidate_plan_changed_manager_context",
        "packetizer_format_changed": "candidate_plan_changed_packetizer_format",
        "live_provider_used": "candidate_plan_used_live_provider",
        "live_websearch_used": "candidate_plan_used_live_websearch",
        "exact_card_created": "candidate_plan_created_exact_card",
    }
    for key, blocker in expected.items():
        plan = _candidate_plan()
        plan[key] = True
        artifact = build_websearch_exact_card_review_packet_refresh(
            exact_card_candidate_plan=plan
        )
        assert artifact["status"] == "blocked"
        assert blocker in artifact["blockers"]
        assert artifact["review_packets"] == []


def test_exact_card_review_packet_refresh_blocks_candidate_truth_leak() -> None:
    expected = {
        "runtime_truth_allowed": "planned_candidate_allowed_runtime_truth",
        "websearch_runtime_truth_allowed": "planned_candidate_allowed_websearch_runtime_truth",
        "packet_ready_truth_allowed": "planned_candidate_allowed_packet_ready_truth",
        "promotion_allowed": "planned_candidate_allowed_promotion",
        "exact_card_created": "planned_candidate_created_exact_card",
        "runtime_mutation_allowed": "planned_candidate_allowed_runtime_mutation",
    }
    for key, blocker in expected.items():
        plan = _candidate_plan()
        plan["planned_candidates"][0][key] = True
        artifact = build_websearch_exact_card_review_packet_refresh(
            exact_card_candidate_plan=plan
        )
        assert artifact["status"] == "blocked"
        assert blocker in artifact["blockers"]
        assert artifact["review_packets"] == []


def test_exact_card_review_packet_refresh_blocks_nested_evidence_basis_leaks() -> None:
    expected = {
        "raw_content": "planned_candidate_evidence_basis_unexpected_keys",
        "raw_source_rows": "planned_candidate_evidence_basis_unexpected_keys",
        "runtime_truth_allowed": "planned_candidate_evidence_basis_unexpected_keys",
        "websearch_runtime_truth_allowed": "planned_candidate_evidence_basis_unexpected_keys",
        "packet_ready_truth_allowed": "planned_candidate_evidence_basis_unexpected_keys",
        "promotion_allowed": "planned_candidate_evidence_basis_unexpected_keys",
        "approval_allowed_by_this_packet": "planned_candidate_evidence_basis_unexpected_keys",
        "exact_card_created": "planned_candidate_evidence_basis_unexpected_keys",
        "runtime_mutation_allowed": "planned_candidate_evidence_basis_unexpected_keys",
    }
    for key, blocker in expected.items():
        plan = _candidate_plan()
        plan["planned_candidates"][0]["evidence_basis"][key] = True
        artifact = build_websearch_exact_card_review_packet_refresh(
            exact_card_candidate_plan=plan
        )
        assert artifact["status"] == "blocked"
        assert blocker in artifact["blockers"]
        assert artifact["review_packets"] == []


def test_exact_card_review_packet_refresh_blocks_nested_scope_and_approval_leaks() -> None:
    nested_cases = (
        (
            ("planning_scope", "runtime_exact_card_creation_allowed"),
            "planned_candidate_scope_allowed_exact_card_creation",
        ),
        (
            ("planning_scope", "promotion_allowed"),
            "planned_candidate_scope_promotion_allowed",
        ),
        (
            ("planning_scope", "runtime_mutation_allowed"),
            "planned_candidate_scope_runtime_mutation_allowed",
        ),
        (
            ("approval_metadata", "promotion_allowed"),
            "planned_candidate_approval_promotion_allowed",
        ),
        (
            ("approval_metadata", "exact_card_created"),
            "planned_candidate_approval_exact_card_created",
        ),
        (
            ("approval_metadata", "runtime_mutation_allowed"),
            "planned_candidate_approval_runtime_mutation_allowed",
        ),
    )
    for (section, key), blocker in nested_cases:
        plan = _candidate_plan()
        plan["planned_candidates"][0][section][key] = True
        artifact = build_websearch_exact_card_review_packet_refresh(
            exact_card_candidate_plan=plan
        )
        assert artifact["status"] == "blocked"
        assert blocker in artifact["blockers"]
        assert artifact["review_packets"] == []


def test_exact_card_review_packet_refresh_blocks_next_slice_or_approval_boundary_drift() -> None:
    plan = _candidate_plan()
    plan["next_required_slice"] = "runtime_exact_card_truth_promotion"
    artifact = build_websearch_exact_card_review_packet_refresh(
        exact_card_candidate_plan=plan
    )
    assert artifact["status"] == "blocked"
    assert "candidate_plan_next_slice_not_review_packet_refresh" in artifact["blockers"]

    plan = _candidate_plan()
    plan["approval_boundary"]["planning_artifact_can_create_exact_card"] = True
    artifact = build_websearch_exact_card_review_packet_refresh(
        exact_card_candidate_plan=plan
    )
    assert artifact["status"] == "blocked"
    assert "candidate_plan_boundary_allowed_exact_card_creation" in artifact["blockers"]


def test_exact_card_review_packet_refresh_rejects_unexpected_plan_artifact_type() -> None:
    try:
        build_websearch_exact_card_review_packet_refresh(
            exact_card_candidate_plan={"artifact_type": "wrong"}
        )
    except ValueError as exc:
        assert "unsupported_exact_card_review_refresh_candidate_plan" in str(exc)
    else:
        raise AssertionError("unexpected candidate plan type must fail")


def test_exact_card_review_packet_refresh_script_roundtrip(tmp_path: Path) -> None:
    from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact
    from scripts.build_accurate_intake_websearch_exact_card_review_packet_refresh import (
        main,
    )

    plan_path = tmp_path / "plan.json"
    output = tmp_path / "review_refresh.json"
    write_json_artifact(plan_path, _candidate_plan())

    assert main(["--exact-card-candidate-plan", str(plan_path), "--output", str(output)]) == 0

    artifact = read_json_artifact(output)
    assert (
        artifact["artifact_type"]
        == "accurate_intake_websearch_exact_card_review_packet_refresh_v1"
    )
    assert artifact["status"] == "pass"


def test_exact_card_review_packet_refresh_has_no_live_or_shared_contract_imports() -> None:
    source_paths = [
        Path("app/nutrition/application/websearch_exact_card_review_packet_refresh.py"),
        Path("scripts/build_accurate_intake_websearch_exact_card_review_packet_refresh.py"),
    ]
    forbidden = [
        "Tavily",
        "tavily",
        "OpenAI",
        "openai",
        "BuilderSpaceAdapter",
        "requests.",
        "httpx.",
        "ManagerContextPacket",
        "NutritionEvidenceStorePort",
        "PacketReadyAnchor",
    ]
    for path in source_paths:
        source = path.read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in source
