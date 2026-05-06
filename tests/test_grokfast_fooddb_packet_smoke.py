from __future__ import annotations

import json
from pathlib import Path

from app.nutrition.application.fooddb_manager_packet_smoke import (
    build_fooddb_manager_packet_smoke,
)
from app.nutrition.application.fooddb_retrieval_policy import (
    build_runtime_retrieval_records_from_small_anchor_payload,
)
from app.nutrition.application.grokfast_fooddb_packet_smoke import (
    FOODDB_PACKET_MANAGER_REQUIRED_FIELDS,
    build_fixture_manager_outputs,
    build_grokfast_fooddb_packet_diagnostic,
    build_live_manager_payload,
    build_packet_artifact_from_tool_evidence_result,
    evaluate_manager_output_against_packet,
)
from app.nutrition.application.tool_evidence_result import build_tool_evidence_result
from app.providers.builderspace_runtime_contract import validate_manager_payload
from app.runtime.agent.manager_branch_contract import should_attempt_b1_pass2_structured_output_transport
from app.runtime.contracts.trace import MANAGER_LOOP_STAGE


def _packet_artifact() -> dict:
    payload = json.loads(Path("app/knowledge/small_anchor_store_tw.json").read_text(encoding="utf-8-sig"))
    records = build_runtime_retrieval_records_from_small_anchor_payload(payload)
    return build_fooddb_manager_packet_smoke(retrieval_records=records)


def _tool_evidence_artifact() -> dict:
    packet_artifact = _packet_artifact()
    tool_result = build_tool_evidence_result(
        tool_name="lookup_food_evidence",
        tool_call_id="tool-fooddb-manager-packet-smoke",
        evidence_packets=tuple(case["manager_evidence_packet"] for case in packet_artifact["cases"]),
        index_adapter={
            "adapter_kind": "local_small_anchor_index",
            "storage_backend": "local_json",
        },
    )
    return {
        "artifact_type": "accurate_intake_tool_evidence_result_smoke",
        "adapter_diagnostics": {
            "adapter_kind": "local_small_anchor_index",
            "storage_backend": "local_json",
            "manager_visible": False,
        },
        "tool_evidence_result": tool_result,
    }


def test_grokfast_fooddb_packet_diagnostic_classifies_fixture_evidence_use() -> None:
    packet_artifact = _packet_artifact()
    manager_outputs = build_fixture_manager_outputs(packet_artifact=packet_artifact)

    diagnostic = build_grokfast_fooddb_packet_diagnostic(
        packet_artifact=packet_artifact,
        manager_outputs=manager_outputs,
        live_provider_used=False,
    )

    assert diagnostic["artifact_type"] == "accurate_intake_grokfast_fooddb_packet_smoke"
    assert diagnostic["classification"] == "live_diagnostic_only"
    assert diagnostic["live_provider_used"] is False
    assert diagnostic["readiness_claimed"] is False
    assert diagnostic["self_use_approved"] is False
    assert diagnostic["production_selected"] is False
    assert diagnostic["summary"]["case_count"] == 5
    assert diagnostic["summary"]["pass_count"] == 5
    assert diagnostic["summary"]["fail_count"] == 0
    assert diagnostic["provider_profile"]["model"] == "grok-4-fast"


def test_grokfast_fooddb_fixture_outputs_match_b1_pass2_manager_schema() -> None:
    packet_artifact = _packet_artifact()
    manager_outputs = build_fixture_manager_outputs(packet_artifact=packet_artifact)

    for packet_case, output in zip(packet_artifact["cases"], manager_outputs, strict=True):
        constraints = build_live_manager_payload(packet_case=packet_case)["constraints"]
        assert should_attempt_b1_pass2_structured_output_transport(constraints) is True
        manager_output = output["manager_output"]
        for field in FOODDB_PACKET_MANAGER_REQUIRED_FIELDS:
            assert field in manager_output
        validate_manager_payload(
            MANAGER_LOOP_STAGE,
            manager_output,
            constraints=constraints,
        )


