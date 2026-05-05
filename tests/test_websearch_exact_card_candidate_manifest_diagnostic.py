from __future__ import annotations

from pathlib import Path

from app.nutrition.application.websearch_exact_card_candidate_manifest_diagnostic import (
    build_websearch_exact_card_candidate_manifest_diagnostic,
)
from app.nutrition.application.websearch_exact_card_runtime_promotion_policy import (
    build_websearch_exact_card_runtime_promotion_policy,
)


def _approval_wall() -> dict:
    return {
        "artifact_type": (
            "accurate_intake_websearch_exact_card_candidate_approval_wall_v1"
        ),
        "status": "blocked_pending_exact_card_approval_policy",
        "classification": "deterministic_exact_card_approval_wall_only",
        "blockers": ["exact_card_runtime_approval_policy_missing"],
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
        "approval_wall_records": [
            {
                "approval_wall_record_id": "wall_exact_card_approval_123",
                "approval_wall_role": "exact_card_runtime_truth_stop_gate",
                "approval_status": "blocked_pending_exact_card_approval_policy",
                "source_review_packet_id": "pkt_exact_card_review_refresh_123",
                "runtime_truth_allowed": False,
                "websearch_runtime_truth_allowed": False,
                "packet_ready_truth_allowed": False,
                "promotion_allowed": False,
                "approval_allowed_by_this_wall": False,
                "exact_card_created": False,
                "runtime_mutation_allowed": False,
                "raw_content_included": False,
                "raw_source_rows_included": False,
            }
        ],
        "summary": {
            "approval_wall_record_count": 1,
            "runtime_truth_allowed_count": 0,
            "exact_card_created_count": 0,
            "promotion_allowed_count": 0,
        },
        "next_required_slice": "define_exact_card_runtime_promotion_policy_or_stop",
    }


def _policy() -> dict:
    return build_websearch_exact_card_runtime_promotion_policy(
        exact_card_approval_wall=_approval_wall()
    )


def _request(**overrides: object) -> dict:
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
    }
    request.update(overrides)
    return request


def test_exact_card_candidate_manifest_diagnostic_emits_candidate_only_records() -> None:
    artifact = build_websearch_exact_card_candidate_manifest_diagnostic(
        runtime_promotion_policy=_policy(),
        promotion_requests=[_request()],
    )

    assert (
        artifact["artifact_type"]
        == "accurate_intake_websearch_exact_card_candidate_manifest_diagnostic_v1"
    )
    assert artifact["status"] == "pass_candidate_manifest_diagnostic"
    assert artifact["classification"] == "deterministic_exact_card_candidate_manifest_diagnostic_only"
    assert artifact["runtime_truth_changed"] is False
    assert artifact["mutation_changed"] is False
    assert artifact["runtime_mutation_allowed"] is False
    assert artifact["websearch_runtime_truth_allowed"] is False
    assert artifact["exact_card_created"] is False
    assert artifact["summary"]["manifest_candidate_count"] == 1
    assert artifact["summary"]["runtime_truth_allowed_count"] == 0
    assert artifact["next_required_slice"] == "websearch_exact_card_manifest_candidate_review_packet"


def test_exact_card_candidate_manifest_record_is_non_runtime() -> None:
    artifact = build_websearch_exact_card_candidate_manifest_diagnostic(
        runtime_promotion_policy=_policy(),
        promotion_requests=[_request()],
    )
    candidate = artifact["manifest_candidates"][0]

    assert candidate["candidate_role"] == "exact_card_manifest_candidate_only"
    assert candidate["truth_level"] == "manifest_candidate"
    assert candidate["source_class"] == "official_brand_chain_page"
    assert candidate["approval_id"] == "batch-policy-1"
    assert candidate["runtime_truth_allowed"] is False
    assert candidate["websearch_runtime_truth_allowed"] is False
    assert candidate["packet_ready_truth_allowed"] is False
    assert candidate["promotion_allowed"] is False
    assert candidate["exact_card_created"] is False
    assert candidate["runtime_mutation_allowed"] is False
    assert candidate["raw_content_included"] is False
    assert candidate["raw_source_rows_included"] is False
    assert candidate["required_before_runtime_truth"] == [
        "exact_card_record_creation_slice",
        "exact_card_runtime_gate",
        "packetizer_contract_review",
    ]


def test_exact_card_candidate_manifest_blocks_dirty_policy() -> None:
    policy = _policy()
    policy["live_websearch_used"] = 1
    artifact = build_websearch_exact_card_candidate_manifest_diagnostic(
        runtime_promotion_policy=policy,
        promotion_requests=[_request()],
    )

    assert artifact["status"] == "blocked"
    assert "policy_artifact_used_live_websearch" in artifact["blockers"]
    assert artifact["manifest_candidates"] == []


def test_exact_card_candidate_manifest_rejects_unsupported_request_without_candidate() -> None:
    artifact = build_websearch_exact_card_candidate_manifest_diagnostic(
        runtime_promotion_policy=_policy(),
        promotion_requests=[_request(source_class="open_food_facts")],
    )

    assert artifact["status"] == "blocked"
    assert "request_blocked:source_class_not_allowed_for_exact_card_runtime_policy" in artifact["blockers"]
    assert artifact["manifest_candidates"] == []
    assert artifact["rejected_requests"][0]["candidate_id"] == "official-drink-card"


