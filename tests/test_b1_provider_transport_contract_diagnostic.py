from __future__ import annotations

from scripts.run_b1_provider_transport_contract_diagnostic import (
    build_transport_contract_artifact,
    classify_transport_case_result,
)


def test_transport_diagnostic_classifies_json_schema_search_as_schema_not_enforced() -> None:
    result = classify_transport_case_result(
        {
            "case_id": "B1-001",
            "transport_mode": "json_schema",
            "profile_id": "builderspace-deepseek-default",
            "model": "deepseek",
            "status": "success",
            "parsed_object": {
                "manager_action": "call_tools",
                "tool_calls": [{"name": "search", "arguments": {"query": "tea egg"}}],
            },
            "trace": {
                "structured_output_transport_attempted": True,
                "structured_output_transport_mode": "json_schema",
                "effective_response_format_type": "json_schema",
            },
        }
    )

    assert result["failure_family"] == "schema_not_enforced"
    assert result["canonical_tool_enum_enforced"] is False
    assert result["unsupported_tool_names"] == ["search"]
    assert result["alias_normalized"] is False


def test_transport_diagnostic_classifies_tool_choice_rejection_from_http_400() -> None:
    result = classify_transport_case_result(
        {
            "case_id": "B1-004",
            "transport_mode": "tool_choice",
            "profile_id": "builderspace-grok-4-fast-b1004-probe",
            "model": "grok-4-fast",
            "status": "error",
            "trace": {
                "response_status": 400,
                "failure_family": "tool_choice_rejected",
                "decision_transport_attempted": True,
                "decision_transport_accepted": False,
                "raw_response_excerpt": "{\"error\":{\"message\":\"tool_choice not accepted\"}}",
            },
        }
    )

    assert result["failure_family"] == "tool_choice_rejected"
    assert result["provider_accepted_transport"] is False
    assert "tool_choice not accepted" in result["raw_response_excerpt"]


def test_transport_contract_artifact_never_claims_b1_readiness() -> None:
    artifact = build_transport_contract_artifact(
        results=[
            {
                "case_id": "B1-001",
                "transport_mode": "json_schema",
                "profile_id": "builderspace-deepseek-default",
                "model": "deepseek",
                "status": "success",
                "failure_family": "schema_not_enforced",
                "canonical_tool_enum_enforced": False,
            }
        ],
        generated_at_utc="2026-04-30T00:00:00Z",
    )

    assert artifact["artifact_type"] == "b1_provider_transport_contract_diagnostic"
    assert artifact["readiness_claimed"] is False
    assert artifact["not_b1_readiness_evidence"] is True
    assert artifact["tavily_live_invoked"] is False
    assert artifact["summary"]["failure_families"] == ["schema_not_enforced"]
    assert artifact["summary"]["viable_transport_profiles"] == []
