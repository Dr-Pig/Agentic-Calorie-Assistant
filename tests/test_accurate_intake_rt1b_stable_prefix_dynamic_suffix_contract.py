from __future__ import annotations

import asyncio

from scripts.run_accurate_intake_rt1b_stable_prefix_dynamic_suffix_contract import (
    build_rt1b_stable_prefix_dynamic_suffix_contract_artifact,
)


def test_rt1b_stable_prefix_dynamic_suffix_contract_passes_and_targets_gate() -> None:
    artifact = asyncio.run(build_rt1b_stable_prefix_dynamic_suffix_contract_artifact())

    assert artifact["status"] == "pass"
    assert artifact["target_manager_runtime_gate"] == "rt1b_stable_prefix_dynamic_suffix_contract"
    assert artifact["pass_type"] == "contract"
    assert artifact["summary"]["case_count"] == 4
    assert artifact["summary"]["passed_case_count"] == 4


def test_rt1b_keeps_system_prompt_static_and_runtime_state_dynamic() -> None:
    artifact = asyncio.run(build_rt1b_stable_prefix_dynamic_suffix_contract_artifact())
    by_id = {case["case_id"]: case for case in artifact["cases"]}

    system_vs_dynamic = by_id["system_prompt_stays_static_and_dynamic_payload_carries_runtime_state"]["observed"]
    assert "available_tools" in system_vs_dynamic["user_payload_keys"]
    assert "tool_results" in system_vs_dynamic["user_payload_keys"]

    tool_order = by_id["available_tools_are_stably_normalized_for_prefix_reuse"]["observed"]
    assert tool_order["available_tools"] == ["body.get_latest_observation", "budget.get_today_summary"]


def test_rt1b_keeps_provider_metadata_on_trace_side_only() -> None:
    artifact = asyncio.run(build_rt1b_stable_prefix_dynamic_suffix_contract_artifact())
    by_id = {case["case_id"]: case for case in artifact["cases"]}

    provider_trace = by_id["provider_trace_stays_trace_side_and_not_prompt_side"]["observed"]
    assert provider_trace["provider"] == "fake_provider"
    assert provider_trace["manager_model"] == "fake-model"


def test_rt1b_records_prompt_layer_and_cache_profile_without_prompt_payload_leakage() -> None:
    artifact = asyncio.run(build_rt1b_stable_prefix_dynamic_suffix_contract_artifact())
    by_id = {case["case_id"]: case for case in artifact["cases"]}

    observed = by_id["prompt_layer_contract_supports_prefix_cache_and_progressive_disclosure"]["observed"]
    assert observed["contract_version"] == "manager_prompt_layer_contract.v1"
    assert observed["system_prompt_layer"] == "static_prefix"
    assert observed["runtime_payload_layer"] == "dynamic_suffix"
    assert observed["provider_profile_layer"] == "transport_overlay_trace_only"
    assert observed["prompt_cache_profile"]["static_prefix_first"] is True
    assert observed["prompt_cache_profile"]["dynamic_context_last"] is True
    assert observed["progressive_disclosure"]["full_context_in_user_payload"] is True
