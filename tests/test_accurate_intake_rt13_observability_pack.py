from __future__ import annotations

from scripts.run_accurate_intake_rt13_observability_pack import build_rt13_observability_pack_artifact


def test_rt13_observability_pack_artifact_passes_and_targets_gate() -> None:
    artifact = build_rt13_observability_pack_artifact()

    assert artifact["status"] == "pass"
    assert artifact["target_manager_runtime_gate"] == "rt13_observability_pack"
    assert artifact["pass_type"] == "contract"
    assert artifact["summary"]["case_count"] == 5
    assert artifact["summary"]["passed_case_count"] == 5
    assert "react_trace_call_topology" in artifact["summary"]["observability_contracts"]
    assert "react_trace_layer_latency" in artifact["summary"]["observability_contracts"]


def test_rt13_observability_pack_records_prompt_registry_and_trace_lineage() -> None:
    artifact = build_rt13_observability_pack_artifact()
    by_id = {case["case_id"]: case for case in artifact["cases"]}

    prompt_registry = by_id["prompt_registry_versions_and_overlay_split"]["observed"]
    assert prompt_registry["system_prompt_id"] == "single_manager_system_prompt"
    assert prompt_registry["tool_surface_version"] == "current_shell_public_tools.v1"
    assert prompt_registry["model_profile_overlay_transport_mode"] == "structured_outputs"

    react_trace = by_id["react_trace_contains_passes_and_tool_lineage"]["observed"]
    assert react_trace["trace_schema_version"] == "manager_react_trace.v1"
    assert react_trace["requested_tools"] == ["estimate_nutrition", "compare_against_budget"]
    assert react_trace["executed_tools"] == ["estimate_nutrition", "compare_against_budget"]
    assert react_trace["manager_round_count"] == 2
    assert react_trace["manager_round_latency_ms"] == [180, 260]
    assert react_trace["tool_batch_latency_ms"] == 420
    assert react_trace["guard_latency_ms"] == 40
    assert react_trace["tool_call_count"] == 2
    assert react_trace["total_latency_ms"] == 980
    assert react_trace["orchestration_latency_ms"] == 80
    assert [event["operation"] for event in react_trace["call_topology"]] == [
        "manager_provider_round",
        "tool_batch",
        "manager_provider_round",
        "guard_check",
    ]
    assert (
        react_trace["manager_pass_1"]["prompt_layer_contract"]["contract_version"]
        == "manager_prompt_layer_contract.v1"
    )


def test_rt13_observability_pack_records_request_links_and_latency_contracts() -> None:
    artifact = build_rt13_observability_pack_artifact()
    by_id = {case["case_id"]: case for case in artifact["cases"]}

    trace_refs = by_id["trace_refs_include_public_and_internal_request_linkage"]["observed"]
    assert trace_refs["public_refs"] == {"request_id": "rt13-request"}
    assert trace_refs["internal_refs"]["admin_trace_url"] == "/admin/trace/rt13-request"
    assert trace_refs["internal_refs"]["request_trace_path"].endswith("rt13-request.json")

    latency = by_id["latency_tracking_summarizes_passes_and_tools"]["observed"]
    assert latency["total_duration_ms"] == 860
    assert latency["slowest_step_name"] == "tool_batch"
    assert latency["tools_used"] == ["estimate_nutrition", "compare_against_budget"]

    buckets = by_id["route_latency_bucket_thresholds_are_stable"]["observed"]
    assert buckets == {
        "1999": "<2s",
        "2000": "2-4s",
        "3999": "2-4s",
        "4000": "4-8s",
        "7999": "4-8s",
        "8000": ">8s",
    }
