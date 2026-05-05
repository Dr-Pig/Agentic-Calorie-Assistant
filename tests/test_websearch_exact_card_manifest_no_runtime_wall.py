from __future__ import annotations

from pathlib import Path

from app.nutrition.application.websearch_exact_card_manifest_no_runtime_wall import (
    build_websearch_exact_card_manifest_no_runtime_wall,
)


def _review_packet_artifact(*, status: str = "pass_manifest_review_packet") -> dict:
    packets = [
        {
            "packet_id": "pkt_exact_card_manifest_review_123",
            "packet_type": "ExactCardManifestReviewPacket",
            "packet_role": "review_only_exact_card_manifest_candidate",
            "truth_level": "review_candidate",
            "source_type": "websearch_exact_card_manifest_candidate",
            "source_manifest_candidate_id": "exact_card_manifest_candidate_123",
            "source_request_candidate_id": "official-drink-card",
            "source_class": "official_brand_chain_page",
            "approval_id": "batch-policy-1",
            "approval_checklist": {
                "exact_card_record_creation_slice_required": True,
                "exact_card_runtime_gate_required": True,
                "packetizer_contract_review_required": True,
            },
            "runtime_truth_allowed": False,
            "websearch_runtime_truth_allowed": False,
            "packet_ready_truth_allowed": False,
            "promotion_allowed": False,
            "exact_card_created": False,
            "runtime_mutation_allowed": False,
            "raw_content_included": False,
            "raw_source_rows_included": False,
            "manager_visible_role": "manifest_review_packet_only_not_manager_truth",
        }
    ]
    return {
        "artifact_type": "accurate_intake_websearch_exact_card_manifest_review_packet_v1",
        "status": status,
        "classification": "deterministic_exact_card_manifest_review_packet_only",
        "claim_scope": "websearch_exact_card_manifest_review_packet_without_truth",
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
        "review_packets": packets if status == "pass_manifest_review_packet" else [],
        "summary": {
            "review_packet_count": 1 if status == "pass_manifest_review_packet" else 0,
            "runtime_truth_allowed_count": 0,
            "exact_card_created_count": 0,
            "promotion_allowed_count": 0,
        },
        "next_required_slice": (
            "websearch_exact_card_manifest_no_runtime_wall"
            if status == "pass_manifest_review_packet"
            else "inspect_websearch_exact_card_manifest_review_packet_blockers"
        ),
    }


def test_manifest_no_runtime_wall_blocks_runtime_use_by_design() -> None:
    artifact = build_websearch_exact_card_manifest_no_runtime_wall(
        manifest_review_packet=_review_packet_artifact()
    )

    assert (
        artifact["artifact_type"]
        == "accurate_intake_websearch_exact_card_manifest_no_runtime_wall_v1"
    )
    assert artifact["status"] == "blocked_runtime_truth_by_design"
    assert artifact["classification"] == "deterministic_exact_card_manifest_no_runtime_wall"
    assert artifact["runtime_truth_changed"] is False
    assert artifact["mutation_changed"] is False
    assert artifact["runtime_mutation_allowed"] is False
    assert artifact["websearch_runtime_truth_allowed"] is False
    assert artifact["exact_card_created"] is False
    assert artifact["summary"]["blocked_review_packet_count"] == 1
    assert artifact["blockers"] == ["exact_card_manifest_runtime_truth_not_allowed"]
    assert artifact["next_required_slice"] == "websearch_exact_card_record_creation_contract_probe"


def test_manifest_no_runtime_wall_emits_stop_records_without_truth() -> None:
    artifact = build_websearch_exact_card_manifest_no_runtime_wall(
        manifest_review_packet=_review_packet_artifact()
    )
    record = artifact["no_runtime_wall_records"][0]

    assert record["wall_role"] == "manifest_candidate_runtime_truth_stop"
    assert record["source_review_packet_id"] == "pkt_exact_card_manifest_review_123"
    assert record["runtime_truth_allowed"] is False
    assert record["websearch_runtime_truth_allowed"] is False
    assert record["packet_ready_truth_allowed"] is False
    assert record["promotion_allowed"] is False
    assert record["exact_card_created"] is False
    assert record["runtime_mutation_allowed"] is False
    assert record["raw_content_included"] is False
    assert record["raw_source_rows_included"] is False
    assert record["required_before_runtime_truth"] == [
        "exact_card_record_creation_contract_probe",
        "exact_card_record_creation_slice",
        "exact_card_runtime_gate",
        "packetizer_contract_review",
    ]


