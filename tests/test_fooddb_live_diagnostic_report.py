from __future__ import annotations

import hashlib
import json as jsonlib
from pathlib import Path

from app.nutrition.application.fooddb_live_diagnostic_report import (
    build_fooddb_live_diagnostic_report,
)
from app.nutrition.application.grokfast_fooddb_packet_smoke import (
    build_fixture_manager_outputs,
    build_grokfast_fooddb_packet_diagnostic,
)
from app.nutrition.application.fooddb_manager_packet_smoke import (
    build_fooddb_manager_packet_smoke,
)
from app.nutrition.application.fooddb_retrieval_policy import (
    build_runtime_retrieval_records_from_small_anchor_payload,
)
import json


def _packet_artifact() -> dict:
    payload = json.loads(Path("app/knowledge/small_anchor_store_tw.json").read_text(encoding="utf-8-sig"))
    records = build_runtime_retrieval_records_from_small_anchor_payload(payload)
    return build_fooddb_manager_packet_smoke(retrieval_records=records)


def _clear_preflight_artifact() -> dict[str, object]:
    return {
        "artifact_type": "accurate_intake_grokfast_fooddb_diagnostic_preflight_v1",
        "artifact_schema_version": "1.0",
        "generated_at_utc": "2026-05-06T00:00:00Z",
        "track": "FDB",
        "classification": "deterministic_fooddb_live_preflight_only",
        "claim_scope": "fooddb_live_diagnostic_preflight_without_live_call",
        "status": "clear_for_grokfast_fooddb_packet_live_diagnostic",
        "clear_to_run_live_diagnostic": True,
        "blockers": [],
        "runtime_truth_changed": False,
        "mutation_changed": False,
        "manager_context_changed": False,
        "packetizer_format_changed": False,
        "live_provider_used": False,
        "live_websearch_used": False,
        "readiness_claimed": False,
        "self_use_approved": False,
        "production_selected": False,
        "next_required_slice": "grokfast_fooddb_packet_live_diagnostic",
        "summary": {
            "retrieval_eval_fail_count": 0,
            "retrieval_eval_next_required_slice": "grokfast_fooddb_packet_live_diagnostic",
            "websearch_runtime_truth_allowed_count": 0,
            "fooddb_next_required_slices": ["grokfast_fooddb_packet_live_diagnostic"],
            "manager_fooddb_packet_seam_gate_status": "pass",
            "manager_contract_handoff_status": "not_run",
            "manager_contract_owner_handoff_ready": False,
            "manager_packet_case_count": 5,
            "manager_packet_compact_pass_count": 5,
            "index_backend_parity_status": "pass",
            "index_backend_parity_fail_count": 0,
            "index_backend_parity_backend_count": 3,
            "index_backend_parity_next_required_slice": "grokfast_fooddb_packet_live_diagnostic",
            "case_matrix_status": "pass",
            "case_matrix_plan_only": True,
            "case_matrix_case_count": 5,
            "case_matrix_modifier_guard_cases": 2,
            "case_matrix_bare_basket_cases": 1,
            "case_matrix_listed_basket_cases": 1,
            "case_matrix_websearch_cases": 0,
            "case_matrix_exact_card_cases": 0,
            "case_matrix_live_provider_invoked": False,
            "case_matrix_websearch_invoked": False,
            "case_matrix_shared_contract_changed": False,
            "case_matrix_non_claim_count": 7,
        },
    }


def _clear_router_readiness_artifact() -> dict[str, object]:
    return {
        "artifact_type": "accurate_intake_food_evidence_retriever_router_readiness_v1",
        "artifact_schema_version": "1.0",
        "generated_at_utc": "2026-05-06T00:00:00Z",
        "track": "FDB",
        "classification": "deterministic_retriever_router_readiness_only",
        "claim_scope": "food_evidence_retriever_router_readiness_without_live_call",
        "status": "pass",
        "runtime_truth_changed": False,
        "mutation_changed": False,
        "shared_contract_changed": False,
        "manager_context_changed": False,
        "live_provider_used": False,
        "live_websearch_used": False,
        "readiness_claimed": False,
        "summary": {
            "case_count": 4,
            "fail_count": 0,
            "exact_brand_websearch_ready": False,
            "websearch_status_gate_present": False,
            "next_required_slice": "inspect_websearch_status_packet",
        },
    }


