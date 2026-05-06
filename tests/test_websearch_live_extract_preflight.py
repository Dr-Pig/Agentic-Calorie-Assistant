from __future__ import annotations

from pathlib import Path

from app.nutrition.application.exact_card_candidate_promotion_readiness import (
    build_exact_card_candidate_promotion_readiness,
)
from app.nutrition.application.exact_evidence_lane_policy import (
    build_exact_evidence_lane_policy_artifact,
)
from app.nutrition.application.websearch_exact_candidate_review_packet import (
    build_websearch_exact_candidate_review_packet,
)
from app.nutrition.application.websearch_extract_result_candidate_smoke import (
    build_websearch_extract_result_candidate_smoke,
)
from app.nutrition.application.websearch_grokfast_live_diagnostic_case_matrix import (
    REQUIRED_CASE_IDS,
    build_websearch_grokfast_live_diagnostic_case_matrix_artifact,
)
from app.nutrition.application.websearch_live_extract_preflight import (
    build_websearch_live_extract_preflight,
    is_websearch_live_extract_preflight_clear,
)
from app.nutrition.application.websearch_selected_extract_packet_smoke import (
    build_websearch_selected_extract_packet_smoke,
)


def _review_packet() -> dict[str, object]:
    readiness = build_exact_card_candidate_promotion_readiness(
        exact_lane_artifact=build_exact_evidence_lane_policy_artifact()
    )
    selected = build_websearch_selected_extract_packet_smoke(
        exact_card_readiness_artifact=readiness
    )
    extract_result = build_websearch_extract_result_candidate_smoke(
        selected_extract_artifact=selected
    )
    return build_websearch_exact_candidate_review_packet(
        extract_result_artifact=extract_result
    )


def test_live_extract_preflight_enables_diagnostic_only_not_truth() -> None:
    artifact = build_websearch_live_extract_preflight(
        exact_review_packet_artifact=_review_packet(),
    )

    assert artifact["artifact_type"] == "accurate_intake_websearch_live_extract_preflight_v1"
    assert artifact["status"] == "pass"
    assert artifact["classification"] == "deterministic_live_extract_preflight_only"
    assert artifact["ready_for_live_extract_diagnostic"] is True
    assert artifact["ready_for_runtime_truth"] is False
    assert artifact["live_websearch_used"] is False
    assert artifact["live_extract_used"] is False
    assert artifact["live_provider_used"] is False
    assert artifact["runtime_truth_changed"] is False
    assert artifact["runtime_mutation_allowed"] is False
    assert artifact["readiness_claimed"] is False
    assert artifact["summary"]["review_packet_count"] == 6
    assert artifact["summary"]["ready_for_runtime_truth_count"] == 0
    assert artifact["summary"]["case_matrix_case_count"] == len(REQUIRED_CASE_IDS)
    assert artifact["summary"]["case_matrix_fixed_required_cases"] is True
    assert artifact["summary"]["case_matrix_negative_case_count"] == 4
    assert artifact["summary"]["case_matrix_modifier_guard_cases"] == 1
    assert artifact["summary"]["case_matrix_live_provider_invoked"] is False
    assert artifact["summary"]["case_matrix_websearch_invoked"] is False
    assert artifact["next_required_slice"] == "grokfast_websearch_packet_live_diagnostic"
    assert is_websearch_live_extract_preflight_clear(artifact) is True


def test_live_extract_preflight_contract_requires_explicit_live_flag_and_cache() -> None:
    artifact = build_websearch_live_extract_preflight(
        exact_review_packet_artifact=_review_packet(),
    )
    contract = artifact["diagnostic_contract"]

    assert contract["live_call_allowed_by_this_artifact"] is False
    assert contract["requires_explicit_allow_live_flag"] is True
    assert contract["max_search_attempts"] == 2
    assert contract["max_extract_urls_per_case"] == 1
    assert contract["max_chunks_per_source"] == 3
    assert contract["cache_required"] is True
    assert contract["raw_content_allowed_in_manager_context"] is False
    assert contract["extract_result_role"] == "review_candidate_only"
    assert contract["ledger_mutation_allowed"] is False
    assert contract["exact_card_creation_allowed"] is False
    assert artifact["review_packet_refs"][0]["packet_digest"]


def test_live_extract_preflight_blocks_review_packet_truth_leak() -> None:
    review_packet = _review_packet()
    review_packet["review_packets"][0]["runtime_truth_allowed"] = True
    review_packet["summary"]["runtime_truth_allowed_count"] = 1

    artifact = build_websearch_live_extract_preflight(
        exact_review_packet_artifact=review_packet,
    )

    assert artifact["status"] == "blocked"
    assert "exact_review_packet_artifact_summary_runtime_truth_allowed" in artifact["blockers"]
    assert "exact_review_packet_allowed_runtime_truth" in artifact["blockers"]
    assert artifact["ready_for_live_extract_diagnostic"] is False


