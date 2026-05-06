from __future__ import annotations

from pathlib import Path

from app.nutrition.application.websearch_manager_contract_handoff import (
    build_websearch_manager_contract_handoff,
)
from app.nutrition.application.websearch_preflight_digest import (
    PREFLIGHT_DIGEST_ALGORITHM,
    PREFLIGHT_DIGEST_SCOPE,
    websearch_live_extract_preflight_digest,
)
from scripts.websearch_live_bundle_artifacts import build_websearch_live_bundle_artifact_paths


def _clear_preflight_artifact() -> dict:
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


def _live_report(
    *,
    seam_status: str = "provider_contract_blocked",
    preflight_artifact: dict | None = None,
) -> dict:
    preflight = preflight_artifact or _clear_preflight_artifact()
    return {
        "artifact_type": "accurate_intake_websearch_live_diagnostic_report",
        "seam_status": seam_status,
        "source_artifact_type": "accurate_intake_grokfast_websearch_packet_smoke",
        "source_status": "pass" if seam_status == "live_diagnostic_pass" else "diagnostic_fail",
        "preflight_evidence_healthy": seam_status == "live_diagnostic_pass",
        "preflight_evidence_required": True,
        "preflight_evidence": {
            "preflight_artifact_digest_algorithm": PREFLIGHT_DIGEST_ALGORITHM,
            "preflight_artifact_digest_scope": PREFLIGHT_DIGEST_SCOPE,
            "preflight_artifact_digest": websearch_live_extract_preflight_digest(preflight),
            "preflight_artifact_digest_verified": seam_status == "live_diagnostic_pass",
            "preflight_artifact_integrity_clear": seam_status == "live_diagnostic_pass",
            "ready_for_runtime_truth": False,
        },
        "can_expand_websearch_candidate_pipeline": seam_status == "live_diagnostic_pass",
        "source_live_provider_used": True,
        "source_live_websearch_used": False,
        "runtime_truth_changed": False,
        "runtime_mutation_attempted": False,
        "readiness_claimed": False,
        "next_recommended_slice": "narrow_grokfast_websearch_manager_contract_probe",
    }


def _probe(*, contract_failure_detected: bool = True) -> dict:
    return {
        "artifact_type": "accurate_intake_websearch_manager_contract_probe",
        "status": "diagnostic_fail" if contract_failure_detected else "pass",
        "contract_failure_detected": contract_failure_detected,
        "summary": {
            "case_count": 2,
            "fail_count": 2 if contract_failure_detected else 0,
            "aggregate_missing_required_fields": {"intent": 2}
            if contract_failure_detected
            else {},
            "next_recommended_slice": "narrow_prompt_schema_intent_alias_probe",
        },
    }


def _repair_pack(
    *,
    next_recommended_slice: str = "tighten_websearch_manager_contract_prompt_or_transport",
) -> dict:
    return {
        "artifact_type": "accurate_intake_websearch_manager_contract_repair_pack",
        "next_recommended_slice": next_recommended_slice,
        "summary": {
            "case_count": 2,
            "alias_hint_counts": {"intent": 2},
            "shape_pattern_counts": {"intent_type_present_intent_missing": 2},
        },
    }


def test_websearch_manager_contract_handoff_marks_owner_ready_for_provider_contract_failures() -> None:
    artifact = build_websearch_manager_contract_handoff(
        live_diagnostic_report=_live_report(),
        contract_probe_artifact=_probe(),
        repair_pack_artifact=_repair_pack(),
    )

    assert artifact["artifact_type"] == "accurate_intake_websearch_manager_contract_handoff_v1"
    assert artifact["status"] == "ready_for_manager_contract_owner"
    assert artifact["selected_next_step"] == "tighten_websearch_manager_contract_prompt_or_transport"
    assert artifact["handoff_ready"] is True
    assert artifact["downstream_owner"] == "manager_runtime_contract"
    assert artifact["runtime_truth_changed"] is False
    assert artifact["shared_contract_changed"] is False
    assert artifact["summary"]["alignment_blocker_count"] == 0


def test_websearch_manager_contract_handoff_blocks_alignment_gaps() -> None:
    artifact = build_websearch_manager_contract_handoff(
        live_diagnostic_report=_live_report(),
        contract_probe_artifact=_probe(),
        repair_pack_artifact={**_repair_pack(), "summary": {"case_count": 0}},
    )

    assert artifact["status"] == "blocked_contract_handoff_alignment"
    assert artifact["selected_next_step"] == "repair_artifact_alignment_required"
    assert "repair_pack_empty_for_contract_failure" in artifact["alignment_blockers"]
    assert "probe_repair_case_count_mismatch" in artifact["alignment_blockers"]