def _clear_live_runner_readiness_artifact(
    preflight: dict[str, object],
    router: dict[str, object],
) -> dict[str, object]:
    return {
        "artifact_type": "accurate_intake_grokfast_fooddb_live_runner_readiness_packet_v1",
        "artifact_schema_version": "1.0",
        "generated_at_utc": "2026-05-06T00:00:00Z",
        "track": "FDB",
        "classification": "deterministic_fooddb_live_runner_readiness_only",
        "claim_scope": "fooddb_live_runner_pre_provider_call_without_live_call",
        "status": "pass",
        "blockers": [],
        "ready_for_grokfast_fooddb_packet_live_diagnostic": True,
        "ready_for_runtime_truth": False,
        "runtime_truth_changed": False,
        "runtime_mutation_allowed": False,
        "manager_context_changed": False,
        "shared_contract_changed": False,
        "packetizer_format_changed": False,
        "live_provider_used": False,
        "live_websearch_used": False,
        "readiness_claimed": False,
        "provider_readiness_checked": False,
        "source_refs": {
            "preflight_artifact_type": preflight["artifact_type"],
            "preflight_status": preflight["status"],
            "router_readiness_artifact_type": router["artifact_type"],
            "router_readiness_status": router["status"],
            "router_fail_count": 0,
            "router_next_required_slice": "inspect_websearch_status_packet",
            "router_exact_brand_websearch_ready": False,
            "router_websearch_status_gate_present": False,
        },
        "summary": {
            "preflight_status": preflight["status"],
            "router_readiness_status": router["status"],
            "router_readiness_fail_count": 0,
            "router_next_required_slice": "inspect_websearch_status_packet",
            "router_exact_brand_websearch_ready": False,
            "provider_configuration_status": "not_checked_until_live_invocation",
        },
        "runner_contract": {
            "requires_explicit_allow_live_flag": True,
            "requires_clear_fooddb_preflight": True,
            "requires_clear_retriever_router_readiness": True,
            "requires_clear_live_runner_readiness_packet": True,
            "live_call_allowed_by_this_artifact": False,
            "ledger_mutation_allowed": False,
            "websearch_runtime_truth_allowed": False,
        },
        "next_required_slice": "run_explicit_grokfast_fooddb_packet_live_diagnostic",
    }


def _semantic_digest(artifact: dict[str, object]) -> str:
    payload = {key: value for key, value in artifact.items() if key != "generated_at_utc"}
    encoded = jsonlib.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _live_diagnostic_with_verified_refs() -> tuple[dict[str, object], dict[str, object], dict[str, object], dict[str, object]]:
    preflight = _clear_preflight_artifact()
    router = _clear_router_readiness_artifact()
    readiness = _clear_live_runner_readiness_artifact(preflight, router)
    diagnostic = {
        "artifact_type": "accurate_intake_grokfast_fooddb_packet_smoke",
        "status": "pass",
        "live_provider_used": True,
        "summary": {
            "case_count": 5,
            "pass_count": 5,
            "fail_count": 0,
            "failure_families": [],
        },
        "cases": [],
        "preflight_ref": {
            "artifact_type": preflight["artifact_type"],
            "status": preflight["status"],
            "clear_to_run_live_diagnostic": True,
            "next_required_slice": preflight["next_required_slice"],
            "preflight_artifact_digest_algorithm": "sha256",
            "preflight_artifact_digest_scope": "semantic_artifact_without_generated_at_utc",
            "preflight_artifact_digest": _semantic_digest(preflight),
        },
        "router_readiness_ref": {
            "artifact_type": router["artifact_type"],
            "status": router["status"],
            "fail_count": 0,
            "next_required_slice": "inspect_websearch_status_packet",
            "router_artifact_digest_algorithm": "sha256",
            "router_artifact_digest_scope": "semantic_artifact_without_generated_at_utc",
            "router_artifact_digest": _semantic_digest(router),
        },
        "live_runner_readiness_ref": {
            "artifact_type": readiness["artifact_type"],
            "status": readiness["status"],
            "ready_for_grokfast_fooddb_packet_live_diagnostic": True,
            "ready_for_runtime_truth": False,
            "next_required_slice": readiness["next_required_slice"],
            "live_runner_artifact_digest_algorithm": "sha256",
            "live_runner_artifact_digest_scope": "semantic_artifact_without_generated_at_utc",
            "live_runner_artifact_digest": _semantic_digest(readiness),
        },
    }
    return diagnostic, preflight, router, readiness


def test_fooddb_live_diagnostic_report_treats_fixture_pass_as_live_not_checked() -> None:
    diagnostic = build_grokfast_fooddb_packet_diagnostic(
        packet_artifact=_packet_artifact(),
        manager_outputs=build_fixture_manager_outputs(packet_artifact=_packet_artifact()),
        live_provider_used=False,
    )

    report = build_fooddb_live_diagnostic_report(diagnostic_artifact=diagnostic)

    assert report["artifact_type"] == "accurate_intake_fooddb_live_diagnostic_report"
    assert report["source_status"] == "pass"
    assert report["source_live_provider_used"] is False
    assert report["seam_status"] == "fixture_only_live_not_checked"
    assert report["can_expand_to_websearch_live_diagnostic"] is False
    assert report["next_recommended_slice"] == "run_explicit_grokfast_fooddb_packet_live_diagnostic"
    assert "no_live_provider_call" in report["non_claims"]


