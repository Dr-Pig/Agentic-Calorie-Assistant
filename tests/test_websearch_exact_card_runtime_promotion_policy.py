from __future__ import annotations

from pathlib import Path

from app.nutrition.application.websearch_exact_card_runtime_promotion_policy import (
    build_websearch_exact_card_runtime_promotion_policy,
    evaluate_websearch_exact_card_runtime_promotion_request,
)


def _approval_wall(*, status: str = "blocked_pending_exact_card_approval_policy") -> dict:
    wall_records = [
        {
            "approval_wall_record_id": "wall_exact_card_approval_123",
            "approval_wall_role": "exact_card_runtime_truth_stop_gate",
            "approval_status": "blocked_pending_exact_card_approval_policy",
            "source_review_packet_id": "pkt_exact_card_review_refresh_123",
            "source_plan_candidate_id": (
                "exact_card_candidate_plan:websearch_live_extract_trace_clean"
            ),
            "source_post_extract_status": "clear_for_exact_card_candidate_planning",
            "source_extract_report_status": "trace_only_extract_canary_clean",
            "review_fields_required": {
                "exact_identity_variant_match_required": True,
                "serving_basis_confirmation_required": True,
                "kcal_value_confirmation_required": True,
                "source_license_confirmation_required": True,
            },
            "approval_metadata": {
                "approval_mode": "none",
                "approval_scope": "exact_card_candidate_approval_wall_only",
                "policy_version": "websearch_exact_card_candidate_approval_wall_v1",
                "runtime_truth_allowed": False,
            },
            "runtime_truth_allowed": False,
            "websearch_runtime_truth_allowed": False,
            "packet_ready_truth_allowed": False,
            "promotion_allowed": False,
            "approval_allowed_by_this_wall": False,
            "exact_card_created": False,
            "runtime_mutation_allowed": False,
            "raw_content_included": False,
            "raw_source_rows_included": False,
            "manager_visible_role": "approval_wall_only_not_manager_truth",
            "required_before_runtime_truth": [
                "exact_identity_variant_match",
                "serving_basis_confirmation",
                "kcal_value_confirmation",
                "source_license_confirmation",
                "explicit_exact_card_runtime_promotion_policy",
                "exact_card_runtime_gate",
            ],
        }
    ]
    return {
        "artifact_type": (
            "accurate_intake_websearch_exact_card_candidate_approval_wall_v1"
        ),
        "status": status,
        "classification": "deterministic_exact_card_approval_wall_only",
        "claim_scope": "websearch_exact_card_approval_wall_without_truth_promotion",
        "blockers": ["exact_card_runtime_approval_policy_missing"]
        if status == "blocked_pending_exact_card_approval_policy"
        else ["dirty_input"],
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
        "approval_allowed_by_this_wall": False,
        "approval_wall_records": wall_records
        if status == "blocked_pending_exact_card_approval_policy"
        else [],
        "summary": {
            "review_packet_count": 1
            if status == "blocked_pending_exact_card_approval_policy"
            else 0,
            "approval_wall_record_count": 1
            if status == "blocked_pending_exact_card_approval_policy"
            else 0,
            "runtime_truth_allowed_count": 0,
            "exact_card_created_count": 0,
            "promotion_allowed_count": 0,
        },
        "approval_boundary": {
            "approval_wall_can_create_exact_card": False,
            "approval_wall_can_create_runtime_truth": False,
            "approval_wall_can_mutate_ledger": False,
            "required_before_runtime_truth": (
                "explicit_exact_card_runtime_promotion_policy"
            ),
        },
        "next_required_slice": (
            "define_exact_card_runtime_promotion_policy_or_stop"
            if status == "blocked_pending_exact_card_approval_policy"
            else "inspect_exact_card_approval_wall_blockers"
        ),
    }


def test_exact_card_runtime_promotion_policy_defines_policy_without_truth() -> None:
    artifact = build_websearch_exact_card_runtime_promotion_policy(
        exact_card_approval_wall=_approval_wall()
    )

    assert (
        artifact["artifact_type"]
        == "accurate_intake_websearch_exact_card_runtime_promotion_policy_v1"
    )
    assert artifact["status"] == "policy_defined_no_runtime_truth"
    assert artifact["classification"] == "deterministic_exact_card_runtime_promotion_policy_only"
    assert artifact["runtime_truth_changed"] is False
    assert artifact["mutation_changed"] is False
    assert artifact["runtime_mutation_allowed"] is False
    assert artifact["websearch_runtime_truth_allowed"] is False
    assert artifact["exact_card_created"] is False
    assert artifact["promotion_allowed_by_this_artifact"] is False
    assert artifact["summary"]["approval_wall_record_count"] == 1
    assert artifact["summary"]["runtime_truth_allowed_count"] == 0
    assert artifact["next_required_slice"] == "websearch_exact_card_runtime_promotion_candidate_manifest"