def test_grokfast_fooddb_live_payload_selects_structured_pass2_contract() -> None:
    packet_case = _packet_artifact()["cases"][0]
    payload = build_live_manager_payload(packet_case=packet_case)

    assert payload["constraints"]["phase_b1_manager_role"] == "pass_2_synthesis"
    assert payload["constraints"]["phase_b1_pass1_mode"] == "natural_tool_selection_probe"
    assert should_attempt_b1_pass2_structured_output_transport(payload["constraints"]) is True
    assert payload["expected_output_contract"]["required_top_level_fields"] == list(
        FOODDB_PACKET_MANAGER_REQUIRED_FIELDS
    )
    assert payload["expected_output_contract"]["runtime_mutation_allowed"] is False
    assert payload["expected_output_contract"]["runtime_truth_changed"] is False
    assert packet_case["case_id"] in payload["allowed_evidence_refs"]


def test_grokfast_fooddb_live_payload_requires_packet_authority_for_modifier_adjustment() -> None:
    packet_case = next(
        case for case in _packet_artifact()["cases"] if case["case_id"] == "chicken_bento_less_rice"
    )
    payload = build_live_manager_payload(packet_case=packet_case)

    assert (
        payload["expected_output_contract"]["packet_authorized_modifier_adjustment_only"] is True
    )
    assert any(
        "Do not adjust kcal_point or kcal_range from modifier_compatibility alone" in instruction
        for instruction in payload["instructions"]
    )


def test_grokfast_fooddb_packet_diagnostic_flags_invented_evidence() -> None:
    packet_case = _packet_artifact()["cases"][0]
    manager_output = {
        "manager_action": "final",
        "final_action": "commit",
        "tool_calls": [],
        "item_results": [
            {
                "food_name": "invented",
                "kcal_range": [1, 2],
                "likely_kcal": 1,
                "uncertainty": "low",
                "evidence_used": ["not_in_packet"],
            }
        ],
        "evidence_used": ["not_in_packet"],
    }

    result = evaluate_manager_output_against_packet(
        packet_case=packet_case,
        manager_output=manager_output,
    )

    assert result["status"] == "fail"
    assert "invented_evidence_reference" in result["failure_families"]


def test_grokfast_fooddb_packet_diagnostic_rejects_pass2_tool_calls_after_packet() -> None:
    packet_case = _packet_artifact()["cases"][0]
    manager_output = build_fixture_manager_outputs(packet_artifact={"cases": [packet_case]})[0][
        "manager_output"
    ]
    manager_output["tool_calls"] = [{"tool_name": "lookup_food_evidence", "arguments": {}}]

    result = evaluate_manager_output_against_packet(
        packet_case=packet_case,
        manager_output=manager_output,
    )

    assert result["status"] == "fail"
    assert "packet_pass2_reopened_tool_calls" in result["failure_families"]


def test_grokfast_fooddb_packet_diagnostic_rejects_textual_invented_source_ref() -> None:
    packet_case = _packet_artifact()["cases"][0]
    manager_output = build_fixture_manager_outputs(packet_artifact={"cases": [packet_case]})[0][
        "manager_output"
    ]
    manager_output["answer_contract"] = {
        "text": "Grounded in provided packet plus alias_expansion_exact and kcal_range_adjusted_for_less_rice."
    }

    result = evaluate_manager_output_against_packet(
        packet_case=packet_case,
        manager_output=manager_output,
    )

    assert result["status"] == "fail"
    assert "invented_text_evidence_reference" in result["failure_families"]
    assert result["invented_text_evidence_refs"] == [
        "alias_expansion_exact",
        "kcal_range_adjusted_for_less_rice",
    ]


def test_grokfast_fooddb_packet_diagnostic_rejects_nested_textual_source_ref() -> None:
    packet_case = _packet_artifact()["cases"][0]
    manager_output = build_fixture_manager_outputs(packet_artifact={"cases": [packet_case]})[0][
        "manager_output"
    ]
    manager_output["semantic_decision"]["followup_question"] = (
        "Please confirm based on alias_expansion_exact."
    )
    manager_output["target_attachment"] = {
        "label": "candidate from kcal_range_adjusted_for_less_rice"
    }

    result = evaluate_manager_output_against_packet(
        packet_case=packet_case,
        manager_output=manager_output,
    )

    assert result["status"] == "fail"
    assert "invented_text_evidence_reference" in result["failure_families"]
    assert result["invented_text_evidence_refs"] == [
        "alias_expansion_exact",
        "kcal_range_adjusted_for_less_rice",
    ]


