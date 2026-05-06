from __future__ import annotations

import hashlib
import json
from pathlib import Path

from app.nutrition.application.grokfast_websearch_packet_smoke import (
    build_fixture_grokfast_websearch_manager_outputs,
    build_grokfast_websearch_packet_diagnostic,
)
from app.nutrition.application.tool_evidence_result import build_tool_evidence_result
from app.nutrition.application.websearch_candidate_packet_smoke import (
    build_websearch_candidate_packet_smoke,
)
from app.nutrition.application.websearch_live_diagnostic_report import (
    build_websearch_live_diagnostic_report,
)
from app.nutrition.application.websearch_manager_packet_smoke import (
    build_websearch_manager_packet_projection,
)


def _manager_packet_artifact() -> dict:
    packet_artifact = build_websearch_candidate_packet_smoke()
    packets = tuple(case["websearch_candidate_packet"] for case in packet_artifact["cases"])
    tool_result = build_tool_evidence_result(
        tool_name="search_official_nutrition",
        tool_call_id="tool-call-websearch-live-report",
        evidence_packets=packets,
        trace_context={
            "packet_artifact_type": packet_artifact["artifact_type"],
            "packet_claim_scope": packet_artifact["claim_scope"],
            "live_websearch_used": False,
        },
    )
    return build_websearch_manager_packet_projection(
        tool_evidence_artifact={
            "artifact_type": "accurate_intake_websearch_tool_evidence_result_smoke",
            "tool_evidence_result": tool_result,
        }
    )


def _clear_preflight_ref() -> dict[str, object]:
    preflight = _clear_preflight_artifact()
    return {
        "preflight_ref_source": "run_accurate_intake_grokfast_websearch_packet_smoke",
        "artifact_type": "accurate_intake_websearch_live_extract_preflight_v1",
        "status": "pass",
        "ready_for_live_extract_diagnostic": True,
        "ready_for_runtime_truth": False,
        "review_packet_authorized": True,
        "review_packet_count": 1,
        "case_matrix_fixed_required_cases": True,
        "case_matrix_case_count": 6,
        "case_matrix_negative_case_count": 4,
        "case_matrix_modifier_guard_cases": 1,
        "case_matrix_live_provider_invoked": False,
        "case_matrix_websearch_invoked": False,
        "preflight_artifact_digest_algorithm": "sha256",
        "preflight_artifact_digest_scope": "semantic_preflight_without_generated_at_utc",
        "preflight_artifact_digest": _semantic_preflight_digest(preflight),
    }


def _clear_preflight_artifact() -> dict[str, object]:
    return {
        "artifact_type": "accurate_intake_websearch_live_extract_preflight_v1",
        "artifact_schema_version": "1.0",
        "generated_at_utc": "2026-05-06T00:00:00Z",
        "track": "FDB",
        "classification": "deterministic_live_extract_preflight_only",
        "claim_scope": "websearch_live_extract_diagnostic_preflight_without_live_call",
        "status": "pass",
        "blockers": [],
        "live_websearch_used": False,
        "live_extract_used": False,
        "live_provider_used": False,
        "runtime_truth_changed": False,
        "runtime_mutation_allowed": False,
        "manager_context_changed": False,
        "packetizer_format_changed": False,
        "readiness_claimed": False,
        "ready_for_live_extract_diagnostic": True,
        "ready_for_runtime_truth": False,
        "diagnostic_contract": {
            "live_call_allowed_by_this_artifact": False,
            "requires_explicit_allow_live_flag": True,
            "cache_required": True,
            "raw_content_allowed_in_manager_context": False,
            "ledger_mutation_allowed": False,
            "exact_card_creation_allowed": False,
        },
        "review_packet_refs": [
            {
                "packet_id": "pkt_exact_card_review_123456789abc",
                "source_url": "https://milksha.example/menu/pearl-black-tea-latte",
                "canonical_name": "Milksha pearl black tea latte",
                "matched_name": "Milksha pearl black tea latte",
                "packet_digest": "abc123def4567890",
            }
        ],
        "summary": {
            "review_packet_count": 1,
            "ready_for_live_extract_diagnostic_count": 1,
            "ready_for_runtime_truth_count": 0,
            "case_matrix_case_count": 6,
            "case_matrix_fixed_required_cases": True,
            "case_matrix_negative_case_count": 4,
            "case_matrix_modifier_guard_cases": 1,
            "case_matrix_live_provider_invoked": False,
            "case_matrix_websearch_invoked": False,
        },
        "next_required_slice": "grokfast_websearch_packet_live_diagnostic",
        "non_claims": [
            "no_live_websearch_call",
            "no_live_extract_call",
            "no_live_provider_call",
            "no_websearch_runtime_truth",
            "no_exact_card_truth_promotion",
            "no_runtime_mutation",
            "no_readiness_claim",
        ],
    }


