from __future__ import annotations

from pathlib import Path

from app.nutrition.application.exact_card_candidate_promotion_readiness import (
    build_exact_card_candidate_promotion_readiness,
)
from app.nutrition.application.exact_evidence_lane_policy import (
    build_exact_evidence_lane_policy_artifact,
)
from app.nutrition.application.grokfast_websearch_packet_diagnostic import (
    GROKFAST_WEBSEARCH_PACKET_PROFILE,
    WEBSEARCH_PACKET_MANAGER_REQUIRED_FIELDS,
    build_fixture_manager_outputs,
    build_grokfast_websearch_packet_diagnostic,
    build_live_manager_payload,
    evaluate_manager_output_against_review_packet,
)
from app.nutrition.application.websearch_exact_candidate_review_packet import (
    build_websearch_exact_candidate_review_packet,
)
from app.nutrition.application.websearch_exact_candidate_chain_status import (
    build_websearch_exact_candidate_chain_status,
)
from app.nutrition.application.websearch_extract_result_candidate_smoke import (
    build_websearch_extract_result_candidate_smoke,
)
from app.nutrition.application.websearch_live_extract_preflight import (
    build_websearch_live_extract_preflight,
    is_websearch_live_extract_preflight_clear,
)
from app.nutrition.application.websearch_live_runner_readiness_packet import (
    build_websearch_live_runner_readiness_packet,
)
from app.nutrition.application.websearch_selected_extract_packet_smoke import (
    build_websearch_selected_extract_packet_smoke,
)
from app.providers.builderspace_runtime_contract import validate_manager_payload
from app.runtime.agent.manager_branch_contract import should_attempt_b1_pass2_structured_output_transport
from app.runtime.contracts.trace import MANAGER_LOOP_STAGE


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


def test_grokfast_websearch_packet_diagnostic_classifies_fixture_review_packet_use() -> None:
    review_packet = _review_packet()
    manager_outputs = build_fixture_manager_outputs(review_packet_artifact=review_packet)

    diagnostic = build_grokfast_websearch_packet_diagnostic(
        review_packet_artifact=review_packet,
        manager_outputs=manager_outputs,
        live_provider_used=False,
    )

    assert diagnostic["artifact_type"] == "accurate_intake_grokfast_websearch_packet_smoke"
    assert diagnostic["classification"] == "live_diagnostic_only"
    assert diagnostic["provider_profile"]["model"] == "grok-4-fast"
    assert diagnostic["live_provider_used"] is False
    assert diagnostic["readiness_claimed"] is False
    assert diagnostic["runtime_truth_changed"] is False
    assert diagnostic["runtime_mutation_attempted"] is False
    assert diagnostic["summary"]["case_count"] == 1
    assert diagnostic["summary"]["pass_count"] == 1
    assert diagnostic["summary"]["fail_count"] == 0
    assert diagnostic["provider_profile"]["provider_profile_id"] == (
        GROKFAST_WEBSEARCH_PACKET_PROFILE["provider_profile_id"]
    )


def test_grokfast_websearch_fixture_outputs_match_b1_pass2_manager_schema() -> None:
    review_packet = _review_packet()
    constraints = build_live_manager_payload(
        review_packet=review_packet["review_packets"][0]
    )["constraints"]
    manager_outputs = build_fixture_manager_outputs(review_packet_artifact=review_packet)

    assert should_attempt_b1_pass2_structured_output_transport(constraints) is True
    for output in manager_outputs:
        manager_output = output["manager_output"]
        for field in WEBSEARCH_PACKET_MANAGER_REQUIRED_FIELDS:
            assert field in manager_output
        validate_manager_payload(
            MANAGER_LOOP_STAGE,
            manager_output,
            constraints=constraints,
        )


def test_grokfast_websearch_live_payload_selects_structured_pass2_contract() -> None:
    packet = _review_packet()["review_packets"][0]
    payload = build_live_manager_payload(review_packet=packet)

    assert payload["constraints"]["phase_b1_manager_role"] == "pass_2_synthesis"
    assert payload["constraints"]["phase_b1_pass1_mode"] == "natural_tool_selection_probe"
    assert payload["constraints"]["phase_b1_case_family"] == "common_commercial_drink"
    assert should_attempt_b1_pass2_structured_output_transport(payload["constraints"]) is True
    assert payload["expected_output_contract"]["required_top_level_fields"] == list(
        WEBSEARCH_PACKET_MANAGER_REQUIRED_FIELDS
    )
    assert payload["expected_output_contract"]["target_attachment"] == {}
    assert payload["expected_output_contract"]["forbidden_top_level_fields"] == ["item_results"]
    assert packet["packet_id"] in payload["allowed_evidence_refs"]
    assert packet["source_url"] in payload["allowed_evidence_refs"]


