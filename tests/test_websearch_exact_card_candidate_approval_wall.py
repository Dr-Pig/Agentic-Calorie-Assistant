from __future__ import annotations

from pathlib import Path

from app.nutrition.application.websearch_exact_card_candidate_approval_wall import (
    build_websearch_exact_card_candidate_approval_wall,
)


def _review_packet_refresh(*, status: str = "pass") -> dict:
    review_packets = [
        {
            "packet_id": "pkt_exact_card_review_refresh_123",
            "packet_type": "ExactCardReviewPacketRefresh",
            "packet_role": "review_only_exact_card_candidate",
            "truth_level": "review_candidate",
            "source_type": "websearch_exact_card_candidate_plan",
            "source_plan_candidate_id": (
                "exact_card_candidate_plan:websearch_live_extract_trace_clean"
            ),
            "source_post_extract_status": "clear_for_exact_card_candidate_planning",
            "source_extract_report_status": "trace_only_extract_canary_clean",
            "evidence_basis": {
                "extract_report_case_count": 1,
                "extract_report_failure_count": 0,
                "extract_port_used": True,
                "live_extract_used": True,
            },
            "review_fields": {
                "exact_identity_variant_match_required": True,
                "serving_basis_confirmation_required": True,
                "kcal_value_confirmation_required": True,
                "source_license_confirmation_required": True,
            },
            "approval_checklist": {
                "identity_variant_confirmation_required": True,
                "serving_basis_confirmation_required": True,
                "kcal_value_confirmation_required": True,
                "source_license_confirmation_required": True,
                "explicit_exact_card_approval_required": True,
            },
            "approval_metadata": {
                "approval_mode": "none",
                "approval_scope": "exact_card_review_packet_refresh_only",
                "policy_version": "websearch_exact_card_review_packet_refresh_v1",
                "runtime_truth_allowed": False,
            },
            "approval_allowed_by_this_packet": False,
            "runtime_truth_allowed": False,
            "websearch_runtime_truth_allowed": False,
            "packet_ready_truth_allowed": False,
            "promotion_allowed": False,
            "exact_card_created": False,
            "runtime_mutation_allowed": False,
            "raw_content_included": False,
            "raw_source_rows_included": False,
            "manager_visible_role": "review_packet_only_not_manager_truth",
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
    return {
        "artifact_type": (
            "accurate_intake_websearch_exact_card_review_packet_refresh_v1"
        ),
        "status": status,
        "classification": "deterministic_exact_card_review_packet_refresh_only",
        "claim_scope": (
            "websearch_exact_card_review_packet_refresh_without_truth_promotion"
        ),
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
        "review_packets": review_packets if status == "pass" else [],
        "summary": {
            "review_packet_count": 1 if status == "pass" else 0,
            "runtime_truth_allowed_count": 0,
            "exact_card_created_count": 0,
            "approval_allowed_count": 0,
        },
        "next_required_slice": (
            "websearch_exact_card_candidate_approval_wall"
            if status == "pass"
            else "inspect_websearch_exact_card_review_packet_refresh_blockers"
        ),
    }


def test_exact_card_approval_wall_blocks_pending_runtime_policy() -> None:
    artifact = build_websearch_exact_card_candidate_approval_wall(
        exact_card_review_packet_refresh=_review_packet_refresh()
    )

    assert (
        artifact["artifact_type"]
        == "accurate_intake_websearch_exact_card_candidate_approval_wall_v1"
    )
    assert artifact["status"] == "blocked_pending_exact_card_approval_policy"
    assert artifact["classification"] == "deterministic_exact_card_approval_wall_only"
    assert artifact["runtime_truth_changed"] is False
    assert artifact["mutation_changed"] is False
    assert artifact["runtime_mutation_allowed"] is False
    assert artifact["websearch_runtime_truth_allowed"] is False
    assert artifact["exact_card_created"] is False
    assert artifact["approval_allowed_by_this_wall"] is False
    assert artifact["summary"]["review_packet_count"] == 1
    assert artifact["summary"]["approval_wall_record_count"] == 1
    assert artifact["summary"]["runtime_truth_allowed_count"] == 0
    assert artifact["blockers"] == ["exact_card_runtime_approval_policy_missing"]
    assert artifact["next_required_slice"] == "define_exact_card_runtime_promotion_policy_or_stop"


def test_exact_card_approval_wall_records_required_policy_inputs_without_truth() -> None:
    artifact = build_websearch_exact_card_candidate_approval_wall(
        exact_card_review_packet_refresh=_review_packet_refresh()
    )
    record = artifact["approval_wall_records"][0]

    assert record["approval_wall_role"] == "exact_card_runtime_truth_stop_gate"
    assert record["source_review_packet_id"] == "pkt_exact_card_review_refresh_123"
    assert record["approval_status"] == "blocked_pending_exact_card_approval_policy"
    assert record["runtime_truth_allowed"] is False
    assert record["websearch_runtime_truth_allowed"] is False
    assert record["packet_ready_truth_allowed"] is False
    assert record["promotion_allowed"] is False
    assert record["exact_card_created"] is False
    assert record["runtime_mutation_allowed"] is False
    assert record["raw_content_included"] is False
    assert record["raw_source_rows_included"] is False
    assert record["required_before_runtime_truth"] == [
        "exact_identity_variant_match",
        "serving_basis_confirmation",
        "kcal_value_confirmation",
        "source_license_confirmation",
        "explicit_exact_card_runtime_promotion_policy",
        "exact_card_runtime_gate",
    ]


def test_exact_card_approval_wall_blocks_dirty_refresh_artifact() -> None:
    artifact = build_websearch_exact_card_candidate_approval_wall(
        exact_card_review_packet_refresh=_review_packet_refresh(status="blocked")
    )

    assert artifact["status"] == "blocked"
    assert "review_packet_refresh_not_pass:blocked" in artifact["blockers"]
    assert artifact["approval_wall_records"] == []
    assert artifact["next_required_slice"] == "inspect_exact_card_approval_wall_blockers"


def test_exact_card_approval_wall_blocks_malformed_review_packet_entries() -> None:
    refresh = _review_packet_refresh()
    refresh["review_packets"].append("not-a-packet")
    artifact = build_websearch_exact_card_candidate_approval_wall(
        exact_card_review_packet_refresh=refresh
    )

    assert artifact["status"] == "blocked"
    assert "review_refresh_review_packet_malformed" in artifact["blockers"]
    assert artifact["approval_wall_records"] == []


def test_exact_card_approval_wall_blocks_refresh_overclaims() -> None:
    expected = {
        "runtime_truth_changed": "review_refresh_changed_runtime_truth",
        "mutation_changed": "review_refresh_changed_mutation",
        "runtime_mutation_allowed": "review_refresh_allowed_runtime_mutation",
        "websearch_runtime_truth_allowed": "review_refresh_allowed_websearch_runtime_truth",
        "runtime_web_activation_approved": "review_refresh_approved_runtime_web_activation",
        "runtime_web_activation_recommended": (
            "review_refresh_recommended_runtime_web_activation"
        ),
        "readiness_claimed": "review_refresh_claimed_readiness",
        "shared_contract_changed": "review_refresh_changed_shared_contract",
        "manager_context_changed": "review_refresh_changed_manager_context",
        "packetizer_format_changed": "review_refresh_changed_packetizer_format",
        "live_provider_used": "review_refresh_used_live_provider",
        "live_websearch_used": "review_refresh_used_live_websearch",
        "exact_card_created": "review_refresh_created_exact_card",
        "approval_allowed_by_this_packet": "review_refresh_allowed_approval",
        "approval_allowed_by_this_wall": "review_refresh_allowed_wall_approval",
    }
    for key, blocker in expected.items():
        refresh = _review_packet_refresh()
        refresh[key] = True
        artifact = build_websearch_exact_card_candidate_approval_wall(
            exact_card_review_packet_refresh=refresh
        )
        assert artifact["status"] == "blocked"
        assert blocker in artifact["blockers"]
        assert artifact["approval_wall_records"] == []


def test_exact_card_approval_wall_blocks_truthy_or_top_level_raw_refresh_leaks() -> None:
    expected = {
        "runtime_truth_changed": "review_refresh_changed_runtime_truth",
        "raw_content_included": "review_refresh_included_raw_content",
        "raw_source_rows_included": "review_refresh_included_raw_source_rows",
    }
    for key, blocker in expected.items():
        refresh = _review_packet_refresh()
        refresh[key] = 1
        artifact = build_websearch_exact_card_candidate_approval_wall(
            exact_card_review_packet_refresh=refresh
        )
        assert artifact["status"] == "blocked"
        assert blocker in artifact["blockers"]
        assert artifact["approval_wall_records"] == []


def test_exact_card_approval_wall_blocks_review_packet_truth_or_raw_leaks() -> None:
    expected = {
        "approval_allowed_by_this_packet": "review_packet_allowed_approval",
        "runtime_truth_allowed": "review_packet_allowed_runtime_truth",
        "websearch_runtime_truth_allowed": "review_packet_allowed_websearch_runtime_truth",
        "packet_ready_truth_allowed": "review_packet_allowed_packet_ready_truth",
        "promotion_allowed": "review_packet_allowed_promotion",
        "exact_card_created": "review_packet_created_exact_card",
        "runtime_mutation_allowed": "review_packet_allowed_runtime_mutation",
        "raw_content_included": "review_packet_included_raw_content",
        "raw_source_rows_included": "review_packet_included_raw_source_rows",
    }
    for key, blocker in expected.items():
        refresh = _review_packet_refresh()
        refresh["review_packets"][0][key] = True
        artifact = build_websearch_exact_card_candidate_approval_wall(
            exact_card_review_packet_refresh=refresh
        )
        assert artifact["status"] == "blocked"
        assert blocker in artifact["blockers"]
        assert artifact["approval_wall_records"] == []


def test_exact_card_approval_wall_blocks_nested_packet_authority_leaks() -> None:
    nested_cases = (
        (
            ("approval_metadata", "runtime_truth_allowed"),
            "review_packet_approval_allowed_runtime_truth",
        ),
        (
            ("approval_metadata", "promotion_allowed"),
            "review_packet_approval_promotion_allowed",
        ),
        (
            ("approval_checklist", "approval_allowed_by_this_packet"),
            "review_packet_checklist_approval_allowed_by_this_packet",
        ),
        (
            ("review_fields", "runtime_truth_allowed"),
            "review_packet_review_fields_runtime_truth_allowed",
        ),
        (
            ("evidence_basis", "packet_ready_truth_allowed"),
            "review_packet_evidence_basis_packet_ready_truth_allowed",
        ),
        (
            ("evidence_basis", "raw_content_included"),
            "review_packet_evidence_basis_raw_content_included",
        ),
        (
            ("review_fields", "shared_contract_changed"),
            "review_packet_review_fields_shared_contract_changed",
        ),
    )
    for (section, key), blocker in nested_cases:
        refresh = _review_packet_refresh()
        refresh["review_packets"][0][section][key] = True
        artifact = build_websearch_exact_card_candidate_approval_wall(
            exact_card_review_packet_refresh=refresh
        )
        assert artifact["status"] == "blocked"
        assert blocker in artifact["blockers"]
        assert artifact["approval_wall_records"] == []


def test_exact_card_approval_wall_blocks_truthy_non_bool_nested_leaks() -> None:
    nested_cases = (
        (
            ("approval_metadata", "promotion_allowed"),
            "review_packet_approval_promotion_allowed",
        ),
        (
            ("evidence_basis", "runtime_truth_allowed"),
            "review_packet_evidence_basis_runtime_truth_allowed",
        ),
    )
    for (section, key), blocker in nested_cases:
        refresh = _review_packet_refresh()
        refresh["review_packets"][0][section][key] = 1
        artifact = build_websearch_exact_card_candidate_approval_wall(
            exact_card_review_packet_refresh=refresh
        )
        assert artifact["status"] == "blocked"
        assert blocker in artifact["blockers"]
        assert artifact["approval_wall_records"] == []


def test_exact_card_approval_wall_blocks_arbitrary_nested_authority_leaks() -> None:
    refresh = _review_packet_refresh()
    refresh["review_packets"][0]["extra"] = {
        "nested": {
            "runtime_truth_allowed": True,
            "raw_source_rows_included": True,
        }
    }
    artifact = build_websearch_exact_card_candidate_approval_wall(
        exact_card_review_packet_refresh=refresh
    )

    assert artifact["status"] == "blocked"
    assert "review_packet_nested_runtime_truth_allowed" in artifact["blockers"]
    assert "review_packet_nested_raw_source_rows_included" in artifact["blockers"]
    assert artifact["approval_wall_records"] == []


def test_exact_card_approval_wall_blocks_refresh_level_nested_authority_leaks() -> None:
    refresh = _review_packet_refresh()
    refresh["extra"] = {
        "nested": {
            "runtime_truth_allowed": True,
            "raw_source_rows_included": True,
        }
    }
    artifact = build_websearch_exact_card_candidate_approval_wall(
        exact_card_review_packet_refresh=refresh
    )

    assert artifact["status"] == "blocked"
    assert "review_refresh_nested_runtime_truth_allowed" in artifact["blockers"]
    assert "review_refresh_nested_raw_source_rows_included" in artifact["blockers"]
    assert artifact["approval_wall_records"] == []


def test_exact_card_approval_wall_blocks_next_slice_drift_or_summary_leaks() -> None:
    refresh = _review_packet_refresh()
    refresh["next_required_slice"] = "runtime_exact_card_truth_promotion"
    artifact = build_websearch_exact_card_candidate_approval_wall(
        exact_card_review_packet_refresh=refresh
    )
    assert artifact["status"] == "blocked"
    assert "review_refresh_next_slice_not_approval_wall" in artifact["blockers"]

    refresh = _review_packet_refresh()
    refresh["summary"]["runtime_truth_allowed_count"] = 1
    artifact = build_websearch_exact_card_candidate_approval_wall(
        exact_card_review_packet_refresh=refresh
    )
    assert artifact["status"] == "blocked"
    assert "review_refresh_runtime_truth_allowed_count_nonzero" in artifact["blockers"]


def test_exact_card_approval_wall_rejects_unexpected_refresh_artifact_type() -> None:
    try:
        build_websearch_exact_card_candidate_approval_wall(
            exact_card_review_packet_refresh={"artifact_type": "wrong"}
        )
    except ValueError as exc:
        assert "unsupported_exact_card_approval_wall_review_refresh" in str(exc)
    else:
        raise AssertionError("unexpected review refresh type must fail")


def test_exact_card_approval_wall_script_roundtrip(tmp_path: Path) -> None:
    from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact
    from scripts.build_accurate_intake_websearch_exact_card_candidate_approval_wall import (
        main,
    )

    refresh_path = tmp_path / "review_refresh.json"
    output = tmp_path / "approval_wall.json"
    write_json_artifact(refresh_path, _review_packet_refresh())

    assert main(["--exact-card-review-packet-refresh", str(refresh_path), "--output", str(output)]) == 0

    artifact = read_json_artifact(output)
    assert (
        artifact["artifact_type"]
        == "accurate_intake_websearch_exact_card_candidate_approval_wall_v1"
    )
    assert artifact["status"] == "blocked_pending_exact_card_approval_policy"


def test_exact_card_approval_wall_has_no_live_or_shared_contract_imports() -> None:
    source_paths = [
        Path("app/nutrition/application/websearch_exact_card_candidate_approval_wall.py"),
        Path("scripts/build_accurate_intake_websearch_exact_card_candidate_approval_wall.py"),
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