def _semantic_preflight_digest(preflight: dict[str, object]) -> str:
    payload = {
        key: value
        for key, value in preflight.items()
        if key != "generated_at_utc"
    }
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def test_websearch_live_diagnostic_report_blocks_expansion_after_provider_contract_failure() -> None:
    diagnostic = {
        "artifact_type": "accurate_intake_grokfast_websearch_packet_smoke",
        "status": "diagnostic_fail",
        "live_provider_used": True,
        "live_websearch_used": False,
        "summary": {
            "case_count": 4,
            "pass_count": 0,
            "fail_count": 4,
            "failure_families": [
                "provider_response_error",
                "websearch_candidate_not_used",
            ],
        },
        "cases": [
            {
                "case_id": "pkt_web_search_milksha_exact",
                "status": "fail",
                "failure_families": ["websearch_candidate_not_used"],
                "provider_trace": {
                    "trace_summary": {
                        "failure_family": "manager_output_contract_violation",
                        "failing_component": "builderspace_runtime_contract.validate_manager_payload",
                        "transport_attempt_count": 2,
                        "parse_attempt_count": 2,
                    }
                },
            }
        ],
    }

    report = build_websearch_live_diagnostic_report(
        diagnostic_artifact=diagnostic,
        preflight_artifact=_clear_preflight_artifact(),
    )

    assert report["artifact_type"] == "accurate_intake_websearch_live_diagnostic_report"
    assert report["seam_status"] == "provider_contract_blocked"
    assert report["provider_contract_blocked"] is True
    assert report["can_expand_websearch_candidate_pipeline"] is False
    assert report["should_run_websearch_live_tool_loop"] is False
    assert report["next_recommended_slice"] == "narrow_grokfast_websearch_manager_contract_probe"
    assert report["readiness_claimed"] is False
    assert report["runtime_truth_changed"] is False


def test_websearch_live_diagnostic_report_distinguishes_post_contract_candidate_boundary_failures() -> None:
    diagnostic = {
        "artifact_type": "accurate_intake_grokfast_websearch_packet_smoke",
        "status": "diagnostic_fail",
        "live_provider_used": True,
        "live_websearch_used": False,
        "summary": {
            "case_count": 4,
            "pass_count": 0,
            "fail_count": 4,
            "failure_families": [
                "provider_response_error",
                "websearch_candidate_not_used",
                "websearch_weak_candidate_not_rejected",
            ],
        },
        "cases": [
            {
                "case_id": "pkt_web_search_milksha_exact",
                "status": "fail",
                "failure_families": ["websearch_candidate_not_used"],
                "provider_trace": {
                    "trace_summary": {
                        "structured_output_transport_mode": "json_schema",
                        "decision_transport_mode": "synthetic_tool_transport",
                        "decision_transport_attempted": True,
                        "decision_transport_contract_breach": False,
                        "schema_name": "founder_live_manager_contract",
                        "schema_version": "v1",
                    }
                },
            },
            {
                "case_id": "pkt_web_search_third_party_weak",
                "status": "fail",
                "failure_families": [
                    "provider_response_error",
                    "websearch_weak_candidate_not_rejected",
                ],
                "provider_trace": {
                    "failure_family": "provider_response_error",
                    "trace_summary": {
                        "failing_component": "builderspace_adapter.complete_with_trace",
                        "structured_output_transport_mode": "json_schema",
                        "decision_transport_mode": "synthetic_tool_transport",
                        "decision_transport_attempted": True,
                        "decision_transport_contract_breach": False,
                        "schema_name": "founder_live_manager_contract",
                        "schema_version": "v1",
                    },
                },
            },
        ],
    }

    report = build_websearch_live_diagnostic_report(
        diagnostic_artifact=diagnostic,
        preflight_artifact=_clear_preflight_artifact(),
    )

    assert report["seam_status"] == "candidate_boundary_blocked"
    assert report["provider_contract_blocked"] is False
    assert report["provider_runtime_residual_blocked"] is True
    assert report["candidate_boundary_blocked"] is True
    assert report["can_expand_websearch_candidate_pipeline"] is False
    assert report["next_recommended_slice"] == "narrow_websearch_packet_boundary_or_prompt_probe"
    assert report["contract_transport"]["healthy"] is True
    assert report["contract_transport"]["healthy_case_count"] == 2
    assert report["contract_transport"]["observed_decision_transport_modes"] == [
        "synthetic_tool_transport"
    ]
    assert report["contract_transport"]["observed_schema_names"] == [
        "founder_live_manager_contract"
    ]