def test_exact_card_runtime_promotion_policy_lists_strict_eligibility() -> None:
    artifact = build_websearch_exact_card_runtime_promotion_policy(
        exact_card_approval_wall=_approval_wall()
    )
    policy = artifact["runtime_promotion_policy"]

    assert policy["eligible_source_classes"] == ["official_brand_chain_page"]
    assert policy["blocked_source_classes"] == [
        "open_food_facts",
        "usda_fallback",
        "old_base_db",
        "dogfood_user_correction",
        "generic_web_snippet",
    ]
    assert policy["required_confirmations"] == [
        "official_or_brand_owned_source",
        "exact_identity_variant_match",
        "serving_basis_confirmation",
        "kcal_value_confirmation",
        "source_license_confirmation",
        "explicit_item_or_batch_approval_id",
        "exact_card_runtime_gate",
    ]
    assert policy["this_artifact_can_create_exact_card"] is False
    assert policy["this_artifact_can_create_runtime_truth"] is False


def test_exact_card_runtime_promotion_policy_blocks_dirty_approval_wall() -> None:
    artifact = build_websearch_exact_card_runtime_promotion_policy(
        exact_card_approval_wall=_approval_wall(status="blocked")
    )

    assert artifact["status"] == "blocked"
    assert "approval_wall_not_pending_policy:blocked" in artifact["blockers"]
    assert artifact["next_required_slice"] == "inspect_exact_card_runtime_promotion_policy_blockers"


def test_exact_card_runtime_promotion_policy_blocks_wall_truth_or_raw_leaks() -> None:
    expected = {
        "runtime_truth_changed": "approval_wall_changed_runtime_truth",
        "runtime_mutation_allowed": "approval_wall_allowed_runtime_mutation",
        "websearch_runtime_truth_allowed": "approval_wall_allowed_websearch_runtime_truth",
        "exact_card_created": "approval_wall_created_exact_card",
        "raw_content_included": "approval_wall_included_raw_content",
        "raw_source_rows_included": "approval_wall_included_raw_source_rows",
    }
    for key, blocker in expected.items():
        wall = _approval_wall()
        wall[key] = 1
        artifact = build_websearch_exact_card_runtime_promotion_policy(
            exact_card_approval_wall=wall
        )
        assert artifact["status"] == "blocked"
        assert blocker in artifact["blockers"]


def test_exact_card_runtime_promotion_policy_blocks_nested_wall_record_leaks() -> None:
    wall = _approval_wall()
    wall["approval_wall_records"][0]["extra"] = {
        "nested": {
            "runtime_truth_allowed": True,
            "raw_source_rows_included": True,
        }
    }

    artifact = build_websearch_exact_card_runtime_promotion_policy(
        exact_card_approval_wall=wall
    )

    assert artifact["status"] == "blocked"
    assert "approval_wall_record_nested_runtime_truth_allowed" in artifact["blockers"]
    assert "approval_wall_record_nested_raw_source_rows_included" in artifact["blockers"]


def test_exact_card_runtime_promotion_request_allows_future_manifest_only() -> None:
    policy = build_websearch_exact_card_runtime_promotion_policy(
        exact_card_approval_wall=_approval_wall()
    )
    result = evaluate_websearch_exact_card_runtime_promotion_request(
        policy_artifact=policy,
        request={
            "candidate_id": "official-drink-card",
            "requested_transition": "review_packet_to_exact_card_manifest_candidate",
            "source_class": "official_brand_chain_page",
            "official_or_brand_owned_source": True,
            "exact_identity_variant_match": True,
            "serving_basis_confirmed": True,
            "kcal_value_confirmed": True,
            "source_license_confirmed": True,
            "approval_id": "batch-policy-1",
        },
    )

    assert result["policy_allows_future_manifest_entry"] is True
    assert result["promotion_allowed_by_policy_artifact"] is False
    assert result["exact_card_created"] is False
    assert result["runtime_truth_allowed"] is False
    assert result["blockers"] == []


