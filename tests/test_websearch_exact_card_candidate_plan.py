from __future__ import annotations

from pathlib import Path

from app.nutrition.application.websearch_exact_card_candidate_plan import (
    build_websearch_exact_card_candidate_plan,
)


def _post_extract_status(*, status: str = "clear_for_exact_card_candidate_planning") -> dict:
    return {
        "artifact_type": "accurate_intake_websearch_post_extract_lane_status_packet_v1",
        "status": status,
        "classification": "deterministic_websearch_post_extract_status_only",
        "claim_scope": "websearch_post_extract_lane_status_without_runtime_activation",
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
        "upstream_gate": {
            "status": status,
            "blocked": status != "clear_for_exact_card_candidate_planning",
            "blockers": [],
            "next_required_slice": (
                "websearch_exact_card_candidate_planning_after_live_extract"
                if status == "clear_for_exact_card_candidate_planning"
                else "inspect_websearch_live_extract_canary_blockers"
            ),
        },
        "summary": {
            "extract_report_status": "trace_only_extract_canary_clean",
            "extract_report_selected_option": "trace_only_extract_canary_continues",
            "extract_port_used": True,
            "live_extract_used": True,
            "extract_report_case_count": 1,
            "extract_report_failure_count": 0,
            "runtime_activation_ready_count": 0,
            "runtime_truth_allowed_count": 0,
        },
        "next_required_slices": [
            "websearch_exact_card_candidate_planning_after_live_extract"
            if status == "clear_for_exact_card_candidate_planning"
            else "inspect_websearch_live_extract_canary_blockers"
        ],
    }


def test_exact_card_candidate_plan_is_review_only_after_clean_extract_status() -> None:
    artifact = build_websearch_exact_card_candidate_plan(
        post_extract_status_packet=_post_extract_status()
    )

    assert artifact["artifact_type"] == "accurate_intake_websearch_exact_card_candidate_plan_v1"
    assert artifact["status"] == "pass"
    assert artifact["classification"] == "deterministic_exact_card_candidate_plan_only"
    assert artifact["runtime_truth_changed"] is False
    assert artifact["runtime_mutation_allowed"] is False
    assert artifact["websearch_runtime_truth_allowed"] is False
    assert artifact["exact_card_created"] is False
    assert artifact["readiness_claimed"] is False
    assert artifact["summary"]["planned_candidate_count"] == 1
    assert artifact["summary"]["runtime_truth_allowed_count"] == 0
    assert artifact["summary"]["exact_card_created_count"] == 0
    assert artifact["next_required_slice"] == "websearch_exact_card_review_packet_refresh"


def test_exact_card_candidate_plan_preserves_approval_boundary() -> None:
    artifact = build_websearch_exact_card_candidate_plan(
        post_extract_status_packet=_post_extract_status()
    )
    candidate = artifact["planned_candidates"][0]

    assert candidate["candidate_role"] == "exact_card_candidate_plan"
    assert candidate["promotion_status"] == "review_candidate_only"
    assert candidate["runtime_truth_allowed"] is False
    assert candidate["websearch_runtime_truth_allowed"] is False
    assert candidate["packet_ready_truth_allowed"] is False
    assert candidate["promotion_allowed"] is False
    assert candidate["exact_card_created"] is False
    assert candidate["approval_metadata"]["approval_mode"] == "none"
    assert candidate["approval_metadata"]["runtime_truth_allowed"] is False
    assert candidate["required_before_runtime_truth"] == [
        "exact_identity_variant_match",
        "serving_basis_confirmation",
        "kcal_value_confirmation",
        "source_license_confirmation",
        "explicit_exact_card_approval",
        "exact_card_runtime_gate",
    ]


def test_exact_card_candidate_plan_blocks_without_clear_post_extract_status() -> None:
    artifact = build_websearch_exact_card_candidate_plan(
        post_extract_status_packet=_post_extract_status(status="blocked_on_live_extract_report")
    )

    assert artifact["status"] == "blocked"
    assert "post_extract_status_not_clear:blocked_on_live_extract_report" in artifact["blockers"]
    assert artifact["planned_candidates"] == []
    assert artifact["next_required_slice"] == "inspect_websearch_exact_card_candidate_plan_blockers"