def test_websearch_live_diagnostic_report_recognizes_b1_pass2_json_schema_transport() -> None:
    diagnostic = {
        "artifact_type": "accurate_intake_grokfast_websearch_packet_smoke",
        "status": "pass",
        "live_provider_used": True,
        "live_websearch_used": False,
        "preflight_ref": _clear_preflight_ref(),
        "summary": {
            "case_count": 1,
            "pass_count": 1,
            "fail_count": 0,
            "failure_families": [],
        },
        "cases": [
            {
                "packet_id": "pkt_exact_card_review",
                "status": "pass",
                "failure_families": [],
                "provider_trace": {
                    "structured_output_transport_attempted": True,
                    "structured_output_transport_mode": "json_schema",
                    "structured_output_transport_accepted": True,
                    "schema_name": "phase_b1_pass2_manager_contract",
                    "decision_transport_attempted": False,
                    "decision_transport_contract_breach": False,
                    "parse_contract_status": "strict_json",
                },
            }
        ],
    }

    report = build_websearch_live_diagnostic_report(
        diagnostic_artifact=diagnostic,
        preflight_artifact=_clear_preflight_artifact(),
    )

    assert report["seam_status"] == "live_diagnostic_pass"
    assert report["can_expand_websearch_candidate_pipeline"] is True
    assert report["preflight_evidence_required"] is True
    assert report["preflight_evidence_healthy"] is True
    assert report["preflight_evidence"]["preflight_artifact_digest_verified"] is True
    assert report["preflight_evidence"]["preflight_artifact_digest_algorithm"] == "sha256"
    assert report["preflight_evidence"]["preflight_artifact_digest_scope"] == (
        "semantic_preflight_without_generated_at_utc"
    )
    assert report["preflight_evidence"]["review_packet_authorized"] is True
    assert report["preflight_evidence"]["case_matrix_fixed_required_cases"] is True
    assert report["contract_transport"]["healthy"] is True
    assert report["contract_transport"]["structured_output_transport_attempted"] is True
    assert report["contract_transport"]["structured_output_healthy_case_count"] == 1
    assert report["next_recommended_slice"] == "inspect_websearch_status_packet"
    assert report["contract_transport"]["observed_structured_output_transport_modes"] == [
        "json_schema"
    ]
    assert report["contract_transport"]["observed_schema_names"] == [
        "phase_b1_pass2_manager_contract"
    ]


