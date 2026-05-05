from __future__ import annotations

from pathlib import Path

from app.nutrition.application.websearch_exact_card_manifest_review_packet import (
    build_websearch_exact_card_manifest_review_packet,
)


def _manifest_diag(*, status: str = "pass_candidate_manifest_diagnostic") -> dict:
    candidates = [
        {
            "manifest_candidate_id": "exact_card_manifest_candidate_123",
            "source_request_candidate_id": "official-drink-card",
            "candidate_role": "exact_card_manifest_candidate_only",
            "truth_level": "manifest_candidate",
            "source_class": "official_brand_chain_page",
            "approval_id": "batch-policy-1",
            "runtime_truth_allowed": False,
            "websearch_runtime_truth_allowed": False,
            "packet_ready_truth_allowed": False,
            "promotion_allowed": False,
            "exact_card_created": False,
            "runtime_mutation_allowed": False,
            "raw_content_included": False,
            "raw_source_rows_included": False,
            "manager_visible_role": "candidate_manifest_only_not_manager_truth",
            "required_before_runtime_truth": [
                "exact_card_record_creation_slice",
                "exact_card_runtime_gate",
                "packetizer_contract_review",
            ],
        }
    ]
    return {
        "artifact_type": (
            "accurate_intake_websearch_exact_card_candidate_manifest_diagnostic_v1"
        ),
        "status": status,
        "classification": (
            "deterministic_exact_card_candidate_manifest_diagnostic_only"
        ),
        "claim_scope": "websearch_exact_card_candidate_manifest_without_truth",
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
        "manifest_candidates": candidates
        if status == "pass_candidate_manifest_diagnostic"
        else [],
        "rejected_requests": [],
        "summary": {
            "promotion_request_count": 1
            if status == "pass_candidate_manifest_diagnostic"
            else 0,
            "manifest_candidate_count": 1
            if status == "pass_candidate_manifest_diagnostic"
            else 0,
            "rejected_request_count": 0,
            "runtime_truth_allowed_count": 0,
            "exact_card_created_count": 0,
            "promotion_allowed_count": 0,
        },
        "next_required_slice": (
            "websearch_exact_card_manifest_candidate_review_packet"
            if status == "pass_candidate_manifest_diagnostic"
            else "inspect_websearch_exact_card_candidate_manifest_blockers"
        ),
    }


def test_manifest_review_packet_emits_review_only_packets() -> None:
    artifact = build_websearch_exact_card_manifest_review_packet(
        manifest_diagnostic=_manifest_diag()
    )

    assert (
        artifact["artifact_type"]
        == "accurate_intake_websearch_exact_card_manifest_review_packet_v1"
    )
    assert artifact["status"] == "pass_manifest_review_packet"
    assert artifact["classification"] == "deterministic_exact_card_manifest_review_packet_only"
    assert artifact["runtime_truth_changed"] is False
    assert artifact["mutation_changed"] is False
    assert artifact["runtime_mutation_allowed"] is False
    assert artifact["websearch_runtime_truth_allowed"] is False
    assert artifact["exact_card_created"] is False
    assert artifact["summary"]["review_packet_count"] == 1
    assert artifact["summary"]["runtime_truth_allowed_count"] == 0
    assert artifact["next_required_slice"] == "websearch_exact_card_manifest_no_runtime_wall"