def test_exact_card_candidate_plan_blocks_status_truth_or_shared_contract_overclaims() -> None:
    expected = {
        "runtime_truth_changed": "post_extract_status_changed_runtime_truth",
        "mutation_changed": "post_extract_status_changed_mutation",
        "runtime_mutation_allowed": "post_extract_status_allowed_runtime_mutation",
        "websearch_runtime_truth_allowed": "post_extract_status_allowed_websearch_runtime_truth",
        "runtime_web_activation_approved": "post_extract_status_approved_runtime_web_activation",
        "runtime_web_activation_recommended": (
            "post_extract_status_recommended_runtime_web_activation"
        ),
        "ready_for_runtime_truth": "post_extract_status_claimed_ready_for_runtime_truth",
        "ready_for_runtime_mutation": (
            "post_extract_status_claimed_ready_for_runtime_mutation"
        ),
        "readiness_claimed": "post_extract_status_claimed_readiness",
        "shared_contract_changed": "post_extract_status_changed_shared_contract",
        "manager_context_changed": "post_extract_status_changed_manager_context",
        "packetizer_format_changed": "post_extract_status_changed_packetizer_format",
        "basket_semantics_changed": "post_extract_status_changed_basket_semantics",
        "live_provider_used": "post_extract_status_used_live_provider",
        "live_websearch_used": "post_extract_status_used_live_websearch",
        "source_live_websearch_used": "post_extract_status_used_source_live_websearch",
        "product_loop_activated": "post_extract_status_activated_product_loop",
        "product_loop_integration_claimed": (
            "post_extract_status_claimed_product_loop_integration"
        ),
        "ce_activated": "post_extract_status_activated_context_engineering",
        "context_engineering_changed": "post_extract_status_changed_context_engineering",
        "webshell_activated": "post_extract_status_activated_webshell",
        "webshell_changed": "post_extract_status_changed_webshell",
    }
    for key, blocker in expected.items():
        status = _post_extract_status()
        status[key] = True
        artifact = build_websearch_exact_card_candidate_plan(
            post_extract_status_packet=status
        )
        assert artifact["status"] == "blocked"
        assert blocker in artifact["blockers"]
        assert artifact["planned_candidates"] == []


def test_exact_card_candidate_plan_blocks_upstream_gate_or_next_slice_drift() -> None:
    status = _post_extract_status()
    status["upstream_gate"]["blocked"] = True
    status["upstream_gate"]["blockers"] = ["extract_report_changed_runtime_truth"]

    artifact = build_websearch_exact_card_candidate_plan(post_extract_status_packet=status)

    assert artifact["status"] == "blocked"
    assert "post_extract_upstream_gate_blocked" in artifact["blockers"]
    assert (
        "post_extract_upstream_gate:extract_report_changed_runtime_truth"
        in artifact["blockers"]
    )

    status = _post_extract_status()
    status["next_required_slices"] = ["runtime_exact_card_truth_promotion"]
    artifact = build_websearch_exact_card_candidate_plan(post_extract_status_packet=status)
    assert artifact["status"] == "blocked"
    assert "post_extract_next_slice_not_exact_card_candidate_planning" in artifact["blockers"]

    status = _post_extract_status()
    status["upstream_gate"]["next_required_slice"] = "runtime_exact_card_truth_promotion"
    artifact = build_websearch_exact_card_candidate_plan(post_extract_status_packet=status)
    assert artifact["status"] == "blocked"
    assert "post_extract_upstream_gate_next_slice_drift" in artifact["blockers"]


def test_exact_card_candidate_plan_rejects_unexpected_status_artifact_type() -> None:
    try:
        build_websearch_exact_card_candidate_plan(
            post_extract_status_packet={"artifact_type": "wrong"}
        )
    except ValueError as exc:
        assert "unsupported_exact_card_candidate_plan_status_packet" in str(exc)
    else:
        raise AssertionError("unexpected status packet type must fail")


def test_exact_card_candidate_plan_script_roundtrip(tmp_path: Path) -> None:
    from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact
    from scripts.build_accurate_intake_websearch_exact_card_candidate_plan import main

    status_path = tmp_path / "status.json"
    output = tmp_path / "plan.json"
    write_json_artifact(status_path, _post_extract_status())

    assert main(["--post-extract-status-packet", str(status_path), "--output", str(output)]) == 0

    artifact = read_json_artifact(output)
    assert artifact["artifact_type"] == "accurate_intake_websearch_exact_card_candidate_plan_v1"
    assert artifact["status"] == "pass"


def test_exact_card_candidate_plan_has_no_live_or_shared_contract_imports() -> None:
    source_paths = [
        Path("app/nutrition/application/websearch_exact_card_candidate_plan.py"),
        Path("scripts/build_accurate_intake_websearch_exact_card_candidate_plan.py"),
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