def test_websearch_live_diagnostic_report_derives_verified_preflight_evidence_from_artifact() -> None:
    preflight_artifact = _clear_preflight_artifact()
    preflight_ref = _clear_preflight_ref()
    preflight_ref.update(
        {
            "status": "blocked",
            "ready_for_live_extract_diagnostic": False,
            "ready_for_runtime_truth": True,
            "review_packet_authorized": False,
            "review_packet_count": 999,
            "case_matrix_fixed_required_cases": False,
            "case_matrix_case_count": 999,
            "case_matrix_negative_case_count": 999,
            "case_matrix_modifier_guard_cases": 999,
            "case_matrix_live_provider_invoked": True,
            "case_matrix_websearch_invoked": True,
        }
    )
    diagnostic = {
        "artifact_type": "accurate_intake_grokfast_websearch_packet_smoke",
        "status": "pass",
        "live_provider_used": True,
        "live_websearch_used": False,
        "preflight_ref": preflight_ref,
        "summary": {
            "case_count": 1,
            "pass_count": 1,
            "fail_count": 0,
            "failure_families": [],
        },
        "cases": [
            {
                "packet_id": "pkt_exact_card_review",
                "status": "pass",
                "failure_families": [],
                "provider_trace": {
                    "structured_output_transport_attempted": True,
                    "structured_output_transport_mode": "json_schema",
                    "structured_output_transport_accepted": True,
                    "schema_name": "phase_b1_pass2_manager_contract",
                    "decision_transport_contract_breach": False,
                },
            }
        ],
    }

    report = build_websearch_live_diagnostic_report(
        diagnostic_artifact=diagnostic,
        preflight_artifact=preflight_artifact,
    )

    assert report["seam_status"] == "live_diagnostic_pass"
    assert report["preflight_evidence_healthy"] is True
    assert report["preflight_evidence"]["status"] == "pass"
    assert report["preflight_evidence"]["ready_for_live_extract_diagnostic"] is True
    assert report["preflight_evidence"]["ready_for_runtime_truth"] is False
    assert report["preflight_evidence"]["review_packet_authorized"] is True
    assert report["preflight_evidence"]["review_packet_count"] == 1
    assert report["preflight_evidence"]["case_matrix_fixed_required_cases"] is True
    assert report["preflight_evidence"]["case_matrix_case_count"] == 6
    assert report["preflight_evidence"]["case_matrix_negative_case_count"] == 4
    assert report["preflight_evidence"]["case_matrix_modifier_guard_cases"] == 1
    assert report["preflight_evidence"]["case_matrix_live_provider_invoked"] is False
    assert report["preflight_evidence"]["case_matrix_websearch_invoked"] is False


def test_websearch_live_diagnostic_report_blocks_pass_without_verified_preflight_digest() -> None:
    diagnostic = {
        "artifact_type": "accurate_intake_grokfast_websearch_packet_smoke",
        "status": "pass",
        "live_provider_used": True,
        "live_websearch_used": False,
        "preflight_ref": _clear_preflight_ref(),
        "summary": {
            "case_count": 1,
            "pass_count": 1,
            "fail_count": 0,
            "failure_families": [],
        },
        "cases": [
            {
                "packet_id": "pkt_exact_card_review",
                "status": "pass",
                "failure_families": [],
                "provider_trace": {
                    "structured_output_transport_attempted": True,
                    "structured_output_transport_mode": "json_schema",
                    "structured_output_transport_accepted": True,
                    "schema_name": "phase_b1_pass2_manager_contract",
                    "decision_transport_contract_breach": False,
                },
            }
        ],
    }

    report = build_websearch_live_diagnostic_report(diagnostic_artifact=diagnostic)

    assert report["seam_status"] == "preflight_evidence_missing"
    assert report["can_expand_websearch_candidate_pipeline"] is False
    assert report["preflight_evidence_healthy"] is False
    assert report["preflight_evidence"]["preflight_artifact_digest_verified"] is False
    assert report["next_recommended_slice"] == "rerun_with_clear_websearch_live_extract_preflight"