def test_manifest_no_runtime_wall_blocks_dirty_review_packet_artifact() -> None:
    artifact = build_websearch_exact_card_manifest_no_runtime_wall(
        manifest_review_packet=_review_packet_artifact(status="blocked")
    )

    assert artifact["status"] == "blocked"
    assert "manifest_review_packet_not_pass:blocked" in artifact["blockers"]
    assert artifact["no_runtime_wall_records"] == []


def test_manifest_no_runtime_wall_blocks_artifact_overclaims() -> None:
    expected = {
        "runtime_truth_changed": "manifest_review_packet_changed_runtime_truth",
        "mutation_changed": "manifest_review_packet_changed_mutation",
        "live_websearch_used": "manifest_review_packet_used_live_websearch",
        "runtime_mutation_allowed": "manifest_review_packet_allowed_runtime_mutation",
        "websearch_runtime_truth_allowed": "manifest_review_packet_allowed_websearch_runtime_truth",
        "exact_card_created": "manifest_review_packet_created_exact_card",
        "readiness_claimed": "manifest_review_packet_claimed_readiness",
    }
    for key, blocker in expected.items():
        packet_artifact = _review_packet_artifact()
        packet_artifact[key] = 1
        artifact = build_websearch_exact_card_manifest_no_runtime_wall(
            manifest_review_packet=packet_artifact
        )
        assert artifact["status"] == "blocked"
        assert blocker in artifact["blockers"]
        assert artifact["no_runtime_wall_records"] == []


def test_manifest_no_runtime_wall_blocks_malformed_or_missing_summary() -> None:
    for bad_summary in ("bad", [], None):
        packet_artifact = _review_packet_artifact()
        if bad_summary is None:
            packet_artifact.pop("summary")
        else:
            packet_artifact["summary"] = bad_summary
        artifact = build_websearch_exact_card_manifest_no_runtime_wall(
            manifest_review_packet=packet_artifact
        )
        assert artifact["status"] == "blocked"
        assert "manifest_review_packet_summary_malformed" in artifact["blockers"]
        assert artifact["no_runtime_wall_records"] == []


def test_manifest_no_runtime_wall_blocks_malformed_summary_counts() -> None:
    keys = [
        "runtime_truth_allowed_count",
        "exact_card_created_count",
        "promotion_allowed_count",
    ]
    for key in keys:
        for bad_count in ([], {}, None, 0.5, False):
            packet_artifact = _review_packet_artifact()
            packet_artifact["summary"][key] = bad_count
            artifact = build_websearch_exact_card_manifest_no_runtime_wall(
                manifest_review_packet=packet_artifact
            )
            assert artifact["status"] == "blocked"
            assert f"manifest_review_packet_{key}_malformed" in artifact["blockers"]
            assert artifact["no_runtime_wall_records"] == []

        packet_artifact = _review_packet_artifact()
        packet_artifact["summary"].pop(key)
        artifact = build_websearch_exact_card_manifest_no_runtime_wall(
            manifest_review_packet=packet_artifact
        )
        assert artifact["status"] == "blocked"
        assert f"manifest_review_packet_{key}_malformed" in artifact["blockers"]
        assert artifact["no_runtime_wall_records"] == []