def test_exact_card_runtime_promotion_request_blocks_runtime_truth_shortcut() -> None:
    policy = build_websearch_exact_card_runtime_promotion_policy(
        exact_card_approval_wall=_approval_wall()
    )
    result = evaluate_websearch_exact_card_runtime_promotion_request(
        policy_artifact=policy,
        request={
            "candidate_id": "official-drink-card",
            "requested_transition": "create_exact_card_runtime_truth",
            "source_class": "official_brand_chain_page",
            "official_or_brand_owned_source": True,
            "exact_identity_variant_match": True,
            "serving_basis_confirmed": True,
            "kcal_value_confirmed": True,
            "source_license_confirmed": True,
            "approval_id": "batch-policy-1",
        },
    )

    assert result["policy_allows_future_manifest_entry"] is False
    assert "unsupported_transition_for_policy_artifact" in result["blockers"]
    assert result["exact_card_created"] is False


def test_exact_card_runtime_promotion_request_blocks_dirty_request_flags() -> None:
    policy = build_websearch_exact_card_runtime_promotion_policy(
        exact_card_approval_wall=_approval_wall()
    )
    expected = {
        "runtime_truth_changed": "request_changed_runtime_truth",
        "mutation_changed": "request_changed_mutation",
        "live_websearch_used": "request_used_live_websearch",
        "source_live_websearch_used": "request_used_source_live_websearch",
        "live_provider_used": "request_used_live_provider",
        "runtime_web_activation_approved": "request_approved_runtime_web_activation",
        "ready_for_runtime_truth": "request_claimed_ready_for_runtime_truth",
        "ready_for_runtime_mutation": "request_claimed_ready_for_runtime_mutation",
        "readiness_claimed": "request_claimed_readiness",
        "exact_card_created": "request_created_exact_card",
        "runtime_truth_allowed": "request_allowed_runtime_truth",
        "runtime_mutation_allowed": "request_allowed_runtime_mutation",
        "raw_content_included": "request_included_raw_content",
    }
    for key, blocker in expected.items():
        request = {
            "candidate_id": "official-drink-card",
            "requested_transition": "review_packet_to_exact_card_manifest_candidate",
            "source_class": "official_brand_chain_page",
            "official_or_brand_owned_source": True,
            "exact_identity_variant_match": True,
            "serving_basis_confirmed": True,
            "kcal_value_confirmed": True,
            "source_license_confirmed": True,
            "approval_id": "batch-policy-1",
            key: 1,
        }
        result = evaluate_websearch_exact_card_runtime_promotion_request(
            policy_artifact=policy,
            request=request,
        )
        assert result["policy_allows_future_manifest_entry"] is False
        assert blocker in result["blockers"]


def test_exact_card_runtime_promotion_request_blocks_nested_dirty_request_flags() -> None:
    policy = build_websearch_exact_card_runtime_promotion_policy(
        exact_card_approval_wall=_approval_wall()
    )
    result = evaluate_websearch_exact_card_runtime_promotion_request(
        policy_artifact=policy,
        request={
            "candidate_id": "official-drink-card",
            "requested_transition": "review_packet_to_exact_card_manifest_candidate",
            "source_class": "official_brand_chain_page",
            "official_or_brand_owned_source": True,
            "exact_identity_variant_match": True,
            "serving_basis_confirmed": True,
            "kcal_value_confirmed": True,
            "source_license_confirmed": True,
            "approval_id": "batch-policy-1",
            "extra": {
                "nested": {
                    "promotion_allowed": True,
                    "shared_contract_changed": True,
                    "ready_for_runtime_truth": True,
                    "source_live_websearch_used": True,
                }
            },
        },
    )

    assert result["policy_allows_future_manifest_entry"] is False
    assert "request_nested_promotion_allowed" in result["blockers"]
    assert "request_nested_shared_contract_changed" in result["blockers"]
    assert "request_nested_ready_for_runtime_truth" in result["blockers"]
    assert "request_nested_source_live_websearch_used" in result["blockers"]