def test_websearch_live_diagnostic_report_blocks_mismatched_preflight_digest() -> None:
    diagnostic = {
        "artifact_type": "accurate_intake_grokfast_websearch_packet_smoke",
        "status": "pass",
        "live_provider_used": True,
        "live_websearch_used": False,
        "preflight_ref": _clear_preflight_ref(),
        "summary": {
            "case_count": 1,
            "pass_count": 1,
            "fail_count": 0,
            "failure_families": [],
        },
        "cases": [
            {
                "packet_id": "pkt_exact_card_review",
                "status": "pass",
                "failure_families": [],
                "provider_trace": {
                    "structured_output_transport_attempted": True,
                    "structured_output_transport_mode": "json_schema",
                    "structured_output_transport_accepted": True,
                    "schema_name": "phase_b1_pass2_manager_contract",
                    "decision_transport_contract_breach": False,
                },
            }
        ],
    }
    drifted_preflight = _clear_preflight_artifact()
    drifted_preflight["review_packet_refs"][0]["packet_digest"] = "drifted"

    report = build_websearch_live_diagnostic_report(
        diagnostic_artifact=diagnostic,
        preflight_artifact=drifted_preflight,
    )

    assert report["seam_status"] == "preflight_evidence_missing"
    assert report["can_expand_websearch_candidate_pipeline"] is False
    assert report["preflight_evidence_healthy"] is False
    assert report["preflight_evidence"]["preflight_artifact_digest_verified"] is False


def test_websearch_live_diagnostic_report_fail_closes_malformed_preflight_artifact() -> None:
    malformed_preflight = _clear_preflight_artifact()
    malformed_preflight["summary"]["review_packet_count"] = "not-an-int"
    preflight_ref = _clear_preflight_ref()
    preflight_ref["preflight_artifact_digest"] = _semantic_preflight_digest(
        malformed_preflight
    )
    diagnostic = {
        "artifact_type": "accurate_intake_grokfast_websearch_packet_smoke",
        "status": "pass",
        "live_provider_used": True,
        "live_websearch_used": False,
        "preflight_ref": preflight_ref,
        "summary": {
            "case_count": 1,
            "pass_count": 1,
            "fail_count": 0,
            "failure_families": [],
        },
        "cases": [
            {
                "packet_id": "pkt_exact_card_review",
                "status": "pass",
                "failure_families": [],
                "provider_trace": {
                    "structured_output_transport_attempted": True,
                    "structured_output_transport_mode": "json_schema",
                    "structured_output_transport_accepted": True,
                    "schema_name": "phase_b1_pass2_manager_contract",
                    "decision_transport_contract_breach": False,
                },
            }
        ],
    }

    report = build_websearch_live_diagnostic_report(
        diagnostic_artifact=diagnostic,
        preflight_artifact=malformed_preflight,
    )

    assert report["seam_status"] == "preflight_evidence_missing"
    assert report["can_expand_websearch_candidate_pipeline"] is False
    assert report["preflight_evidence_healthy"] is False
    assert report["preflight_evidence"]["preflight_artifact_digest_verified"] is True
    assert report["preflight_evidence"]["preflight_artifact_integrity_clear"] is False


def test_websearch_live_diagnostic_report_blocks_pass_without_clear_preflight_ref() -> None:
    diagnostic = {
        "artifact_type": "accurate_intake_grokfast_websearch_packet_smoke",
        "status": "pass",
        "live_provider_used": True,
        "live_websearch_used": False,
        "summary": {
            "case_count": 1,
            "pass_count": 1,
            "fail_count": 0,
            "failure_families": [],
        },
        "cases": [
            {
                "packet_id": "pkt_exact_card_review",
                "status": "pass",
                "failure_families": [],
                "provider_trace": {
                    "structured_output_transport_attempted": True,
                    "structured_output_transport_mode": "json_schema",
                    "structured_output_transport_accepted": True,
                    "schema_name": "phase_b1_pass2_manager_contract",
                    "decision_transport_contract_breach": False,
                },
            }
        ],
    }

    report = build_websearch_live_diagnostic_report(diagnostic_artifact=diagnostic)

    assert report["seam_status"] == "preflight_evidence_missing"
    assert report["can_expand_websearch_candidate_pipeline"] is False
    assert report["preflight_evidence_required"] is True
    assert report["preflight_evidence_healthy"] is False
    assert report["preflight_evidence"]["artifact_type"] == "missing_preflight_ref"
    assert report["next_recommended_slice"] == "rerun_with_clear_websearch_live_extract_preflight"