def test_grokfast_websearch_packet_diagnostic_flags_missing_manager_contract_fields() -> None:
    packet = _review_packet()["review_packets"][0]
    manager_output = build_fixture_manager_outputs(
        review_packet_artifact={"review_packets": [packet]}
    )[0]["manager_output"]
    manager_output.pop("intent")

    result = evaluate_manager_output_against_review_packet(
        review_packet=packet,
        manager_output=manager_output,
    )

    assert result["status"] == "fail"
    assert result["missing_manager_contract_fields"] == ["intent"]
    assert "manager_contract_required_fields_missing" in result["failure_families"]


def test_grokfast_websearch_packet_diagnostic_flags_schema_invalid_field_shape() -> None:
    packet = _review_packet()["review_packets"][0]
    manager_output = build_fixture_manager_outputs(
        review_packet_artifact={"review_packets": [packet]}
    )[0]["manager_output"]
    manager_output["target_attachment"] = "not-a-dict"

    result = evaluate_manager_output_against_review_packet(
        review_packet=packet,
        manager_output=manager_output,
    )

    assert result["status"] == "fail"
    assert "manager_contract_schema_validation_failed" in result["failure_families"]
    assert "target_attachment:expected_dict" in result["manager_contract_validation_errors"]


def test_grokfast_websearch_packet_diagnostic_applies_injected_contract_validator() -> None:
    packet = _review_packet()["review_packets"][0]
    diagnostic = build_grokfast_websearch_packet_diagnostic(
        review_packet_artifact={"review_packets": [packet]},
        manager_outputs=build_fixture_manager_outputs(review_packet_artifact={"review_packets": [packet]}),
        live_provider_used=False,
        manager_contract_validator=lambda _packet, _output: ["external-schema-error"],
    )

    assert diagnostic["status"] == "diagnostic_fail"
    assert diagnostic["summary"]["failure_families"] == ["manager_contract_schema_validation_failed"]
    assert diagnostic["cases"][0]["manager_contract_validation_errors"] == ["external-schema-error"]


def test_grokfast_websearch_packet_diagnostic_flags_review_candidate_target_attachment() -> None:
    packet = _review_packet()["review_packets"][0]
    manager_output = build_fixture_manager_outputs(
        review_packet_artifact={"review_packets": [packet]}
    )[0]["manager_output"]
    manager_output["target_attachment"] = {
        "packet_id": packet["packet_id"],
        "review_kcal_candidate": 400,
    }

    result = evaluate_manager_output_against_review_packet(
        review_packet=packet,
        manager_output=manager_output,
    )

    assert result["status"] == "fail"
    assert "review_candidate_attached_as_mutation_target" in result["failure_families"]


def test_grokfast_websearch_packet_diagnostic_flags_truth_promotion_attempt() -> None:
    packet = _review_packet()["review_packets"][0]
    manager_output = {
        "manager_action": "final",
        "final_action": "commit",
        "tool_calls": [],
        "item_results": [{"food_name": "Milksha", "kcal": 400}],
        "evidence_used": [packet["packet_id"]],
        "runtime_truth_allowed": True,
        "exact_card_created": True,
        "semantic_decision": {"mutation_intent_candidate": "canonical_write"},
    }

    result = evaluate_manager_output_against_review_packet(
        review_packet=packet,
        manager_output=manager_output,
    )

    assert result["status"] == "fail"
    assert "review_candidate_used_for_commit" in result["failure_families"]
    assert "review_candidate_used_as_item_result" in result["failure_families"]
    assert "review_candidate_promoted_to_truth" in result["failure_families"]
    assert "review_candidate_mutation_intent" in result["failure_families"]


def test_grokfast_websearch_packet_diagnostic_flags_textual_truth_overclaim() -> None:
    packet = _review_packet()["review_packets"][0]
    result = evaluate_manager_output_against_review_packet(
        review_packet=packet,
        manager_output={
            "manager_action": "final",
            "final_action": "answer_only",
            "tool_calls": [],
            "item_results": [],
            "evidence_used": [packet["packet_id"]],
            "answer_contract": {
                "text": "This is approved for runtime use and ready to create the exact card."
            },
            "semantic_decision": {"mutation_intent_candidate": "no_mutation"},
        },
    )

    assert result["status"] == "fail"
    assert "review_candidate_promoted_to_truth" in result["failure_families"]