def test_live_extract_preflight_blocks_missing_or_ad_hoc_case_matrix() -> None:
    artifact = build_websearch_live_extract_preflight(
        exact_review_packet_artifact=_review_packet(),
        case_matrix_artifact={},
    )

    assert artifact["status"] == "blocked"
    assert "unsupported_websearch_grokfast_case_matrix_artifact" in artifact["blockers"]
    assert "websearch_grokfast_case_matrix_required_case_order_mismatch" in artifact[
        "blockers"
    ]
    assert artifact["ready_for_live_extract_diagnostic"] is False
    assert is_websearch_live_extract_preflight_clear(artifact) is False


def test_live_extract_preflight_blocks_case_matrix_overfit_or_live_claims() -> None:
    case_matrix = build_websearch_grokfast_live_diagnostic_case_matrix_artifact()
    case_matrix["cases"] = case_matrix["cases"][:1]
    case_matrix["summary"]["case_count"] = 1
    case_matrix["summary"]["negative_case_count"] = 0
    case_matrix["summary"]["modifier_guard_cases"] = 0
    case_matrix["live_provider_invoked"] = True
    case_matrix["websearch_invoked"] = True

    artifact = build_websearch_live_extract_preflight(
        exact_review_packet_artifact=_review_packet(),
        case_matrix_artifact=case_matrix,
    )

    assert artifact["status"] == "blocked"
    assert "websearch_grokfast_case_matrix_required_case_order_mismatch" in artifact[
        "blockers"
    ]
    assert "websearch_grokfast_case_matrix_missing_negative_cases" in artifact["blockers"]
    assert "websearch_grokfast_case_matrix_missing_modifier_guard" in artifact["blockers"]
    assert "websearch_grokfast_case_matrix_invoked_live_provider" in artifact["blockers"]
    assert "websearch_grokfast_case_matrix_invoked_websearch" in artifact["blockers"]


def test_live_extract_preflight_sanitizes_malformed_case_matrix_flags() -> None:
    case_matrix = build_websearch_grokfast_live_diagnostic_case_matrix_artifact()
    case_matrix["live_provider_invoked"] = "raw_response_excerpt forbidden provider_trace"
    case_matrix["websearch_invoked"] = "raw_response_excerpt forbidden"

    artifact = build_websearch_live_extract_preflight(
        exact_review_packet_artifact=_review_packet(),
        case_matrix_artifact=case_matrix,
    )
    serialized = str(artifact)

    assert artifact["status"] == "blocked"
    assert "websearch_grokfast_case_matrix_invoked_live_provider" in artifact["blockers"]
    assert "websearch_grokfast_case_matrix_invoked_websearch" in artifact["blockers"]
    assert artifact["summary"]["case_matrix_live_provider_invoked"] is True
    assert artifact["summary"]["case_matrix_websearch_invoked"] is True
    assert "raw_response_excerpt" not in serialized
    assert "provider_trace" not in serialized
    assert "forbidden" not in serialized


def test_live_extract_preflight_blocks_malformed_case_matrix_summary_counts() -> None:
    case_matrix = build_websearch_grokfast_live_diagnostic_case_matrix_artifact()
    case_matrix["summary"]["case_count"] = "raw_response_excerpt"
    case_matrix["summary"]["exact_candidate_cases"] = "provider_trace"
    case_matrix["summary"]["negative_case_count"] = "forbidden"
    case_matrix["summary"]["modifier_guard_cases"] = "raw_response_excerpt"
    case_matrix["summary"]["runtime_truth_allowed_cases"] = "provider_trace"
    case_matrix["summary"]["websearch_invoked_cases"] = "forbidden"
    case_matrix["summary"]["live_provider_invoked_cases"] = "raw_response_excerpt"

    artifact = build_websearch_live_extract_preflight(
        exact_review_packet_artifact=_review_packet(),
        case_matrix_artifact=case_matrix,
    )
    serialized = str(artifact)

    assert artifact["status"] == "blocked"
    assert "websearch_grokfast_case_matrix_case_count_mismatch" in artifact["blockers"]
    assert "websearch_grokfast_case_matrix_missing_exact_candidate" in artifact["blockers"]
    assert "websearch_grokfast_case_matrix_missing_negative_cases" in artifact["blockers"]
    assert "websearch_grokfast_case_matrix_missing_modifier_guard" in artifact["blockers"]
    assert "websearch_grokfast_case_matrix_runtime_truth_allowed" in artifact["blockers"]
    assert "websearch_grokfast_case_matrix_websearch_invoked_cases" in artifact["blockers"]
    assert "websearch_grokfast_case_matrix_live_provider_invoked_cases" in artifact[
        "blockers"
    ]
    assert artifact["summary"]["case_matrix_case_count"] == len(REQUIRED_CASE_IDS)
    assert artifact["summary"]["case_matrix_negative_case_count"] == 0
    assert artifact["summary"]["case_matrix_modifier_guard_cases"] == 0
    assert "raw_response_excerpt" not in serialized
    assert "provider_trace" not in serialized
    assert "forbidden" not in serialized