def test_websearch_live_diagnostic_report_blocks_forged_preflight_ref_without_runner_authorization() -> None:
    preflight_ref = _clear_preflight_ref()
    preflight_ref.pop("preflight_ref_source")
    preflight_ref.pop("review_packet_authorized")
    preflight_ref["case_matrix_case_count"] = 999

    diagnostic = {
        "artifact_type": "accurate_intake_grokfast_websearch_packet_smoke",
        "status": "pass",
        "live_provider_used": True,
        "live_websearch_used": False,
        "preflight_ref": preflight_ref,
        "summary": {
            "case_count": 1,
            "pass_count": 1,
            "fail_count": 0,
            "failure_families": [],
        },
        "cases": [],
    }

    report = build_websearch_live_diagnostic_report(diagnostic_artifact=diagnostic)

    assert report["seam_status"] == "preflight_evidence_missing"
    assert report["can_expand_websearch_candidate_pipeline"] is False
    assert report["preflight_evidence"]["preflight_ref_source"] == (
        "unsupported_preflight_ref_source"
    )
    assert report["preflight_evidence"]["review_packet_authorized"] is False
    assert report["preflight_evidence"]["case_matrix_case_count"] == 999


def test_websearch_live_diagnostic_report_blocks_live_websearch_expansion_guidance() -> None:
    diagnostic = {
        "artifact_type": "accurate_intake_grokfast_websearch_packet_smoke",
        "status": "pass",
        "live_provider_used": True,
        "live_websearch_used": True,
        "preflight_ref": _clear_preflight_ref(),
        "summary": {
            "case_count": 1,
            "pass_count": 1,
            "fail_count": 0,
            "failure_families": [],
        },
        "cases": [],
    }

    report = build_websearch_live_diagnostic_report(diagnostic_artifact=diagnostic)

    assert report["seam_status"] == "unexpected_live_websearch_used"
    assert report["can_expand_websearch_candidate_pipeline"] is False
    assert report["should_run_websearch_live_tool_loop"] is False
    assert report["next_recommended_slice"] == "inspect_unexpected_websearch_live_tool_loop"
    assert "no_live_provider_call" not in report["non_claims"]


def test_websearch_live_diagnostic_report_blocks_live_websearch_even_without_provider_flag() -> None:
    diagnostic = {
        "artifact_type": "accurate_intake_grokfast_websearch_packet_smoke",
        "status": "pass",
        "live_provider_used": False,
        "live_websearch_used": True,
        "summary": {
            "case_count": 1,
            "pass_count": 1,
            "fail_count": 0,
            "failure_families": [],
        },
        "cases": [],
    }

    report = build_websearch_live_diagnostic_report(diagnostic_artifact=diagnostic)

    assert report["seam_status"] == "unexpected_live_websearch_used"
    assert report["can_expand_websearch_candidate_pipeline"] is False
    assert report["next_recommended_slice"] == "inspect_unexpected_websearch_live_tool_loop"


def test_websearch_live_diagnostic_report_sanitizes_malformed_preflight_ref() -> None:
    diagnostic = {
        "artifact_type": "accurate_intake_grokfast_websearch_packet_smoke",
        "status": "pass",
        "live_provider_used": True,
        "live_websearch_used": False,
        "preflight_ref": {
            "preflight_ref_source": "raw_response_excerpt forbidden",
            "artifact_type": "raw_response_excerpt forbidden",
            "status": "pass",
            "ready_for_live_extract_diagnostic": True,
            "ready_for_runtime_truth": False,
            "review_packet_authorized": True,
            "review_packet_count": "raw_response_excerpt",
            "case_matrix_fixed_required_cases": True,
            "case_matrix_case_count": "provider_trace",
            "case_matrix_negative_case_count": "raw_response_excerpt",
            "case_matrix_modifier_guard_cases": "forbidden",
            "case_matrix_live_provider_invoked": "raw_response_excerpt",
            "case_matrix_websearch_invoked": "provider_trace",
        },
        "summary": {
            "case_count": 1,
            "pass_count": 1,
            "fail_count": 0,
            "failure_families": [],
        },
        "cases": [],
    }

    report = build_websearch_live_diagnostic_report(diagnostic_artifact=diagnostic)
    serialized = str(report)

    assert report["seam_status"] == "preflight_evidence_missing"
    assert report["preflight_evidence"]["artifact_type"] == "unsupported_preflight_artifact"
    assert report["preflight_evidence"]["preflight_ref_source"] == (
        "unsupported_preflight_ref_source"
    )
    assert report["preflight_evidence"]["review_packet_count"] == 0
    assert report["preflight_evidence"]["case_matrix_case_count"] == 0
    assert report["preflight_evidence"]["case_matrix_live_provider_invoked"] is True
    assert "raw_response_excerpt forbidden" not in serialized
    assert "forbidden" not in serialized