def test_websearch_manager_contract_handoff_detects_live_probe_status_mismatch() -> None:
    artifact = build_websearch_manager_contract_handoff(
        live_diagnostic_report=_live_report(),
        contract_probe_artifact=_probe(contract_failure_detected=False),
        repair_pack_artifact={**_repair_pack(), "summary": {"case_count": 0}},
    )

    assert artifact["status"] == "blocked_contract_handoff_alignment"
    assert "live_report_probe_contract_status_mismatch" in artifact["alignment_blockers"]


def test_websearch_manager_contract_handoff_returns_to_websearch_on_candidate_boundary_block() -> None:
    artifact = build_websearch_manager_contract_handoff(
        live_diagnostic_report=_live_report(seam_status="candidate_boundary_blocked"),
        contract_probe_artifact=_probe(contract_failure_detected=False),
        repair_pack_artifact={**_repair_pack(), "summary": {"case_count": 0}},
    )

    assert artifact["status"] == "return_to_websearch_packet_boundary"
    assert artifact["selected_next_step"] == "narrow_websearch_packet_boundary_or_prompt_probe"
    assert artifact["handoff_ready"] is False


def test_websearch_manager_contract_handoff_blocks_live_pass_when_probe_still_fails() -> None:
    artifact = build_websearch_manager_contract_handoff(
        live_diagnostic_report=_live_report(seam_status="live_diagnostic_pass"),
        contract_probe_artifact=_probe(),
        repair_pack_artifact=_repair_pack(),
    )

    assert artifact["status"] == "blocked_contract_handoff_alignment"
    assert "live_pass_with_contract_failure_detected" in artifact["alignment_blockers"]
    assert artifact["handoff_ready"] is False


def test_websearch_manager_contract_handoff_blocks_live_pass_without_healthy_preflight_gate() -> None:
    preflight = _clear_preflight_artifact()
    artifact = build_websearch_manager_contract_handoff(
        live_diagnostic_report={
            **_live_report(seam_status="live_diagnostic_pass", preflight_artifact=preflight),
            "preflight_evidence_healthy": False,
            "can_expand_websearch_candidate_pipeline": True,
        },
        contract_probe_artifact=_probe(contract_failure_detected=False),
        repair_pack_artifact={**_repair_pack(), "summary": {"case_count": 0}},
        preflight_artifact=preflight,
    )

    assert artifact["status"] == "blocked_contract_handoff_alignment"
    assert "live_report_preflight_evidence_not_healthy" in artifact["alignment_blockers"]
    assert artifact["selected_next_step"] == "repair_artifact_alignment_required"
    assert artifact["handoff_ready"] is False


def test_websearch_manager_contract_handoff_blocks_live_pass_with_runtime_or_live_overclaims() -> None:
    preflight = _clear_preflight_artifact()
    artifact = build_websearch_manager_contract_handoff(
        live_diagnostic_report={
            **_live_report(seam_status="live_diagnostic_pass", preflight_artifact=preflight),
            "preflight_evidence_healthy": True,
            "can_expand_websearch_candidate_pipeline": True,
            "runtime_truth_changed": True,
            "runtime_mutation_attempted": True,
            "readiness_claimed": True,
            "source_live_websearch_used": True,
        },
        contract_probe_artifact=_probe(contract_failure_detected=False),
        repair_pack_artifact={**_repair_pack(), "summary": {"case_count": 0}},
        preflight_artifact=preflight,
    )

    assert artifact["status"] == "blocked_contract_handoff_alignment"
    assert "live_report_changed_runtime_truth" in artifact["alignment_blockers"]
    assert "live_report_attempted_runtime_mutation" in artifact["alignment_blockers"]
    assert "live_report_claimed_readiness" in artifact["alignment_blockers"]
    assert "live_report_used_live_websearch" in artifact["alignment_blockers"]
    assert artifact["handoff_ready"] is False


def test_websearch_manager_contract_handoff_blocks_minimal_forged_live_pass_report() -> None:
    artifact = build_websearch_manager_contract_handoff(
        live_diagnostic_report={
            "artifact_type": "accurate_intake_websearch_live_diagnostic_report",
            "seam_status": "live_diagnostic_pass",
            "preflight_evidence_healthy": True,
            "can_expand_websearch_candidate_pipeline": True,
            "source_live_provider_used": True,
            "source_live_websearch_used": False,
            "runtime_truth_changed": False,
            "runtime_mutation_attempted": False,
            "readiness_claimed": False,
            "next_recommended_slice": "inspect_websearch_status_packet",
        },
        contract_probe_artifact=_probe(contract_failure_detected=False),
        repair_pack_artifact={**_repair_pack(), "summary": {"case_count": 0}},
    )

    assert artifact["status"] == "blocked_contract_handoff_alignment"
    assert "live_report_source_artifact_type_mismatch" in artifact["alignment_blockers"]
    assert "live_report_preflight_evidence_missing" in artifact["alignment_blockers"]
    assert artifact["handoff_ready"] is False