def test_live_extract_preflight_blocks_case_level_matrix_overclaims() -> None:
    case_matrix = build_websearch_grokfast_live_diagnostic_case_matrix_artifact()
    case = case_matrix["cases"][0]
    case["runtime_truth_allowed"] = True
    case["ledger_mutation_allowed"] = True
    case["websearch_candidate_only"] = False
    case["snippet_truth_allowed"] = True
    case["live_provider_invoked"] = True
    case["websearch_invoked"] = True
    case["raw_content_allowed_in_manager_context"] = True
    case["must_not_happen"] = ["exact_card_created"]

    artifact = build_websearch_live_extract_preflight(
        exact_review_packet_artifact=_review_packet(),
        case_matrix_artifact=case_matrix,
    )

    assert artifact["status"] == "blocked"
    assert (
        "websearch_grokfast_case_matrix.websearch_official_exact_candidate.allowed_runtime_truth"
        in artifact["blockers"]
    )
    assert (
        "websearch_grokfast_case_matrix.websearch_official_exact_candidate.allowed_ledger_mutation"
        in artifact["blockers"]
    )
    assert (
        "websearch_grokfast_case_matrix.websearch_official_exact_candidate.not_candidate_only"
        in artifact["blockers"]
    )
    assert (
        "websearch_grokfast_case_matrix.websearch_official_exact_candidate.allowed_snippet_truth"
        in artifact["blockers"]
    )
    assert (
        "websearch_grokfast_case_matrix.websearch_official_exact_candidate.invoked_live_provider"
        in artifact["blockers"]
    )
    assert (
        "websearch_grokfast_case_matrix.websearch_official_exact_candidate.invoked_websearch"
        in artifact["blockers"]
    )
    assert (
        "websearch_grokfast_case_matrix.websearch_official_exact_candidate.allowed_raw_content"
        in artifact["blockers"]
    )
    assert (
        "websearch_grokfast_case_matrix.websearch_official_exact_candidate.missing_snippet_guard"
        in artifact["blockers"]
    )


def test_live_extract_preflight_blocks_case_matrix_missing_non_claims() -> None:
    case_matrix = build_websearch_grokfast_live_diagnostic_case_matrix_artifact()
    case_matrix["non_claims"] = ["not_full_self_use_gate"]

    artifact = build_websearch_live_extract_preflight(
        exact_review_packet_artifact=_review_packet(),
        case_matrix_artifact=case_matrix,
    )

    assert artifact["status"] == "blocked"
    assert (
        "websearch_grokfast_case_matrix_missing_non_claim.not_websearch_runtime_truth_gate"
        in artifact["blockers"]
    )
    assert (
        "websearch_grokfast_case_matrix_missing_non_claim.not_exact_card_promotion_gate"
        in artifact["blockers"]
    )


def test_live_extract_preflight_blocks_review_artifact_live_or_readiness_overclaim() -> None:
    review_packet = _review_packet()
    review_packet["live_extract_used"] = True
    review_packet["readiness_claimed"] = True

    artifact = build_websearch_live_extract_preflight(
        exact_review_packet_artifact=review_packet,
    )

    assert artifact["status"] == "blocked"
    assert "exact_review_packet_artifact_used_live_extract" in artifact["blockers"]
    assert "exact_review_packet_artifact_claimed_readiness" in artifact["blockers"]