def test_websearch_live_diagnostic_report_treats_fixture_pass_as_live_not_checked() -> None:
    packet_artifact = _manager_packet_artifact()
    diagnostic = build_grokfast_websearch_packet_diagnostic(
        packet_artifact=packet_artifact,
        manager_outputs=build_fixture_grokfast_websearch_manager_outputs(
            packet_artifact=packet_artifact
        ),
        live_provider_used=False,
    )

    report = build_websearch_live_diagnostic_report(diagnostic_artifact=diagnostic)

    assert report["source_status"] == "pass"
    assert report["source_live_provider_used"] is False
    assert report["seam_status"] == "fixture_only_live_not_checked"
    assert report["can_expand_websearch_candidate_pipeline"] is False
    assert report["next_recommended_slice"] == "run_explicit_grokfast_websearch_packet_live_diagnostic"
    assert "no_live_provider_call" in report["non_claims"]


def test_websearch_live_diagnostic_report_sanitizes_raw_payloads_from_source_artifact() -> None:
    diagnostic = {
        "artifact_type": "accurate_intake_grokfast_websearch_packet_smoke",
        "status": "diagnostic_fail",
        "live_provider_used": True,
        "live_websearch_used": False,
        "summary": {"case_count": 1, "pass_count": 0, "fail_count": 1, "failure_families": []},
        "cases": [
            {
                "case_id": "case",
                "status": "fail",
                "failure_families": ["websearch_truth_shortcut"],
                "manager_output": {
                    "exact_card_truth": {"kcal": 123},
                    "item_results": [{"food_name": "invented", "likely_kcal": 123}],
                },
                "provider_trace": {
                    "trace_summary": {
                        "failure_family": "manager_output_contract_violation",
                    },
                    "raw_response_excerpt": "snippet exact_card_truth likely_kcal",
                    "parsed_object": {"runtime_truth_allowed": True},
                },
            }
        ],
    }

    report = build_websearch_live_diagnostic_report(diagnostic_artifact=diagnostic)

    assert not _contains_key(report, "manager_output")
    assert not _contains_key(report, "raw_response_excerpt")
    assert not _contains_key(report, "parsed_object")
    assert not _contains_key(report, "food_name")
    assert not _contains_key(report, "likely_kcal")
    assert not _contains_key(report, "runtime_truth_allowed")
    assert "invented" not in _scalar_values(report)
    assert "websearch_truth_shortcut" in report["failure_matrix"]["failure_counts"]
    assert "manager_output_contract_violation" in report["failure_matrix"]["failure_counts"]


def test_websearch_live_diagnostic_report_script_roundtrip(tmp_path: Path) -> None:
    from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact
    from scripts.build_accurate_intake_websearch_live_diagnostic_report import main

    diagnostic = {
        "artifact_type": "accurate_intake_grokfast_websearch_packet_smoke",
        "status": "diagnostic_fail",
        "live_provider_used": True,
        "live_websearch_used": False,
        "summary": {
            "case_count": 4,
            "pass_count": 0,
            "fail_count": 4,
            "failure_families": ["provider_response_error"],
        },
        "cases": [],
    }
    input_path = tmp_path / "diagnostic.json"
    output_path = tmp_path / "report.json"
    write_json_artifact(input_path, diagnostic)

    assert main(["--diagnostic-artifact", str(input_path), "--output", str(output_path)]) == 0

    report = read_json_artifact(output_path)
    assert report["seam_status"] == "provider_contract_blocked"
    assert report["source_live_websearch_used"] is False
    assert report["should_run_websearch_live_tool_loop"] is False