def test_websearch_manager_contract_handoff_blocks_live_pass_with_contradictory_preflight_payload() -> None:
    preflight = _clear_preflight_artifact()
    live_report = _live_report(seam_status="live_diagnostic_pass", preflight_artifact=preflight)
    live_report["preflight_evidence"] = {
        "preflight_artifact_digest_algorithm": PREFLIGHT_DIGEST_ALGORITHM,
        "preflight_artifact_digest_scope": PREFLIGHT_DIGEST_SCOPE,
        "preflight_artifact_digest": websearch_live_extract_preflight_digest(preflight),
        "preflight_artifact_digest_verified": False,
        "preflight_artifact_integrity_clear": True,
        "ready_for_runtime_truth": True,
    }

    artifact = build_websearch_manager_contract_handoff(
        live_diagnostic_report=live_report,
        contract_probe_artifact=_probe(contract_failure_detected=False),
        repair_pack_artifact={**_repair_pack(), "summary": {"case_count": 0}},
        preflight_artifact=preflight,
    )

    assert artifact["status"] == "blocked_contract_handoff_alignment"
    assert "live_report_preflight_digest_not_verified" in artifact["alignment_blockers"]
    assert "live_report_preflight_allowed_runtime_truth" in artifact["alignment_blockers"]
    assert artifact["handoff_ready"] is False


def test_websearch_manager_contract_handoff_blocks_complete_forged_live_pass_without_preflight_artifact() -> None:
    artifact = build_websearch_manager_contract_handoff(
        live_diagnostic_report=_live_report(seam_status="live_diagnostic_pass"),
        contract_probe_artifact=_probe(contract_failure_detected=False),
        repair_pack_artifact={**_repair_pack(), "summary": {"case_count": 0}},
    )

    assert artifact["status"] == "blocked_contract_handoff_alignment"
    assert "live_report_preflight_artifact_missing" in artifact["alignment_blockers"]
    assert artifact["handoff_ready"] is False


def test_websearch_manager_contract_handoff_blocks_live_pass_with_mismatched_preflight_artifact() -> None:
    preflight = _clear_preflight_artifact()
    mismatched_preflight = {**preflight, "status": "blocked"}

    artifact = build_websearch_manager_contract_handoff(
        live_diagnostic_report=_live_report(
            seam_status="live_diagnostic_pass",
            preflight_artifact=preflight,
        ),
        contract_probe_artifact=_probe(contract_failure_detected=False),
        repair_pack_artifact={**_repair_pack(), "summary": {"case_count": 0}},
        preflight_artifact=mismatched_preflight,
    )

    assert artifact["status"] == "blocked_contract_handoff_alignment"
    assert "live_report_preflight_artifact_digest_mismatch" in artifact["alignment_blockers"]
    assert "live_report_preflight_artifact_not_clear" in artifact["alignment_blockers"]
    assert artifact["handoff_ready"] is False


def test_websearch_manager_contract_handoff_allows_passed_contract() -> None:
    preflight = _clear_preflight_artifact()
    artifact = build_websearch_manager_contract_handoff(
        live_diagnostic_report=_live_report(
            seam_status="live_diagnostic_pass",
            preflight_artifact=preflight,
        ),
        contract_probe_artifact=_probe(contract_failure_detected=False),
        repair_pack_artifact={**_repair_pack(), "summary": {"case_count": 0}},
        preflight_artifact=preflight,
    )

    assert artifact["status"] == "websearch_contract_unblocked"
    assert artifact["selected_next_step"] == "inspect_websearch_status_packet"
    assert artifact["handoff_ready"] is False


def test_websearch_manager_contract_handoff_sanitizes_against_raw_payload_leakage() -> None:
    artifact = build_websearch_manager_contract_handoff(
        live_diagnostic_report={
            **_live_report(),
            "raw_response_excerpt": "forbidden",
            "parsed_object": {"food_name": "invented"},
        },
        contract_probe_artifact={
            **_probe(),
            "cases": [{"raw_content_excerpt": "forbidden"}],
        },
        repair_pack_artifact={
            **_repair_pack(),
            "cases": [{"present_top_level_fields": ["intent_type"], "food_name": "invented"}],
        },
    )

    serialized = str(artifact)
    assert "raw_response_excerpt" not in serialized
    assert "parsed_object" not in serialized
    assert "food_name" not in serialized
    assert "invented" not in serialized
    assert "forbidden" not in serialized