def test_grokfast_fooddb_packet_diagnostic_allows_plain_text_kcal_summary() -> None:
    packet_case = _packet_artifact()["cases"][0]
    manager_output = build_fixture_manager_outputs(packet_artifact={"cases": [packet_case]})[0][
        "manager_output"
    ]
    manager_output["answer_contract"] = {
        "text": "大杯半糖珍奶約450kcal（範圍350-550kcal），基於提供的 FoodDB packet。"
    }

    result = evaluate_manager_output_against_packet(
        packet_case=packet_case,
        manager_output=manager_output,
    )

    assert result["status"] == "pass"
    assert result["invented_text_evidence_refs"] == []


def test_grokfast_fooddb_packet_diagnostic_flags_missing_manager_contract_fields() -> None:
    packet_case = _packet_artifact()["cases"][0]
    manager_output = build_fixture_manager_outputs(packet_artifact={"cases": [packet_case]})[0][
        "manager_output"
    ]
    manager_output.pop("intent")

    result = evaluate_manager_output_against_packet(
        packet_case=packet_case,
        manager_output=manager_output,
    )

    assert result["status"] == "fail"
    assert result["missing_manager_contract_fields"] == ["intent"]
    assert "manager_contract_required_fields_missing" in result["failure_families"]


def test_grokfast_fooddb_packet_diagnostic_flags_schema_invalid_field_shape() -> None:
    packet_case = _packet_artifact()["cases"][0]
    manager_output = build_fixture_manager_outputs(packet_artifact={"cases": [packet_case]})[0][
        "manager_output"
    ]
    manager_output["target_attachment"] = "not-a-dict"

    result = evaluate_manager_output_against_packet(
        packet_case=packet_case,
        manager_output=manager_output,
    )

    assert result["status"] == "fail"
    assert "manager_contract_schema_validation_failed" in result["failure_families"]
    assert "target_attachment:expected_dict" in result["manager_contract_validation_errors"]


def test_grokfast_fooddb_packet_diagnostic_applies_injected_contract_validator() -> None:
    packet_case = _packet_artifact()["cases"][0]
    diagnostic = build_grokfast_fooddb_packet_diagnostic(
        packet_artifact={"cases": [packet_case]},
        manager_outputs=build_fixture_manager_outputs(packet_artifact={"cases": [packet_case]}),
        live_provider_used=False,
        manager_contract_validator=lambda _case, _output: ["external-schema-error"],
    )

    assert diagnostic["status"] == "diagnostic_fail"
    assert diagnostic["summary"]["failure_families"] == ["manager_contract_schema_validation_failed"]
    assert diagnostic["cases"][0]["manager_contract_validation_errors"] == ["external-schema-error"]


def test_grokfast_fooddb_packet_diagnostic_rejects_substring_evidence_ref() -> None:
    packet_case = _packet_artifact()["cases"][0]
    anchor_id = packet_case["manager_evidence_packet"]["evidence_items"][0]["anchor_id"]
    manager_output = build_fixture_manager_outputs(packet_artifact={"cases": [packet_case]})[0][
        "manager_output"
    ]
    manager_output["evidence_used"] = [f"fabricated wrapper around {anchor_id}"]
    manager_output["item_results"][0]["evidence_used"] = [f"fabricated wrapper around {anchor_id}"]

    result = evaluate_manager_output_against_packet(
        packet_case=packet_case,
        manager_output=manager_output,
    )

    assert result["status"] == "fail"
    assert "invented_evidence_reference" in result["failure_families"]


def test_grokfast_fooddb_packet_diagnostic_blocks_unsupported_modifier_kcal_adjustment() -> None:
    packet_case = next(
        case for case in _packet_artifact()["cases"] if case["case_id"] == "chicken_bento_less_rice"
    )
    manager_output = build_fixture_manager_outputs(packet_artifact={"cases": [packet_case]})[0][
        "manager_output"
    ]
    manager_output["item_results"][0]["kcal_range"] = [600, 750]

    result = evaluate_manager_output_against_packet(
        packet_case=packet_case,
        manager_output=manager_output,
    )

    assert result["status"] == "fail"
    assert "unsupported_modifier_adjusted_kcal_range" not in result["failure_families"]
    assert "modifier_adjusted_kcal_without_packet_adjustment" in result["failure_families"]