def test_exact_card_candidate_manifest_blocks_dirty_request_payload() -> None:
    artifact = build_websearch_exact_card_candidate_manifest_diagnostic(
        runtime_promotion_policy=_policy(),
        promotion_requests=[
            _request(
                extra={
                    "nested": {
                        "runtime_truth_allowed": True,
                        "source_live_websearch_used": True,
                    }
                }
            )
        ],
    )

    assert artifact["status"] == "blocked"
    assert "request_blocked:request_nested_runtime_truth_allowed" in artifact["blockers"]
    assert "request_blocked:request_nested_source_live_websearch_used" in artifact["blockers"]
    assert artifact["manifest_candidates"] == []


def test_exact_card_candidate_manifest_blocks_candidate_truth_leaks() -> None:
    artifact = build_websearch_exact_card_candidate_manifest_diagnostic(
        runtime_promotion_policy=_policy(),
        promotion_requests=[_request(runtime_truth_allowed=True)],
    )

    assert artifact["status"] == "blocked"
    assert "request_blocked:request_allowed_runtime_truth" in artifact["blockers"]
    assert artifact["summary"]["runtime_truth_allowed_count"] == 0


def test_exact_card_candidate_manifest_requires_request_list() -> None:
    artifact = build_websearch_exact_card_candidate_manifest_diagnostic(
        runtime_promotion_policy=_policy(),
        promotion_requests=[],
    )

    assert artifact["status"] == "blocked"
    assert "manifest_promotion_request_missing" in artifact["blockers"]
    assert artifact["manifest_candidates"] == []


def test_exact_card_candidate_manifest_blocks_malformed_request_entries() -> None:
    artifact = build_websearch_exact_card_candidate_manifest_diagnostic(
        runtime_promotion_policy=_policy(),
        promotion_requests=[_request(), "bad-request"],
    )

    assert artifact["status"] == "blocked"
    assert "manifest_promotion_request_malformed" in artifact["blockers"]
    assert artifact["manifest_candidates"] == []


def test_exact_card_candidate_manifest_blocks_non_list_request_payload() -> None:
    artifact = build_websearch_exact_card_candidate_manifest_diagnostic(
        runtime_promotion_policy=_policy(),
        promotion_requests={"promotion_requests": [_request()]},  # type: ignore[arg-type]
    )

    assert artifact["status"] == "blocked"
    assert "manifest_promotion_requests_not_list" in artifact["blockers"]
    assert artifact["manifest_candidates"] == []


def test_exact_card_candidate_manifest_script_roundtrip(tmp_path: Path) -> None:
    from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact
    from scripts.build_accurate_intake_websearch_exact_card_candidate_manifest_diagnostic import (
        main,
    )

    policy_path = tmp_path / "policy.json"
    requests_path = tmp_path / "requests.json"
    output = tmp_path / "manifest.json"
    write_json_artifact(policy_path, _policy())
    write_json_artifact(requests_path, {"promotion_requests": [_request()]})

    assert main(
        [
            "--runtime-promotion-policy",
            str(policy_path),
            "--promotion-requests",
            str(requests_path),
            "--output",
            str(output),
        ]
    ) == 0

    artifact = read_json_artifact(output)
    assert (
        artifact["artifact_type"]
        == "accurate_intake_websearch_exact_card_candidate_manifest_diagnostic_v1"
    )
    assert artifact["status"] == "pass_candidate_manifest_diagnostic"


def test_exact_card_candidate_manifest_script_preserves_non_list_request_payload(
    tmp_path: Path,
) -> None:
    from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact
    from scripts.build_accurate_intake_websearch_exact_card_candidate_manifest_diagnostic import (
        main,
    )

    policy_path = tmp_path / "policy.json"
    requests_path = tmp_path / "requests.json"
    output = tmp_path / "manifest.json"
    write_json_artifact(policy_path, _policy())
    write_json_artifact(requests_path, {"promotion_requests": {"candidate_id": "bad"}})

    assert main(
        [
            "--runtime-promotion-policy",
            str(policy_path),
            "--promotion-requests",
            str(requests_path),
            "--output",
            str(output),
        ]
    ) == 0

    artifact = read_json_artifact(output)
    assert artifact["status"] == "blocked"
    assert "manifest_promotion_requests_not_list" in artifact["blockers"]


def test_exact_card_candidate_manifest_script_blocks_null_or_scalar_request_payload(
    tmp_path: Path,
) -> None:
    from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact
    from scripts.build_accurate_intake_websearch_exact_card_candidate_manifest_diagnostic import (
        main,
    )

    policy_path = tmp_path / "policy.json"
    write_json_artifact(policy_path, _policy())

    for payload in (None, "bad"):
        requests_path = tmp_path / f"requests_{payload or 'null'}.json"
        output = tmp_path / f"manifest_{payload or 'null'}.json"
        write_json_artifact(requests_path, {"promotion_requests": payload})

        assert main(
            [
                "--runtime-promotion-policy",
                str(policy_path),
                "--promotion-requests",
                str(requests_path),
                "--output",
                str(output),
            ]
        ) == 0

        artifact = read_json_artifact(output)
        assert artifact["status"] == "blocked"
        assert "manifest_promotion_requests_not_list" in artifact["blockers"]
        assert artifact["summary"]["promotion_request_count"] == 0


def test_exact_card_candidate_manifest_has_no_live_or_shared_contract_imports() -> None:
    source_paths = [
        Path("app/nutrition/application/websearch_exact_card_candidate_manifest_diagnostic.py"),
        Path("scripts/build_accurate_intake_websearch_exact_card_candidate_manifest_diagnostic.py"),
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