def test_live_extract_preflight_sanitizes_source_artifact_type() -> None:
    artifact = build_websearch_live_extract_preflight(
        exact_review_packet_artifact={
            "artifact_type": "raw_response_excerpt forbidden",
            "status": "pass",
            "runtime_truth_changed": False,
            "runtime_mutation_allowed": False,
            "live_websearch_used": False,
            "live_extract_used": False,
            "live_provider_used": False,
            "readiness_claimed": False,
            "summary": {
                "runtime_truth_allowed_count": 0,
                "exact_card_created_count": 0,
                "approval_allowed_count": 0,
            },
        },
    )

    serialized = str(artifact)
    assert artifact["status"] == "blocked"
    assert (
        artifact["source_artifacts"]["exact_review_packet_artifact_type"]
        == "unsupported_exact_review_packet_artifact"
    )
    assert "raw_response_excerpt" not in serialized
    assert "forbidden" not in serialized


def test_live_extract_preflight_blocks_leaky_review_packet_refs() -> None:
    review_packet = _review_packet()
    packet = review_packet["review_packets"][0]
    packet["packet_id"] = "raw_response_excerpt"
    packet["source_url"] = "raw_response_excerpt forbidden"
    packet["canonical_name"] = "raw_response_excerpt forbidden"
    packet["matched_name"] = "raw_response_excerpt forbidden"

    artifact = build_websearch_live_extract_preflight(
        exact_review_packet_artifact=review_packet,
    )
    serialized = str(artifact)

    assert artifact["status"] == "blocked"
    assert artifact["review_packet_refs"] == []
    assert "exact_review_packet_invalid_source_url" in artifact["blockers"]
    assert "exact_review_packet_invalid_packet_id" in artifact["blockers"]
    assert "exact_review_packet_leaky_canonical_name" in artifact["blockers"]
    assert "raw_response_excerpt" not in serialized
    assert "forbidden" not in serialized


def test_live_extract_preflight_blocks_unknown_marker_free_review_refs() -> None:
    review_packet = _review_packet()
    packet = review_packet["review_packets"][0]
    packet["packet_id"] = "pkt_exact_card_review_private123"
    packet["source_url"] = "https://private-payload-token.example/menu"
    packet["canonical_name"] = "private payload token"
    packet["matched_name"] = "private payload token"

    artifact = build_websearch_live_extract_preflight(
        exact_review_packet_artifact=review_packet,
    )
    serialized = str(artifact)

    assert artifact["status"] == "blocked"
    assert artifact["review_packet_refs"] == []
    assert "private-payload-token" not in serialized
    assert "private payload token" not in serialized
    assert "exact_review_packet_invalid_source_url" in artifact["blockers"]
    assert "exact_review_packet_invalid_packet_id" in artifact["blockers"]


def test_live_extract_preflight_blocks_allowed_host_unknown_path_and_serving() -> None:
    review_packet = _review_packet()
    packet = review_packet["review_packets"][0]
    packet["source_url"] = "https://milksha.example/menu/private_payload_token"
    packet["review_fields"]["serving_basis_candidate"] = "private_payload_serving"

    artifact = build_websearch_live_extract_preflight(
        exact_review_packet_artifact=review_packet,
    )
    serialized = str(artifact)

    assert artifact["status"] == "blocked"
    assert artifact["review_packet_refs"] == []
    assert "private_payload" not in serialized
    assert "exact_review_packet_invalid_source_url" in artifact["blockers"]
    assert "exact_review_packet_invalid_serving_basis_candidate" in artifact["blockers"]


def test_live_extract_preflight_blocks_missing_kcal_value_candidate() -> None:
    review_packet = _review_packet()
    review_packet["review_packets"][0]["review_fields"].pop("kcal_value_candidate")

    artifact = build_websearch_live_extract_preflight(
        exact_review_packet_artifact=review_packet,
    )

    assert artifact["status"] == "blocked"
    assert "exact_review_packet_missing_kcal_candidate" in artifact["blockers"]
    assert artifact["ready_for_live_extract_diagnostic"] is False


def test_live_extract_preflight_script_roundtrip(tmp_path: Path) -> None:
    from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact
    from scripts.build_accurate_intake_websearch_live_extract_preflight import main

    review_packet_path = tmp_path / "review_packet.json"
    case_matrix_path = tmp_path / "case_matrix.json"
    output = tmp_path / "preflight.json"
    write_json_artifact(review_packet_path, _review_packet())
    write_json_artifact(
        case_matrix_path,
        build_websearch_grokfast_live_diagnostic_case_matrix_artifact(),
    )

    assert (
        main(
            [
                "--review-packet-artifact",
                str(review_packet_path),
                "--case-matrix-artifact",
                str(case_matrix_path),
                "--output",
                str(output),
            ]
        )
        == 0
    )

    artifact = read_json_artifact(output)
    assert artifact["artifact_type"] == "accurate_intake_websearch_live_extract_preflight_v1"
    assert artifact["status"] == "pass"