def test_grokfast_websearch_packet_diagnostic_flags_invented_evidence() -> None:
    packet = _review_packet()["review_packets"][0]
    result = evaluate_manager_output_against_review_packet(
        review_packet=packet,
        manager_output={
            "manager_action": "final",
            "final_action": "answer_only",
            "tool_calls": [],
            "item_results": [],
            "evidence_used": ["invented-web-source"],
            "semantic_decision": {"mutation_intent_candidate": "no_mutation"},
        },
    )

    assert result["status"] == "fail"
    assert "invented_evidence_reference" in result["failure_families"]


def test_grokfast_websearch_packet_diagnostic_rejects_substring_evidence_ref() -> None:
    packet = _review_packet()["review_packets"][0]
    result = evaluate_manager_output_against_review_packet(
        review_packet=packet,
        manager_output={
            "manager_action": "final",
            "final_action": "answer_only",
            "tool_calls": [],
            "item_results": [],
            "evidence_used": [f"fabricated wrapper around {packet['packet_id']}"],
            "semantic_decision": {"mutation_intent_candidate": "no_mutation"},
        },
    )

    assert result["status"] == "fail"
    assert "invented_evidence_reference" in result["failure_families"]


def test_grokfast_websearch_packet_diagnostic_blocks_empty_review_packet_artifact() -> None:
    diagnostic = build_grokfast_websearch_packet_diagnostic(
        review_packet_artifact={
            "artifact_type": "accurate_intake_websearch_exact_candidate_review_packet_v1",
            "review_packets": [],
        },
        manager_outputs=[],
        live_provider_used=False,
    )

    assert diagnostic["status"] == "blocked"
    assert diagnostic["failure_family"] == "missing_review_packets"
    assert diagnostic["summary"]["fail_count"] == 1
    assert diagnostic["summary"]["failure_families"] == ["missing_review_packets"]


def test_grokfast_websearch_live_payload_hides_runtime_authority() -> None:
    packet = _review_packet()["review_packets"][0]
    payload = build_live_manager_payload(review_packet=packet)

    assert payload["diagnostic_scope"] == "websearch_review_packet_manager_seam_smoke"
    assert payload["constraints"]["runtime_truth_allowed"] is False
    assert payload["constraints"]["runtime_mutation_allowed"] is False
    assert "local_json" not in str(payload)
    assert "FoodDB truth" not in str(payload)


def test_websearch_live_extract_preflight_integrity_helper_blocks_overclaim() -> None:
    preflight = build_websearch_live_extract_preflight(
        exact_review_packet_artifact=_review_packet()
    )
    assert is_websearch_live_extract_preflight_clear(preflight) is True

    preflight["ready_for_runtime_truth"] = True
    assert is_websearch_live_extract_preflight_clear(preflight) is False


def test_grokfast_websearch_live_runner_preflight_ref_records_authorized_case_matrix() -> None:
    from scripts.run_accurate_intake_grokfast_websearch_packet_smoke import _preflight_ref

    preflight = build_websearch_live_extract_preflight(
        exact_review_packet_artifact=_review_packet()
    )

    ref = _preflight_ref(preflight)

    assert ref["preflight_ref_source"] == "run_accurate_intake_grokfast_websearch_packet_smoke"
    assert ref["review_packet_authorized"] is True
    assert ref["review_packet_count"] == 1
    assert ref["case_matrix_case_count"] == 6
    assert ref["case_matrix_negative_case_count"] == 4
    assert ref["case_matrix_modifier_guard_cases"] == 1
    assert ref["case_matrix_live_provider_invoked"] is False
    assert ref["case_matrix_websearch_invoked"] is False
    assert ref["preflight_artifact_digest_algorithm"] == "sha256"
    assert ref["preflight_artifact_digest_scope"] == (
        "semantic_preflight_without_generated_at_utc"
    )
    assert isinstance(ref["preflight_artifact_digest"], str)
    assert len(ref["preflight_artifact_digest"]) == 64


def test_grokfast_websearch_packet_smoke_cli_defaults_to_fixture_and_blocks_live(
    tmp_path: Path,
) -> None:
    from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact
    from scripts.run_accurate_intake_grokfast_websearch_packet_smoke import main

    review_packet_path = tmp_path / "review_packet.json"
    output = tmp_path / "diagnostic.json"
    write_json_artifact(review_packet_path, _review_packet())

    assert (
        main(
            [
                "--mode",
                "fixture",
                "--review-packet-artifact",
                str(review_packet_path),
                "--output",
                str(output),
            ]
        )
        == 0
    )
    artifact = read_json_artifact(output)
    assert artifact["live_provider_used"] is False
    assert artifact["summary"]["pass_count"] == 1

    blocked_output = tmp_path / "blocked_live.json"
    assert (
        main(
            [
                "--mode",
                "live",
                "--review-packet-artifact",
                str(review_packet_path),
                "--output",
                str(blocked_output),
            ]
        )
        == 2
    )
    blocked = read_json_artifact(blocked_output)
    assert blocked["status"] == "blocked"
    assert blocked["failure_family"] == "live_mode_requires_explicit_allow_live"