def test_websearch_manager_contract_handoff_whitelists_upstream_summaries() -> None:
    artifact = build_websearch_manager_contract_handoff(
        live_diagnostic_report={
            **_live_report(),
            "next_recommended_slice": "raw_response_excerpt forbidden",
            "source_live_provider_used": "raw_response_excerpt forbidden",
            "source_live_websearch_used": "raw_response_excerpt forbidden",
        },
        contract_probe_artifact={
            **_probe(),
            "summary": {
                "case_count": 2,
                "fail_count": 2,
                "aggregate_missing_required_fields": {
                    "intent": 2,
                    "raw_response_excerpt forbidden": 1,
                },
                "next_recommended_slice": "raw_response_excerpt forbidden",
            },
        },
        repair_pack_artifact={
            **_repair_pack(next_recommended_slice="raw_response_excerpt forbidden"),
            "summary": {
                "case_count": 2,
                "alias_hint_counts": {
                    "intent": 2,
                    "raw_response_excerpt forbidden": 1,
                },
                "shape_pattern_counts": {
                    "intent_type_present_intent_missing": 2,
                    "raw_response_excerpt forbidden": 1,
                },
            },
        },
    )

    serialized = str(artifact)
    assert "raw_response_excerpt" not in serialized
    assert "forbidden" not in serialized
    assert artifact["summary"]["aggregate_missing_required_fields"] == {"intent": 2}
    assert artifact["summary"]["alias_hint_counts"] == {"intent": 2}
    assert artifact["artifact_chain"]["live_diagnostic_report"]["next_recommended_slice"] is None
    assert artifact["artifact_chain"]["live_diagnostic_report"]["source_live_provider_used"] is False
    assert artifact["artifact_chain"]["live_diagnostic_report"]["source_live_websearch_used"] is False
    assert artifact["artifact_chain"]["contract_probe"]["next_recommended_slice"] is None


def test_websearch_manager_contract_handoff_script_roundtrip(tmp_path: Path) -> None:
    from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact
    from scripts.build_accurate_intake_websearch_manager_contract_handoff import main

    live_path = tmp_path / "live.json"
    probe_path = tmp_path / "probe.json"
    repair_path = tmp_path / "repair.json"
    output_path = tmp_path / "handoff.json"
    write_json_artifact(live_path, _live_report())
    write_json_artifact(probe_path, _probe())
    write_json_artifact(repair_path, _repair_pack())

    assert (
        main(
            [
                "--live-diagnostic-report",
                str(live_path),
                "--contract-probe-artifact",
                str(probe_path),
                "--repair-pack-artifact",
                str(repair_path),
                "--output",
                str(output_path),
            ]
        )
        == 0
    )

    artifact = read_json_artifact(output_path)
    assert artifact["status"] == "ready_for_manager_contract_owner"
    assert artifact["handoff_ready"] is True


def test_websearch_manager_contract_handoff_script_roundtrip_with_preflight_artifact(
    tmp_path: Path,
) -> None:
    from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact
    from scripts.build_accurate_intake_websearch_manager_contract_handoff import main

    preflight = _clear_preflight_artifact()
    live_path = tmp_path / "live.json"
    preflight_path = tmp_path / "preflight.json"
    probe_path = tmp_path / "probe.json"
    repair_path = tmp_path / "repair.json"
    output_path = tmp_path / "handoff.json"
    write_json_artifact(live_path, _live_report(seam_status="live_diagnostic_pass"))
    write_json_artifact(preflight_path, preflight)
    write_json_artifact(probe_path, _probe(contract_failure_detected=False))
    write_json_artifact(repair_path, {**_repair_pack(), "summary": {"case_count": 0}})

    assert (
        main(
            [
                "--live-diagnostic-report",
                str(live_path),
                "--contract-probe-artifact",
                str(probe_path),
                "--repair-pack-artifact",
                str(repair_path),
                "--preflight-artifact",
                str(preflight_path),
                "--output",
                str(output_path),
            ]
        )
        == 0
    )

    artifact = read_json_artifact(output_path)
    assert artifact["status"] == "websearch_contract_unblocked"
    assert artifact["selected_next_step"] == "inspect_websearch_status_packet"