def test_grokfast_fooddb_packet_diagnostic_blocks_compatible_modifier_kcal_adjustment() -> None:
    packet_case = next(
        case for case in _packet_artifact()["cases"] if case["case_id"] == "boba_large_half_sugar"
    )
    manager_output = build_fixture_manager_outputs(packet_artifact={"cases": [packet_case]})[0][
        "manager_output"
    ]
    manager_output["item_results"][0]["kcal_range"] = [400, 520]
    manager_output["item_results"][0]["likely_kcal"] = 460

    result = evaluate_manager_output_against_packet(
        packet_case=packet_case,
        manager_output=manager_output,
    )

    assert result["status"] == "fail"
    assert "modifier_adjusted_kcal_without_packet_adjustment" in result["failure_families"]
    assert "unsupported_modifier_adjusted_kcal_range" not in result["failure_families"]


def test_grokfast_fooddb_packet_diagnostic_blocks_adjustment_with_non_anchor_ref() -> None:
    packet_case = next(
        case for case in _packet_artifact()["cases"] if case["case_id"] == "boba_large_half_sugar"
    )
    manager_output = build_fixture_manager_outputs(packet_artifact={"cases": [packet_case]})[0][
        "manager_output"
    ]
    canonical_name = packet_case["manager_evidence_packet"]["evidence_items"][0]["canonical_name"]
    manager_output["item_results"][0]["evidence_used"] = [canonical_name]
    manager_output["item_results"][0]["kcal_range"] = [400, 520]
    manager_output["item_results"][0]["likely_kcal"] = 460

    result = evaluate_manager_output_against_packet(
        packet_case=packet_case,
        manager_output=manager_output,
    )

    assert result["status"] == "fail"
    assert "modifier_adjusted_kcal_without_packet_adjustment" in result["failure_families"]


def test_grokfast_fooddb_packet_diagnostic_normalizes_refs_before_modifier_guard() -> None:
    packet_case = next(
        case for case in _packet_artifact()["cases"] if case["case_id"] == "boba_large_half_sugar"
    )
    manager_output = build_fixture_manager_outputs(packet_artifact={"cases": [packet_case]})[0][
        "manager_output"
    ]
    anchor_id = packet_case["manager_evidence_packet"]["evidence_items"][0]["anchor_id"]
    manager_output["item_results"][0]["evidence_used"] = [anchor_id.upper()]
    manager_output["item_results"][0]["kcal_range"] = [400, 520]
    manager_output["item_results"][0]["likely_kcal"] = 460

    result = evaluate_manager_output_against_packet(
        packet_case=packet_case,
        manager_output=manager_output,
    )

    assert result["status"] == "fail"
    assert "modifier_adjusted_kcal_without_packet_adjustment" in result["failure_families"]
    assert "invented_evidence_reference" not in result["failure_families"]


def test_grokfast_fooddb_packet_diagnostic_does_not_false_flag_shared_source_ref() -> None:
    packet_case = next(
        case for case in _packet_artifact()["cases"] if case["case_id"] == "listed_luwei_components"
    )
    evidence_items = packet_case["manager_evidence_packet"]["evidence_items"]
    shared_source_id = evidence_items[0]["source_provenance"]["source_id"]
    packet_case = {
        **packet_case,
        "manager_evidence_packet": {
            **packet_case["manager_evidence_packet"],
            "evidence_items": [
                {
                    **item,
                    "modifier_compatibility": {"seasoning": "compatible"},
                    "source_provenance": {
                        **item["source_provenance"],
                        "source_id": shared_source_id,
                    },
                }
                for item in evidence_items[:2]
            ],
        },
    }
    manager_output = build_fixture_manager_outputs(packet_artifact={"cases": [packet_case]})[0][
        "manager_output"
    ]
    for index, item in enumerate(packet_case["manager_evidence_packet"]["evidence_items"]):
        manager_output["item_results"][index]["evidence_used"] = [shared_source_id]
        manager_output["item_results"][index]["kcal_range"] = item["kcal_range"]
        manager_output["item_results"][index]["likely_kcal"] = item["kcal_point"]

    result = evaluate_manager_output_against_packet(
        packet_case=packet_case,
        manager_output=manager_output,
    )

    assert result["status"] == "pass"
    assert "modifier_adjusted_kcal_without_packet_adjustment" not in result["failure_families"]