def test_manifest_no_runtime_wall_blocks_review_packet_truth_or_raw_leaks() -> None:
    expected = {
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
        packet_artifact = _review_packet_artifact()
        packet_artifact["review_packets"][0][key] = True
        artifact = build_websearch_exact_card_manifest_no_runtime_wall(
            manifest_review_packet=packet_artifact
        )
        assert artifact["status"] == "blocked"
        assert blocker in artifact["blockers"]
        assert artifact["no_runtime_wall_records"] == []


def test_manifest_no_runtime_wall_blocks_nested_raw_payload_leaks() -> None:
    packet_artifact = _review_packet_artifact()
    packet_artifact["review_packets"][0]["source_class"] = {
        "raw_content": "...",
        "raw_source_rows": [{"row": 1}],
    }
    artifact = build_websearch_exact_card_manifest_no_runtime_wall(
        manifest_review_packet=packet_artifact
    )

    assert artifact["status"] == "blocked"
    assert "review_packet_nested_raw_content" in artifact["blockers"]
    assert "review_packet_nested_raw_source_rows" in artifact["blockers"]
    assert artifact["no_runtime_wall_records"] == []


def test_manifest_no_runtime_wall_blocks_category_equivalent_artifact_leaks() -> None:
    expected = {
        "runtime_truth": "manifest_review_packet_nested_runtime_truth",
        "exact_card": "manifest_review_packet_nested_exact_card",
        "live_provider_response": "manifest_review_packet_nested_live_provider_response",
        "shared_contract_patch": "manifest_review_packet_nested_shared_contract_patch",
    }
    for key, blocker in expected.items():
        packet_artifact = _review_packet_artifact()
        packet_artifact["metadata"] = {key: {"unsafe": True}}
        artifact = build_websearch_exact_card_manifest_no_runtime_wall(
            manifest_review_packet=packet_artifact
        )
        assert artifact["status"] == "blocked"
        assert blocker in artifact["blockers"]
        assert artifact["no_runtime_wall_records"] == []


def test_manifest_no_runtime_wall_blocks_category_equivalent_review_packet_leaks() -> None:
    expected = {
        "runtime_truth": "review_packet_nested_runtime_truth",
        "exact_card": "review_packet_nested_exact_card",
        "live_provider_response": "review_packet_nested_live_provider_response",
        "shared_contract_patch": "review_packet_nested_shared_contract_patch",
    }
    for key, blocker in expected.items():
        packet_artifact = _review_packet_artifact()
        packet_artifact["review_packets"][0]["nested_payload"] = {key: {"unsafe": True}}
        artifact = build_websearch_exact_card_manifest_no_runtime_wall(
            manifest_review_packet=packet_artifact
        )
        assert artifact["status"] == "blocked"
        assert blocker in artifact["blockers"]
        assert artifact["no_runtime_wall_records"] == []


def test_manifest_no_runtime_wall_blocks_malformed_review_packets() -> None:
    packet_artifact = _review_packet_artifact()
    packet_artifact["review_packets"].append("bad")
    artifact = build_websearch_exact_card_manifest_no_runtime_wall(
        manifest_review_packet=packet_artifact
    )

    assert artifact["status"] == "blocked"
    assert "review_packet_malformed" in artifact["blockers"]
    assert artifact["no_runtime_wall_records"] == []


def test_manifest_no_runtime_wall_blocks_non_dict_artifact_without_raise() -> None:
    artifact = build_websearch_exact_card_manifest_no_runtime_wall(
        manifest_review_packet=["bad"]  # type: ignore[arg-type]
    )

    assert artifact["status"] == "blocked"
    assert "manifest_review_packet_not_dict" in artifact["blockers"]
    assert artifact["source_artifacts"]["manifest_review_packet_type"] == "<non_dict>"


def test_manifest_no_runtime_wall_sanitizes_artifact_type_payload() -> None:
    artifact = build_websearch_exact_card_manifest_no_runtime_wall(
        manifest_review_packet={"artifact_type": {"raw_content": "..."}}
    )

    assert artifact["status"] == "blocked"
    assert "unsupported_manifest_review_packet_artifact" in artifact["blockers"]
    assert artifact["source_artifacts"]["manifest_review_packet_type"] == "<non_scalar>"


def test_manifest_no_runtime_wall_script_roundtrip(tmp_path: Path) -> None:
    from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact
    from scripts.build_accurate_intake_websearch_exact_card_manifest_no_runtime_wall import (
        main,
    )

    review_path = tmp_path / "manifest_review_packet.json"
    output = tmp_path / "no_runtime_wall.json"
    write_json_artifact(review_path, _review_packet_artifact())

    assert main(["--manifest-review-packet", str(review_path), "--output", str(output)]) == 0

    artifact = read_json_artifact(output)
    assert (
        artifact["artifact_type"]
        == "accurate_intake_websearch_exact_card_manifest_no_runtime_wall_v1"
    )
    assert artifact["status"] == "blocked_runtime_truth_by_design"


def test_manifest_no_runtime_wall_has_no_live_or_shared_contract_imports() -> None:
    source_paths = [
        Path("app/nutrition/application/websearch_exact_card_manifest_no_runtime_wall.py"),
        Path("scripts/build_accurate_intake_websearch_exact_card_manifest_no_runtime_wall.py"),
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