def test_fooddb_live_diagnostic_report_blocks_provider_contract_failures() -> None:
    diagnostic = {
        "artifact_type": "accurate_intake_grokfast_fooddb_packet_smoke",
        "status": "diagnostic_fail",
        "live_provider_used": True,
        "summary": {
            "case_count": 5,
            "pass_count": 0,
            "fail_count": 5,
            "failure_families": ["provider_response_error"],
        },
        "cases": [
            {
                "case_id": "boba_large_half_sugar",
                "status": "fail",
                "failure_families": [],
                "provider_trace": {
                    "failure_family": "provider_response_error",
                    "trace": {"failure_family": "manager_output_contract_violation"},
                },
            }
        ],
    }

    report = build_fooddb_live_diagnostic_report(diagnostic_artifact=diagnostic)

    assert report["seam_status"] == "provider_contract_blocked"
    assert report["provider_contract_blocked"] is True
    assert report["packet_boundary_blocked"] is False
    assert report["next_recommended_slice"] == "narrow_grokfast_fooddb_manager_contract_probe"


def test_fooddb_live_diagnostic_report_distinguishes_packet_boundary_failures() -> None:
    diagnostic = {
        "artifact_type": "accurate_intake_grokfast_fooddb_packet_smoke",
        "status": "diagnostic_fail",
        "live_provider_used": True,
        "summary": {
            "case_count": 5,
            "pass_count": 0,
            "fail_count": 5,
            "failure_families": [
                "fooddb_packet_not_used",
                "generic_meal_overclaimed_exact",
            ],
        },
        "cases": [
            {
                "case_id": "chicken_bento_less_rice",
                "status": "fail",
                "failure_families": [
                    "fooddb_packet_not_used",
                    "generic_meal_overclaimed_exact",
                ],
                "provider_trace": {},
            }
        ],
    }

    report = build_fooddb_live_diagnostic_report(diagnostic_artifact=diagnostic)

    assert report["seam_status"] == "packet_boundary_blocked"
    assert report["provider_contract_blocked"] is False
    assert report["packet_boundary_blocked"] is True
    assert report["next_recommended_slice"] == "narrow_fooddb_packet_boundary_or_prompt_probe"


def test_fooddb_live_diagnostic_report_treats_modifier_adjustment_misuse_as_packet_boundary_failure() -> None:
    diagnostic = {
        "artifact_type": "accurate_intake_grokfast_fooddb_packet_smoke",
        "status": "diagnostic_fail",
        "live_provider_used": True,
        "summary": {
            "case_count": 5,
            "pass_count": 4,
            "fail_count": 1,
            "failure_families": ["modifier_adjusted_kcal_without_packet_adjustment"],
        },
        "cases": [
            {
                "case_id": "chicken_bento_less_rice",
                "status": "fail",
                "failure_families": ["modifier_adjusted_kcal_without_packet_adjustment"],
                "provider_trace": {},
            }
        ],
    }

    report = build_fooddb_live_diagnostic_report(diagnostic_artifact=diagnostic)

    assert report["seam_status"] == "packet_boundary_blocked"
    assert report["packet_boundary_blocked"] is True
    assert report["next_recommended_slice"] == "narrow_fooddb_packet_boundary_or_prompt_probe"


def test_fooddb_live_diagnostic_report_advances_to_websearch_only_after_live_pass() -> None:
    diagnostic, preflight, router, readiness = _live_diagnostic_with_verified_refs()

    report = build_fooddb_live_diagnostic_report(
        diagnostic_artifact=diagnostic,
        preflight_artifact=preflight,
        router_readiness_artifact=router,
        live_runner_readiness_artifact=readiness,
    )

    assert report["seam_status"] == "live_diagnostic_pass"
    assert report["can_expand_to_websearch_live_diagnostic"] is True
    assert report["next_recommended_slice"] == "grokfast_websearch_packet_live_diagnostic"
    assert report["readiness_claimed"] is False
    assert report["upstream_evidence_required"] is True
    assert report["upstream_evidence_healthy"] is True
    assert "no_live_provider_call" not in report["non_claims"]


def test_fooddb_live_diagnostic_report_blocks_live_pass_without_verified_upstream_evidence() -> None:
    diagnostic, _, _, _ = _live_diagnostic_with_verified_refs()

    report = build_fooddb_live_diagnostic_report(diagnostic_artifact=diagnostic)

    assert report["seam_status"] == "upstream_evidence_missing"
    assert report["can_expand_to_websearch_live_diagnostic"] is False
    assert report["upstream_evidence_required"] is True
    assert report["upstream_evidence_healthy"] is False
    assert report["next_recommended_slice"] == "rerun_with_clear_fooddb_live_runner_evidence"