def test_manifest_review_packet_is_non_runtime_and_review_scoped() -> None:
    artifact = build_websearch_exact_card_manifest_review_packet(
        manifest_diagnostic=_manifest_diag()
    )
    packet = artifact["review_packets"][0]

    assert packet["packet_type"] == "ExactCardManifestReviewPacket"
    assert packet["packet_role"] == "review_only_exact_card_manifest_candidate"
    assert packet["truth_level"] == "review_candidate"
    assert packet["source_manifest_candidate_id"] == "exact_card_manifest_candidate_123"
    assert packet["approval_checklist"] == {
        "exact_card_record_creation_slice_required": True,
        "exact_card_runtime_gate_required": True,
        "packetizer_contract_review_required": True,
    }
    assert packet["runtime_truth_allowed"] is False
    assert packet["websearch_runtime_truth_allowed"] is False
    assert packet["packet_ready_truth_allowed"] is False
    assert packet["promotion_allowed"] is False
    assert packet["exact_card_created"] is False
    assert packet["runtime_mutation_allowed"] is False
    assert packet["raw_content_included"] is False
    assert packet["raw_source_rows_included"] is False


def test_manifest_review_packet_blocks_dirty_manifest_diagnostic() -> None:
    artifact = build_websearch_exact_card_manifest_review_packet(
        manifest_diagnostic=_manifest_diag(status="blocked")
    )

    assert artifact["status"] == "blocked"
    assert "manifest_diagnostic_not_pass:blocked" in artifact["blockers"]
    assert artifact["review_packets"] == []


def test_manifest_review_packet_blocks_manifest_overclaims() -> None:
    expected = {
        "runtime_truth_changed": "manifest_diagnostic_changed_runtime_truth",
        "mutation_changed": "manifest_diagnostic_changed_mutation",
        "live_websearch_used": "manifest_diagnostic_used_live_websearch",
        "runtime_mutation_allowed": "manifest_diagnostic_allowed_runtime_mutation",
        "websearch_runtime_truth_allowed": "manifest_diagnostic_allowed_websearch_runtime_truth",
        "exact_card_created": "manifest_diagnostic_created_exact_card",
        "readiness_claimed": "manifest_diagnostic_claimed_readiness",
    }
    for key, blocker in expected.items():
        manifest = _manifest_diag()
        manifest[key] = 1
        artifact = build_websearch_exact_card_manifest_review_packet(
            manifest_diagnostic=manifest
        )
        assert artifact["status"] == "blocked"
        assert blocker in artifact["blockers"]
        assert artifact["review_packets"] == []


def test_manifest_review_packet_blocks_candidate_truth_or_raw_leaks() -> None:
    expected = {
        "runtime_truth_allowed": "manifest_candidate_allowed_runtime_truth",
        "websearch_runtime_truth_allowed": "manifest_candidate_allowed_websearch_runtime_truth",
        "packet_ready_truth_allowed": "manifest_candidate_allowed_packet_ready_truth",
        "promotion_allowed": "manifest_candidate_allowed_promotion",
        "exact_card_created": "manifest_candidate_created_exact_card",
        "runtime_mutation_allowed": "manifest_candidate_allowed_runtime_mutation",
        "raw_content_included": "manifest_candidate_included_raw_content",
        "raw_source_rows_included": "manifest_candidate_included_raw_source_rows",
    }
    for key, blocker in expected.items():
        manifest = _manifest_diag()
        manifest["manifest_candidates"][0][key] = True
        artifact = build_websearch_exact_card_manifest_review_packet(
            manifest_diagnostic=manifest
        )
        assert artifact["status"] == "blocked"
        assert blocker in artifact["blockers"]
        assert artifact["review_packets"] == []


def test_manifest_review_packet_blocks_nested_candidate_leaks() -> None:
    manifest = _manifest_diag()
    manifest["manifest_candidates"][0]["extra"] = {
        "nested": {
            "runtime_truth_allowed": True,
            "source_live_websearch_used": True,
        }
    }
    artifact = build_websearch_exact_card_manifest_review_packet(
        manifest_diagnostic=manifest
    )

    assert artifact["status"] == "blocked"
    assert "manifest_candidate_nested_runtime_truth_allowed" in artifact["blockers"]
    assert "manifest_candidate_nested_source_live_websearch_used" in artifact["blockers"]
    assert artifact["review_packets"] == []