def test_grokfast_websearch_packet_smoke_live_blocks_preflight_review_packet_mismatch(
    tmp_path: Path,
) -> None:
    from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact
    from scripts.run_accurate_intake_grokfast_websearch_packet_smoke import main

    review_packet = _review_packet()
    preflight = build_websearch_live_extract_preflight(
        exact_review_packet_artifact=review_packet
    )
    mismatched_review_packet = _review_packet()
    mismatched_review_packet["review_packets"][0]["packet_id"] = "different-review-packet"

    review_packet_path = tmp_path / "review_packet.json"
    preflight_path = tmp_path / "preflight.json"
    output = tmp_path / "blocked_mismatch.json"
    write_json_artifact(review_packet_path, mismatched_review_packet)
    write_json_artifact(preflight_path, preflight)

    assert (
        main(
            [
                "--mode",
                "live",
                "--allow-live",
                "--review-packet-artifact",
                str(review_packet_path),
                "--preflight-artifact",
                str(preflight_path),
                "--output",
                str(output),
            ]
        )
        == 2
    )
    blocked = read_json_artifact(output)
    assert blocked["status"] == "blocked"
    assert blocked["failure_family"] == "websearch_live_preflight_review_packet_mismatch"
    assert blocked["live_provider_used"] is False


def test_grokfast_websearch_packet_smoke_live_requires_exact_candidate_chain_status(
    tmp_path: Path,
) -> None:
    from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact
    from scripts.run_accurate_intake_grokfast_websearch_packet_smoke import main

    review_packet = _review_packet()
    preflight = build_websearch_live_extract_preflight(
        exact_review_packet_artifact=review_packet
    )
    review_packet_path = tmp_path / "review_packet.json"
    preflight_path = tmp_path / "preflight.json"
    output = tmp_path / "blocked_missing_chain.json"
    write_json_artifact(review_packet_path, review_packet)
    write_json_artifact(preflight_path, preflight)

    assert (
        main(
            [
                "--mode",
                "live",
                "--allow-live",
                "--review-packet-artifact",
                str(review_packet_path),
                "--preflight-artifact",
                str(preflight_path),
                "--exact-candidate-chain-status-artifact",
                str(tmp_path / "missing_chain.json"),
                "--output",
                str(output),
            ]
        )
        == 2
    )
    blocked = read_json_artifact(output)
    assert blocked["status"] == "blocked"
    assert blocked["failure_family"] == "missing_clear_websearch_exact_candidate_chain_status"
    assert blocked["live_provider_used"] is False


def test_grokfast_websearch_packet_smoke_live_blocks_chain_review_packet_mismatch(
    tmp_path: Path,
) -> None:
    from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact
    from scripts.run_accurate_intake_grokfast_websearch_packet_smoke import main

    review_packet = _review_packet()
    preflight = build_websearch_live_extract_preflight(
        exact_review_packet_artifact=review_packet
    )
    chain = build_websearch_exact_candidate_chain_status(
        exact_review_packet_artifact=review_packet,
        preflight_artifact=preflight,
    )
    chain["chain_proof"]["review_packet_ids"] = ["different-review-packet"]

    review_packet_path = tmp_path / "review_packet.json"
    preflight_path = tmp_path / "preflight.json"
    chain_path = tmp_path / "chain.json"
    output = tmp_path / "blocked_chain_mismatch.json"
    write_json_artifact(review_packet_path, review_packet)
    write_json_artifact(preflight_path, preflight)
    write_json_artifact(chain_path, chain)

    assert (
        main(
            [
                "--mode",
                "live",
                "--allow-live",
                "--review-packet-artifact",
                str(review_packet_path),
                "--preflight-artifact",
                str(preflight_path),
                "--exact-candidate-chain-status-artifact",
                str(chain_path),
                "--output",
                str(output),
            ]
        )
        == 2
    )
    blocked = read_json_artifact(output)
    assert blocked["status"] == "blocked"
    assert blocked["failure_family"] == "websearch_exact_candidate_chain_review_packet_mismatch"
    assert blocked["live_provider_used"] is False