def test_fooddb_live_diagnostic_report_blocks_live_pass_with_mismatched_upstream_digest() -> None:
    diagnostic, preflight, router, readiness = _live_diagnostic_with_verified_refs()
    diagnostic["live_runner_readiness_ref"]["live_runner_artifact_digest"] = "0" * 64

    report = build_fooddb_live_diagnostic_report(
        diagnostic_artifact=diagnostic,
        preflight_artifact=preflight,
        router_readiness_artifact=router,
        live_runner_readiness_artifact=readiness,
    )

    assert report["seam_status"] == "upstream_evidence_missing"
    assert report["upstream_evidence_healthy"] is False
    assert report["upstream_evidence"]["live_runner_artifact_digest_verified"] is False
    assert report["next_recommended_slice"] == "rerun_with_clear_fooddb_live_runner_evidence"


def test_fooddb_live_diagnostic_report_sanitizes_raw_payloads() -> None:
    diagnostic = {
        "artifact_type": "accurate_intake_grokfast_fooddb_packet_smoke",
        "status": "diagnostic_fail",
        "live_provider_used": True,
        "summary": {"case_count": 1, "pass_count": 0, "fail_count": 1, "failure_families": []},
        "cases": [
            {
                "case_id": "case",
                "status": "fail",
                "failure_families": ["invented_evidence_reference"],
                "manager_output": {
                    "item_results": [{"food_name": "invented", "likely_kcal": 123}],
                    "evidence_used": ["fake_anchor"],
                },
                "provider_trace": {
                    "raw_response_excerpt": "invented fake_anchor likely_kcal",
                    "parsed_object": {"runtime_truth_allowed": True},
                },
            }
        ],
    }

    report = build_fooddb_live_diagnostic_report(diagnostic_artifact=diagnostic)

    assert not _contains_key(report, "manager_output")
    assert not _contains_key(report, "raw_response_excerpt")
    assert not _contains_key(report, "parsed_object")
    assert not _contains_key(report, "food_name")
    assert not _contains_key(report, "likely_kcal")
    assert "invented" not in _scalar_values(report)
    assert "fake_anchor" not in _scalar_values(report)


def test_fooddb_live_diagnostic_report_script_roundtrip(tmp_path: Path) -> None:
    from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact
    from scripts.build_accurate_intake_fooddb_live_diagnostic_report import main

    diagnostic, preflight, router, readiness = _live_diagnostic_with_verified_refs()
    input_path = tmp_path / "diagnostic.json"
    preflight_path = tmp_path / "preflight.json"
    router_path = tmp_path / "router.json"
    readiness_path = tmp_path / "readiness.json"
    output_path = tmp_path / "report.json"
    write_json_artifact(input_path, diagnostic)
    write_json_artifact(preflight_path, preflight)
    write_json_artifact(router_path, router)
    write_json_artifact(readiness_path, readiness)

    assert (
        main(
            [
                "--diagnostic-artifact",
                str(input_path),
                "--preflight-artifact",
                str(preflight_path),
                "--router-readiness-artifact",
                str(router_path),
                "--live-runner-readiness-artifact",
                str(readiness_path),
                "--output",
                str(output_path),
            ]
        )
        == 0
    )

    report = read_json_artifact(output_path)
    assert report["seam_status"] == "live_diagnostic_pass"
    assert report["next_recommended_slice"] == "grokfast_websearch_packet_live_diagnostic"


def test_fooddb_live_diagnostic_report_rejects_unexpected_source_artifact_type() -> None:
    diagnostic = {
        "artifact_type": "some_other_artifact",
        "status": "pass",
        "live_provider_used": True,
        "summary": {"case_count": 0, "pass_count": 0, "fail_count": 0, "failure_families": []},
        "cases": [],
    }

    try:
        build_fooddb_live_diagnostic_report(diagnostic_artifact=diagnostic)
    except ValueError as exc:
        assert "unsupported_fooddb_live_diagnostic_artifact_type" in str(exc)
    else:
        raise AssertionError("unexpected source artifact type must fail")


def test_fooddb_live_diagnostic_report_has_no_live_imports() -> None:
    source_paths = [
        Path("app/nutrition/application/fooddb_live_diagnostic_report.py"),
        Path("scripts/build_accurate_intake_fooddb_live_diagnostic_report.py"),
    ]
    forbidden = [
        "BuilderSpaceAdapter",
        "requests.",
        "httpx.",
        "allow_live",
        "Tavily",
        "tavily",
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
