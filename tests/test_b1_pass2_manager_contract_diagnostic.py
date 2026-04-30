from __future__ import annotations

from scripts.run_b1_pass2_manager_contract_diagnostic import (
    build_pass2_contract_artifact,
    classify_pass2_probe_result,
)


def test_pass2_diagnostic_classifies_answer_contract_bridge_as_compatibility_output() -> None:
    result = classify_pass2_probe_result(
        {
            "case_id": "B1-003",
            "profile_id": "builderspace-deepseek-default",
            "model": "deepseek",
            "prompt_variant": "current",
            "schema_variant": "current",
            "status": "success",
            "parsed_object": {
                "manager_action": "final",
                "answer_contract": {
                    "item_results": [{"item_name": "bento"}],
                    "kcal_range": [550, 960],
                    "likely_kcal": 750,
                    "uncertainty": "medium",
                    "evidence_used": ["generic_food_db:bento"],
                },
            },
            "trace": {"structured_output_transport_mode": "json_schema"},
        }
    )

    assert result["failure_family"] == "answer_contract_bridge_item_results"
    assert result["top_level_item_results_present"] is False
    assert result["answer_contract_item_results_present"] is True
    assert result["item_results_source"] == "answer_contract_bridge"
    assert result["item_results_owner_class"] == "compatibility_bridge"
    assert result["bounded_repair_attempted"] is False


def test_pass2_diagnostic_top_level_item_results_take_precedence_over_bridge() -> None:
    result = classify_pass2_probe_result(
        {
            "case_id": "B1-003",
            "profile_id": "builderspace-grok-4-fast-b1-pass2-probe",
            "model": "grok-4-fast",
            "prompt_variant": "current",
            "schema_variant": "current",
            "status": "success",
            "parsed_object": {
                "manager_action": "final",
                "item_results": [{"food_name": "bento", "likely_kcal": 750, "kcal_range": [550, 960]}],
                "answer_contract": {"item_results": [{"item_name": "compat"}]},
            },
            "trace": {"structured_output_transport_mode": "json_schema"},
        }
    )

    assert result["failure_family"] is None
    assert result["top_level_item_results_present"] is True
    assert result["answer_contract_item_results_present"] is True
    assert result["item_results_source"] == "manager_pass_2_payload"
    assert result["item_results_owner_class"] == "runtime_payload"


def test_pass2_artifact_classifies_deepseek_gap_when_grok_current_passes() -> None:
    artifact = build_pass2_contract_artifact(
        results=[
            {
                "case_id": "B1-003",
                "profile_id": "builderspace-deepseek-default",
                "model": "deepseek",
                "prompt_variant": "current",
                "schema_variant": "current",
                "status": "success",
                "parsed_object": {"answer_contract": {"item_results": [{"item_name": "bento"}]}},
            },
            {
                "case_id": "B1-003",
                "profile_id": "builderspace-grok-4-fast-b1-pass2-probe",
                "model": "grok-4-fast",
                "prompt_variant": "current",
                "schema_variant": "current",
                "status": "success",
                "parsed_object": {"item_results": [{"food_name": "bento"}], "answer_contract": {}},
            },
        ],
        generated_at_utc="2026-04-30T00:00:00Z",
    )

    assert artifact["artifact_type"] == "b1_pass2_manager_contract_diagnostic"
    assert artifact["readiness_claimed"] is False
    assert artifact["not_b1_readiness_evidence"] is True
    assert artifact["summary"]["root_cause"] == "deepseek_pass2_contract_non_adherence"
    assert artifact["summary"]["pass_count"] == 1
    assert artifact["summary"]["fail_count"] == 1


def test_pass2_artifact_classifies_prompt_contract_mismatch_when_tightened_prompt_fixes_bridge() -> None:
    artifact = build_pass2_contract_artifact(
        results=[
            {
                "case_id": "B1-003",
                "profile_id": "builderspace-deepseek-default",
                "model": "deepseek",
                "prompt_variant": "current",
                "schema_variant": "current",
                "status": "success",
                "parsed_object": {"answer_contract": {"item_results": [{"item_name": "bento"}]}},
            },
            {
                "case_id": "B1-003",
                "profile_id": "builderspace-grok-4-fast-b1-pass2-probe",
                "model": "grok-4-fast",
                "prompt_variant": "current",
                "schema_variant": "current",
                "status": "success",
                "parsed_object": {"answer_contract": {"item_results": [{"item_name": "bento"}]}},
            },
            {
                "case_id": "B1-003",
                "profile_id": "builderspace-deepseek-default",
                "model": "deepseek",
                "prompt_variant": "tightened_top_level_item_results",
                "schema_variant": "tightened_top_level_item_results",
                "status": "success",
                "parsed_object": {"item_results": [{"food_name": "bento"}], "answer_contract": {}},
            },
        ],
        generated_at_utc="2026-04-30T00:00:00Z",
    )

    assert artifact["summary"]["root_cause"] == "pass2_prompt_contract_mismatch"
    assert artifact["summary"]["failure_families"] == ["answer_contract_bridge_item_results"]


def test_pass2_artifact_classifies_schema_gap_when_tightened_variants_still_bridge() -> None:
    artifact = build_pass2_contract_artifact(
        results=[
            {
                "case_id": "B1-003",
                "profile_id": "builderspace-deepseek-default",
                "model": "deepseek",
                "prompt_variant": "current",
                "schema_variant": "current",
                "status": "success",
                "parsed_object": {"answer_contract": {"item_results": [{"item_name": "bento"}]}},
            },
            {
                "case_id": "B1-003",
                "profile_id": "builderspace-grok-4-fast-b1-pass2-probe",
                "model": "grok-4-fast",
                "prompt_variant": "current",
                "schema_variant": "current",
                "status": "success",
                "parsed_object": {"answer_contract": {"item_results": [{"item_name": "bento"}]}},
            },
            {
                "case_id": "B1-003",
                "profile_id": "builderspace-deepseek-default",
                "model": "deepseek",
                "prompt_variant": "tightened_top_level_item_results",
                "schema_variant": "tightened_top_level_item_results",
                "status": "success",
                "parsed_object": {"answer_contract": {"item_results": [{"item_name": "bento"}]}},
            },
            {
                "case_id": "B1-003",
                "profile_id": "builderspace-grok-4-fast-b1-pass2-probe",
                "model": "grok-4-fast",
                "prompt_variant": "tightened_top_level_item_results",
                "schema_variant": "tightened_top_level_item_results",
                "status": "success",
                "parsed_object": {"answer_contract": {"item_results": [{"item_name": "bento"}]}},
            },
        ],
        generated_at_utc="2026-04-30T00:00:00Z",
    )

    assert artifact["summary"]["root_cause"] == "schema_not_enforced_or_provider_contract_gap"