def test_grokfast_fooddb_packet_diagnostic_uses_unique_food_name_when_source_ref_shared() -> None:
    packet_case = next(
        case for case in _packet_artifact()["cases"] if case["case_id"] == "listed_luwei_components"
    )
    evidence_items = packet_case["manager_evidence_packet"]["evidence_items"]
    shared_source_id = evidence_items[0]["source_provenance"]["source_id"]
    packet_case = {
        **packet_case,
        "manager_evidence_packet": {
            **packet_case["manager_evidence_packet"],
            "evidence_items": [
                {
                    **item,
                    "modifier_compatibility": {"seasoning": "compatible"},
                    "source_provenance": {
                        **item["source_provenance"],
                        "source_id": shared_source_id,
                    },
                }
                for item in evidence_items[:2]
            ],
        },
    }
    manager_output = build_fixture_manager_outputs(packet_artifact={"cases": [packet_case]})[0][
        "manager_output"
    ]
    first_result = manager_output["item_results"][0]
    first_result["evidence_used"] = [shared_source_id]
    first_result["food_name"] = packet_case["manager_evidence_packet"]["evidence_items"][0][
        "canonical_name"
    ]
    first_result["kcal_range"] = [999, 1000]
    first_result["likely_kcal"] = 999

    result = evaluate_manager_output_against_packet(
        packet_case=packet_case,
        manager_output=manager_output,
    )

    assert result["status"] == "fail"
    assert "modifier_adjusted_kcal_without_packet_adjustment" in result["failure_families"]


def test_grokfast_fooddb_packet_diagnostic_ignores_empty_modifier_maps() -> None:
    packet_case = next(
        case for case in _packet_artifact()["cases"] if case["case_id"] == "boba_large_half_sugar"
    )
    packet_case = {
        **packet_case,
        "manager_evidence_packet": {
            **packet_case["manager_evidence_packet"],
            "evidence_items": [
                {
                    **packet_case["manager_evidence_packet"]["evidence_items"][0],
                    "modifier_compatibility": {},
                }
            ],
        },
    }
    manager_output = build_fixture_manager_outputs(packet_artifact={"cases": [packet_case]})[0][
        "manager_output"
    ]
    manager_output["item_results"][0]["kcal_range"] = [400, 520]
    manager_output["item_results"][0]["likely_kcal"] = 460

    result = evaluate_manager_output_against_packet(
        packet_case=packet_case,
        manager_output=manager_output,
    )

    assert result["status"] == "pass"
    assert "modifier_adjusted_kcal_without_packet_adjustment" not in result["failure_families"]


def test_grokfast_fooddb_packet_diagnostic_counts_shared_refs_from_unguarded_items() -> None:
    packet_case = next(
        case for case in _packet_artifact()["cases"] if case["case_id"] == "listed_luwei_components"
    )
    evidence_items = packet_case["manager_evidence_packet"]["evidence_items"]
    shared_source_id = evidence_items[0]["source_provenance"]["source_id"]
    packet_case = {
        **packet_case,
        "manager_evidence_packet": {
            **packet_case["manager_evidence_packet"],
            "evidence_items": [
                {
                    **evidence_items[0],
                    "modifier_compatibility": {"seasoning": "compatible"},
                    "source_provenance": {
                        **evidence_items[0]["source_provenance"],
                        "source_id": shared_source_id,
                    },
                },
                {
                    **evidence_items[1],
                    "modifier_compatibility": {},
                    "source_provenance": {
                        **evidence_items[1]["source_provenance"],
                        "source_id": shared_source_id,
                    },
                },
            ],
        },
    }
    manager_output = build_fixture_manager_outputs(packet_artifact={"cases": [packet_case]})[0][
        "manager_output"
    ]
    unguarded_item = packet_case["manager_evidence_packet"]["evidence_items"][1]
    manager_output["item_results"][1]["evidence_used"] = [shared_source_id]
    manager_output["item_results"][1]["kcal_range"] = unguarded_item["kcal_range"]
    manager_output["item_results"][1]["likely_kcal"] = unguarded_item["kcal_point"]

    result = evaluate_manager_output_against_packet(
        packet_case=packet_case,
        manager_output=manager_output,
    )

    assert result["status"] == "pass"
    assert "modifier_adjusted_kcal_without_packet_adjustment" not in result["failure_families"]