def test_websearch_live_diagnostic_report_script_accepts_bundle_manifest(
    tmp_path: Path,
) -> None:
    from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact
    from scripts.build_accurate_intake_websearch_live_diagnostic_report import main

    bundle_dir = tmp_path / "bundle"
    bundle_dir.mkdir()
    diagnostic_path = bundle_dir / "grokfast_websearch_packet_smoke.json"
    preflight_path = bundle_dir / "websearch_live_preflight.json"
    manifest_path = bundle_dir / "websearch_live_manifest.json"
    output_path = tmp_path / "report.json"

    write_json_artifact(
        diagnostic_path,
        {
            "artifact_type": "accurate_intake_grokfast_websearch_packet_smoke",
            "status": "pass",
            "live_provider_used": True,
            "live_websearch_used": False,
            "preflight_ref": _clear_preflight_ref(),
            "summary": {
                "case_count": 4,
                "pass_count": 4,
                "fail_count": 0,
                "failure_families": [],
            },
            "cases": [],
        },
    )
    write_json_artifact(preflight_path, _clear_preflight_artifact())
    write_json_artifact(
        manifest_path,
        {
            "artifact_type": "accurate_intake_websearch_live_diagnostic_bundle_manifest",
            "artifacts": {
                "diagnostic": str(diagnostic_path),
                "preflight": str(preflight_path),
            },
        },
    )

    assert (
        main(
            [
                "--bundle-manifest",
                str(manifest_path),
                "--output",
                str(output_path),
            ]
        )
        == 0
    )

    report = read_json_artifact(output_path)
    assert report["seam_status"] == "live_diagnostic_pass"
    assert report["source_live_websearch_used"] is False
    assert report["preflight_evidence_healthy"] is True
    assert report["preflight_evidence"]["status"] == "pass"
    assert report["next_recommended_slice"] == "inspect_websearch_status_packet"


def test_websearch_live_diagnostic_report_rejects_unexpected_source_artifact_type() -> None:
    diagnostic = {
        "artifact_type": "some_other_artifact",
        "status": "pass",
        "live_provider_used": True,
        "live_websearch_used": False,
        "summary": {"case_count": 0, "pass_count": 0, "fail_count": 0, "failure_families": []},
        "cases": [],
    }

    try:
        build_websearch_live_diagnostic_report(diagnostic_artifact=diagnostic)
    except ValueError as exc:
        assert "unsupported_websearch_live_diagnostic_artifact_type" in str(exc)
    else:  # pragma: no cover - assertion branch
        raise AssertionError("unexpected source artifact type must fail")


def test_websearch_live_diagnostic_report_has_no_live_imports() -> None:
    source_paths = [
        Path("app/nutrition/application/websearch_live_diagnostic_report.py"),
        Path("scripts/build_accurate_intake_websearch_live_diagnostic_report.py"),
    ]
    forbidden = [
        "BuilderSpaceAdapter",
        "Tavily",
        "tavily",
        "requests.",
        "httpx.",
        "allow_live",
    ]
    for path in source_paths:
        source = path.read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in source


def _contains_key(value: object, target_key: str) -> bool:
    if isinstance(value, dict):
        return target_key in value or any(_contains_key(child, target_key) for child in value.values())
    if isinstance(value, list):
        return any(_contains_key(item, target_key) for item in value)
    return False


def _scalar_values(value: object) -> set[str]:
    if isinstance(value, dict):
        return {item for child in value.values() for item in _scalar_values(child)}
    if isinstance(value, list):
        return {item for child in value for item in _scalar_values(child)}
    return {str(value)}