def test_websearch_manager_contract_handoff_script_accepts_live_bundle_manifest(
    tmp_path: Path,
) -> None:
    from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact
    from scripts.build_accurate_intake_websearch_manager_contract_handoff import main

    preflight = _clear_preflight_artifact()
    bundle_dir = tmp_path / "bundle"
    bundle_dir.mkdir()
    bundle_paths = build_websearch_live_bundle_artifact_paths(bundle_dir)
    output_path = tmp_path / "handoff.json"

    write_json_artifact(
        bundle_paths["report"],
        _live_report(seam_status="live_diagnostic_pass", preflight_artifact=preflight),
    )
    write_json_artifact(bundle_paths["preflight"], preflight)
    write_json_artifact(
        bundle_paths["manager_contract_probe"],
        _probe(contract_failure_detected=False),
    )
    write_json_artifact(
        bundle_paths["manager_contract_repair_pack"],
        {**_repair_pack(), "summary": {"case_count": 0}},
    )
    write_json_artifact(
        bundle_paths["manifest"],
        {
            "artifact_type": "accurate_intake_websearch_live_diagnostic_bundle_manifest",
            "artifacts": {
                "report": str(bundle_paths["report"]),
                "preflight": str(bundle_paths["preflight"]),
                "manager_contract_probe": str(bundle_paths["manager_contract_probe"]),
                "manager_contract_repair_pack": str(bundle_paths["manager_contract_repair_pack"]),
            },
        },
    )

    assert (
        main(
            [
                "--live-bundle-manifest",
                str(bundle_paths["manifest"]),
                "--output",
                str(output_path),
            ]
        )
        == 0
    )

    artifact = read_json_artifact(output_path)
    assert artifact["status"] == "websearch_contract_unblocked"
    assert artifact["selected_next_step"] == "inspect_websearch_status_packet"


def test_websearch_manager_contract_handoff_script_accepts_live_bundle_dir(
    tmp_path: Path,
) -> None:
    from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact
    from scripts.build_accurate_intake_websearch_manager_contract_handoff import main

    preflight = _clear_preflight_artifact()
    bundle_dir = tmp_path / "bundle"
    bundle_dir.mkdir()
    bundle_paths = build_websearch_live_bundle_artifact_paths(bundle_dir)
    output_path = tmp_path / "handoff.json"

    write_json_artifact(
        bundle_paths["report"],
        _live_report(seam_status="live_diagnostic_pass", preflight_artifact=preflight),
    )
    write_json_artifact(bundle_paths["preflight"], preflight)
    write_json_artifact(
        bundle_paths["manager_contract_probe"],
        _probe(contract_failure_detected=False),
    )
    write_json_artifact(
        bundle_paths["manager_contract_repair_pack"],
        {**_repair_pack(), "summary": {"case_count": 0}},
    )

    assert (
        main(
            [
                "--live-bundle-dir",
                str(bundle_dir),
                "--output",
                str(output_path),
            ]
        )
        == 0
    )

    artifact = read_json_artifact(output_path)
    assert artifact["status"] == "websearch_contract_unblocked"
    assert artifact["selected_next_step"] == "inspect_websearch_status_packet"


def test_websearch_manager_contract_handoff_rejects_unexpected_sources() -> None:
    try:
        build_websearch_manager_contract_handoff(
            live_diagnostic_report={"artifact_type": "wrong"},
            contract_probe_artifact=_probe(),
            repair_pack_artifact=_repair_pack(),
        )
    except ValueError as exc:
        assert "unsupported_websearch_manager_contract_handoff_live_report" in str(exc)
    else:
        raise AssertionError("unexpected live report type must fail")

    try:
        build_websearch_manager_contract_handoff(
            live_diagnostic_report=_live_report(),
            contract_probe_artifact={"artifact_type": "wrong"},
            repair_pack_artifact=_repair_pack(),
        )
    except ValueError as exc:
        assert "unsupported_websearch_manager_contract_handoff_contract_probe" in str(exc)
    else:
        raise AssertionError("unexpected probe artifact type must fail")

    try:
        build_websearch_manager_contract_handoff(
            live_diagnostic_report=_live_report(),
            contract_probe_artifact=_probe(),
            repair_pack_artifact={"artifact_type": "wrong"},
        )
    except ValueError as exc:
        assert "unsupported_websearch_manager_contract_handoff_repair_pack" in str(exc)
    else:
        raise AssertionError("unexpected repair artifact type must fail")


def test_websearch_manager_contract_handoff_has_no_live_imports() -> None:
    source_paths = [
        Path("app/nutrition/application/websearch_manager_contract_handoff.py"),
        Path("scripts/build_accurate_intake_websearch_manager_contract_handoff.py"),
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