def test_grokfast_fooddb_packet_diagnostic_preserves_legacy_unsupported_modifier_family() -> None:
    packet_case = next(
        case for case in _packet_artifact()["cases"] if case["case_id"] == "boba_large_half_sugar"
    )
    packet_case = {
        **packet_case,
        "manager_evidence_packet": {
            **packet_case["manager_evidence_packet"],
            "evidence_items": [
                {
                    **packet_case["manager_evidence_packet"]["evidence_items"][0],
                    "modifier_compatibility": {"cup_size": "unsupported"},
                }
            ],
        },
    }
    manager_output = build_fixture_manager_outputs(packet_artifact={"cases": [packet_case]})[0][
        "manager_output"
    ]
    manager_output["item_results"][0]["kcal_range"] = [400, 520]

    result = evaluate_manager_output_against_packet(
        packet_case=packet_case,
        manager_output=manager_output,
    )

    assert result["status"] == "fail"
    assert "modifier_adjusted_kcal_without_packet_adjustment" in result["failure_families"]
    assert "unsupported_modifier_adjusted_kcal_range" in result["failure_families"]


def test_grokfast_fooddb_packet_diagnostic_allows_packet_authorized_modifier_adjustment() -> None:
    packet_case = next(
        case for case in _packet_artifact()["cases"] if case["case_id"] == "boba_large_half_sugar"
    )
    packet_case = {
        **packet_case,
        "manager_evidence_packet": {
            **packet_case["manager_evidence_packet"],
            "evidence_items": [
                {
                    **packet_case["manager_evidence_packet"]["evidence_items"][0],
                    "adjusted_kcal_range": [400, 520],
                    "adjusted_kcal_point": 460,
                    "modifier_adjustment_authority": "packet_authorized",
                }
            ],
        },
    }
    manager_output = build_fixture_manager_outputs(packet_artifact={"cases": [packet_case]})[0][
        "manager_output"
    ]
    manager_output["item_results"][0]["kcal_range"] = [400, 520]
    manager_output["item_results"][0]["likely_kcal"] = 460

    result = evaluate_manager_output_against_packet(
        packet_case=packet_case,
        manager_output=manager_output,
    )

    assert result["status"] == "pass"


def test_grokfast_fooddb_packet_projection_can_use_tool_evidence_result_without_backend_leak() -> None:
    packet_artifact = build_packet_artifact_from_tool_evidence_result(
        tool_evidence_artifact=_tool_evidence_artifact()
    )

    assert packet_artifact["summary"]["tool_evidence_result_used"] is True
    first_case = packet_artifact["cases"][0]
    payload = build_live_manager_payload(packet_case=first_case)

    assert payload["tool_results"][0]["truth_level"] == "read_only_food_evidence_result"
    assert payload["tool_evidence_result"]["result_type"] == "tool_evidence_result_v1"
    assert payload["fooddb_evidence_packet"]["packet_type"] == "fooddb_manager_evidence_packet_v1"
    assert payload["expected_output_contract"]["required_top_level_fields"] == list(
        FOODDB_PACKET_MANAGER_REQUIRED_FIELDS
    )
    assert payload["expected_output_contract"]["forbidden_top_level_fields"] == ["tool_calls"]
    assert "local_json" not in str(payload)
    assert "adapter_diagnostics" not in str(payload)


def test_grokfast_fooddb_packet_smoke_cli_defaults_to_fixture_and_blocks_accidental_live(tmp_path: Path) -> None:
    from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact
    from scripts.run_accurate_intake_grokfast_fooddb_packet_smoke import main

    packet_path = tmp_path / "packet.json"
    output = tmp_path / "diagnostic.json"
    write_json_artifact(packet_path, _packet_artifact())

    assert main(["--mode", "fixture", "--packet-smoke", str(packet_path), "--output", str(output)]) == 0
    artifact = read_json_artifact(output)
    assert artifact["live_provider_used"] is False
    assert artifact["summary"]["pass_count"] == 5

    tool_packet_path = tmp_path / "tool_packet.json"
    tool_output = tmp_path / "tool_diagnostic.json"
    write_json_artifact(tool_packet_path, _tool_evidence_artifact())
    assert (
        main(
            [
                "--mode",
                "fixture",
                "--tool-evidence-result",
                str(tool_packet_path),
                "--output",
                str(tool_output),
            ]
        )
        == 0
    )
    tool_artifact = read_json_artifact(tool_output)
    assert tool_artifact["packet_artifact_type"] == "accurate_intake_fooddb_manager_packet_smoke"
    assert tool_artifact["summary"]["pass_count"] == 5

    blocked_output = tmp_path / "blocked_live.json"
    assert main(["--mode", "live", "--packet-smoke", str(packet_path), "--output", str(blocked_output)]) == 2
    blocked = read_json_artifact(blocked_output)
    assert blocked["status"] == "blocked"
    assert blocked["failure_family"] == "live_mode_requires_explicit_allow_live"