def test_exact_card_runtime_promotion_request_blocks_dirty_policy_artifact() -> None:
    expected = {
        "mutation_changed": "policy_artifact_changed_mutation",
        "live_websearch_used": "policy_artifact_used_live_websearch",
        "source_live_websearch_used": "policy_artifact_used_source_live_websearch",
        "runtime_mutation_allowed": "policy_artifact_allowed_runtime_mutation",
        "runtime_web_activation_approved": "policy_artifact_approved_runtime_web_activation",
        "runtime_web_activation_recommended": (
            "policy_artifact_recommended_runtime_web_activation"
        ),
        "ready_for_runtime_truth": "policy_artifact_claimed_ready_for_runtime_truth",
        "ready_for_runtime_mutation": "policy_artifact_claimed_ready_for_runtime_mutation",
        "readiness_claimed": "policy_artifact_claimed_readiness",
        "shared_contract_changed": "policy_artifact_changed_shared_contract",
        "websearch_runtime_truth_allowed": "policy_artifact_allowed_websearch_runtime_truth",
    }
    for key, blocker in expected.items():
        policy = build_websearch_exact_card_runtime_promotion_policy(
            exact_card_approval_wall=_approval_wall()
        )
        policy[key] = 1
        result = evaluate_websearch_exact_card_runtime_promotion_request(
            policy_artifact=policy,
            request={
                "candidate_id": "official-drink-card",
                "requested_transition": "review_packet_to_exact_card_manifest_candidate",
                "source_class": "official_brand_chain_page",
                "official_or_brand_owned_source": True,
                "exact_identity_variant_match": True,
                "serving_basis_confirmed": True,
                "kcal_value_confirmed": True,
                "source_license_confirmed": True,
                "approval_id": "batch-policy-1",
            },
        )
        assert result["policy_allows_future_manifest_entry"] is False
        assert blocker in result["blockers"]


def test_exact_card_runtime_promotion_request_blocks_nested_dirty_policy_artifact() -> None:
    policy = build_websearch_exact_card_runtime_promotion_policy(
        exact_card_approval_wall=_approval_wall()
    )
    policy["runtime_promotion_policy"]["extra"] = {
        "runtime_truth_allowed": True,
        "raw_source_rows_included": True,
        "mutation_changed": True,
        "readiness_claimed": True,
    }
    result = evaluate_websearch_exact_card_runtime_promotion_request(
        policy_artifact=policy,
        request={
            "candidate_id": "official-drink-card",
            "requested_transition": "review_packet_to_exact_card_manifest_candidate",
            "source_class": "official_brand_chain_page",
            "official_or_brand_owned_source": True,
            "exact_identity_variant_match": True,
            "serving_basis_confirmed": True,
            "kcal_value_confirmed": True,
            "source_license_confirmed": True,
            "approval_id": "batch-policy-1",
        },
    )

    assert result["policy_allows_future_manifest_entry"] is False
    assert "policy_artifact_nested_runtime_truth_allowed" in result["blockers"]
    assert "policy_artifact_nested_raw_source_rows_included" in result["blockers"]
    assert "policy_artifact_nested_mutation_changed" in result["blockers"]
    assert "policy_artifact_nested_readiness_claimed" in result["blockers"]


def test_exact_card_runtime_promotion_request_blocks_unsupported_sources() -> None:
    policy = build_websearch_exact_card_runtime_promotion_policy(
        exact_card_approval_wall=_approval_wall()
    )
    result = evaluate_websearch_exact_card_runtime_promotion_request(
        policy_artifact=policy,
        request={
            "candidate_id": "off-card",
            "requested_transition": "review_packet_to_exact_card_manifest_candidate",
            "source_class": "open_food_facts",
            "official_or_brand_owned_source": True,
            "exact_identity_variant_match": True,
            "serving_basis_confirmed": True,
            "kcal_value_confirmed": True,
            "source_license_confirmed": True,
            "approval_id": "batch-policy-1",
        },
    )

    assert result["policy_allows_future_manifest_entry"] is False
    assert "source_class_not_allowed_for_exact_card_runtime_policy" in result["blockers"]


def test_exact_card_runtime_promotion_policy_script_roundtrip(tmp_path: Path) -> None:
    from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact
    from scripts.build_accurate_intake_websearch_exact_card_runtime_promotion_policy import (
        main,
    )

    wall_path = tmp_path / "approval_wall.json"
    output = tmp_path / "runtime_policy.json"
    write_json_artifact(wall_path, _approval_wall())

    assert main(["--exact-card-approval-wall", str(wall_path), "--output", str(output)]) == 0

    artifact = read_json_artifact(output)
    assert (
        artifact["artifact_type"]
        == "accurate_intake_websearch_exact_card_runtime_promotion_policy_v1"
    )
    assert artifact["status"] == "policy_defined_no_runtime_truth"


def test_exact_card_runtime_promotion_policy_has_no_live_or_shared_contract_imports() -> None:
    source_paths = [
        Path("app/nutrition/application/websearch_exact_card_runtime_promotion_policy.py"),
        Path("scripts/build_accurate_intake_websearch_exact_card_runtime_promotion_policy.py"),
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