def test_manifest_review_packet_blocks_nested_raw_payload_keys() -> None:
    manifest = _manifest_diag()
    manifest["manifest_candidates"][0]["source_class"] = {
        "raw_content": "...",
        "raw_source_rows": [{"row": 1}],
    }
    artifact = build_websearch_exact_card_manifest_review_packet(
        manifest_diagnostic=manifest
    )

    assert artifact["status"] == "blocked"
    assert "manifest_candidate_nested_raw_content" in artifact["blockers"]
    assert "manifest_candidate_nested_raw_source_rows" in artifact["blockers"]
    assert artifact["review_packets"] == []


def test_manifest_review_packet_blocks_malformed_candidates() -> None:
    manifest = _manifest_diag()
    manifest["manifest_candidates"].append("bad")
    artifact = build_websearch_exact_card_manifest_review_packet(
        manifest_diagnostic=manifest
    )

    assert artifact["status"] == "blocked"
    assert "manifest_candidate_malformed" in artifact["blockers"]
    assert artifact["review_packets"] == []


def test_manifest_review_packet_blocks_unsupported_manifest_without_raise() -> None:
    artifact = build_websearch_exact_card_manifest_review_packet(
        manifest_diagnostic={"artifact_type": "bad"}
    )

    assert artifact["status"] == "blocked"
    assert "unsupported_manifest_diagnostic_artifact" in artifact["blockers"]
    assert artifact["review_packets"] == []


def test_manifest_review_packet_blocks_non_dict_manifest_without_raise() -> None:
    artifact = build_websearch_exact_card_manifest_review_packet(
        manifest_diagnostic=["bad"]  # type: ignore[arg-type]
    )

    assert artifact["status"] == "blocked"
    assert "manifest_diagnostic_not_dict" in artifact["blockers"]
    assert artifact["review_packets"] == []
    assert artifact["source_artifacts"]["manifest_diagnostic_type"] == "<non_dict>"


def test_manifest_review_packet_sanitizes_unsupported_artifact_type_payload() -> None:
    artifact = build_websearch_exact_card_manifest_review_packet(
        manifest_diagnostic={"artifact_type": {"raw_content": "..."}}
    )

    assert artifact["status"] == "blocked"
    assert "unsupported_manifest_diagnostic_artifact" in artifact["blockers"]
    assert artifact["review_packets"] == []
    assert artifact["source_artifacts"]["manifest_diagnostic_type"] == "<non_scalar>"


def test_manifest_review_packet_blocks_malformed_summary_counts_without_raise() -> None:
    manifest = _manifest_diag()
    manifest["summary"]["runtime_truth_allowed_count"] = "nan"
    artifact = build_websearch_exact_card_manifest_review_packet(
        manifest_diagnostic=manifest
    )

    assert artifact["status"] == "blocked"
    assert "manifest_diagnostic_runtime_truth_allowed_count_malformed" in artifact[
        "blockers"
    ]
    assert artifact["review_packets"] == []


def test_manifest_review_packet_script_roundtrip(tmp_path: Path) -> None:
    from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact
    from scripts.build_accurate_intake_websearch_exact_card_manifest_review_packet import (
        main,
    )

    manifest_path = tmp_path / "manifest.json"
    output = tmp_path / "review_packet.json"
    write_json_artifact(manifest_path, _manifest_diag())

    assert main(["--manifest-diagnostic", str(manifest_path), "--output", str(output)]) == 0

    artifact = read_json_artifact(output)
    assert (
        artifact["artifact_type"]
        == "accurate_intake_websearch_exact_card_manifest_review_packet_v1"
    )
    assert artifact["status"] == "pass_manifest_review_packet"


def test_manifest_review_packet_has_no_live_or_shared_contract_imports() -> None:
    source_paths = [
        Path("app/nutrition/application/websearch_exact_card_manifest_review_packet.py"),
        Path("scripts/build_accurate_intake_websearch_exact_card_manifest_review_packet.py"),
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