def test_grokfast_websearch_packet_smoke_live_requires_runner_readiness_packet(
    tmp_path: Path,
) -> None:
    from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact
    from scripts.run_accurate_intake_grokfast_websearch_packet_smoke import main

    review_packet = _review_packet()
    preflight = build_websearch_live_extract_preflight(
        exact_review_packet_artifact=review_packet
    )
    chain = build_websearch_exact_candidate_chain_status(
        exact_review_packet_artifact=review_packet,
        preflight_artifact=preflight,
    )

    review_packet_path = tmp_path / "review_packet.json"
    preflight_path = tmp_path / "preflight.json"
    chain_path = tmp_path / "chain.json"
    output = tmp_path / "blocked_missing_readiness.json"
    write_json_artifact(review_packet_path, review_packet)
    write_json_artifact(preflight_path, preflight)
    write_json_artifact(chain_path, chain)

    assert (
        main(
            [
                "--mode",
                "live",
                "--allow-live",
                "--review-packet-artifact",
                str(review_packet_path),
                "--preflight-artifact",
                str(preflight_path),
                "--exact-candidate-chain-status-artifact",
                str(chain_path),
                "--live-runner-readiness-artifact",
                str(tmp_path / "missing_readiness.json"),
                "--output",
                str(output),
            ]
        )
        == 2
    )
    blocked = read_json_artifact(output)
    assert blocked["status"] == "blocked"
    assert blocked["failure_family"] == "missing_clear_websearch_live_runner_readiness_packet"
    assert blocked["live_provider_used"] is False
    assert blocked["live_websearch_used"] is False


def test_grokfast_websearch_packet_smoke_live_blocks_runner_readiness_packet_mismatch(
    tmp_path: Path,
) -> None:
    from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact
    from scripts.run_accurate_intake_grokfast_websearch_packet_smoke import main

    review_packet = _review_packet()
    preflight = build_websearch_live_extract_preflight(
        exact_review_packet_artifact=review_packet
    )
    chain = build_websearch_exact_candidate_chain_status(
        exact_review_packet_artifact=review_packet,
        preflight_artifact=preflight,
    )
    readiness = build_websearch_live_runner_readiness_packet(
        review_packet_artifact=review_packet,
        preflight_artifact=preflight,
        exact_candidate_chain_status_artifact=chain,
    )
    readiness["source_refs"]["review_packet_digest"] = "different-review-digest"

    review_packet_path = tmp_path / "review_packet.json"
    preflight_path = tmp_path / "preflight.json"
    chain_path = tmp_path / "chain.json"
    readiness_path = tmp_path / "readiness.json"
    output = tmp_path / "blocked_readiness_mismatch.json"
    write_json_artifact(review_packet_path, review_packet)
    write_json_artifact(preflight_path, preflight)
    write_json_artifact(chain_path, chain)
    write_json_artifact(readiness_path, readiness)

    assert (
        main(
            [
                "--mode",
                "live",
                "--allow-live",
                "--review-packet-artifact",
                str(review_packet_path),
                "--preflight-artifact",
                str(preflight_path),
                "--exact-candidate-chain-status-artifact",
                str(chain_path),
                "--live-runner-readiness-artifact",
                str(readiness_path),
                "--output",
                str(output),
            ]
        )
        == 2
    )
    blocked = read_json_artifact(output)
    assert blocked["status"] == "blocked"
    assert blocked["failure_family"] == "websearch_live_runner_readiness_packet_mismatch"
    assert blocked["live_provider_used"] is False


def test_grokfast_websearch_packet_smoke_live_blocks_same_ref_packet_drift(
    tmp_path: Path,
) -> None:
    from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact
    from scripts.run_accurate_intake_grokfast_websearch_packet_smoke import main

    review_packet = _review_packet()
    preflight = build_websearch_live_extract_preflight(
        exact_review_packet_artifact=review_packet
    )
    drifted_review_packet = _review_packet()
    drifted_review_packet["review_packets"][0]["runtime_truth_allowed"] = True

    review_packet_path = tmp_path / "review_packet.json"
    preflight_path = tmp_path / "preflight.json"
    output = tmp_path / "blocked_drift.json"
    write_json_artifact(review_packet_path, drifted_review_packet)
    write_json_artifact(preflight_path, preflight)

    assert (
        main(
            [
                "--mode",
                "live",
                "--allow-live",
                "--review-packet-artifact",
                str(review_packet_path),
                "--preflight-artifact",
                str(preflight_path),
                "--output",
                str(output),
            ]
        )
        == 2
    )
    blocked = read_json_artifact(output)
    assert blocked["status"] == "blocked"
    assert blocked["failure_family"] == "websearch_live_preflight_review_packet_mismatch"
    assert blocked["live_provider_used"] is False
