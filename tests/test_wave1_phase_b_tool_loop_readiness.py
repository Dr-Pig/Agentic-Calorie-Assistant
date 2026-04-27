from __future__ import annotations

import copy
import json
from pathlib import Path

from scripts.verify_wave1_phase_b_tool_loop_readiness import verify_phase_b_readiness


CORE_CASES = [
    "我吃了一顆茶葉蛋",
    "我喝了一杯珍珠奶茶",
    "我吃了一個便當",
    "我吃了滷味",
    "我吃了豆干、海帶、貢丸的滷味",
    "珍珠奶茶大概多少熱量？",
]


def _write_json(path: Path, payload: dict[str, object]) -> Path:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _provider_params() -> dict[str, object]:
    return {
        "provider": "builderspace",
        "model": "deepseek",
        "temperature": 0,
        "max_tokens": 1400,
        "response_format": "json_schema",
        "timeout": 45,
        "retry_policy": {"max_attempts": 1},
        "tool_choice": "none",
        "request_id": "req_123",
    }


def _mutation(*, attempted: bool, reason: str, result: dict[str, object] | None = None) -> dict[str, object]:
    return {
        "mutation_attempted": attempted,
        "reason": reason,
        "mutation_result": result,
    }


def _with_fixture_metadata(packet: dict[str, object], *, case_id: str) -> dict[str, object]:
    packet = dict(packet)
    packet.setdefault("fixture_id", f"fixture_{case_id}_{packet.get('packet_type')}")
    packet.setdefault("fixture_hash", f"hash_{case_id}_{packet.get('packet_type')}")
    packet.setdefault("fixture_only", True)
    packet.setdefault("generated_by", "deterministic_fixture")
    return packet


def valid_phase_b_trace_fixture(
    case_id: str,
    *,
    prompt: str,
    canary: bool = False,
    self_selected_without_ingredients: bool = False,
    listed_luwei: bool = False,
    no_mutation: bool = False,
) -> dict[str, object]:
    requested_tools = ["lookup_generic_food"]
    allowed_tools = ["lookup_generic_food"]
    filtered_plan = ["lookup_generic_food"]
    blocked_tools: list[str] = []
    block_reasons: list[dict[str, str]] = []
    read_tool_executions = [
        {
            "tool_name": "lookup_generic_food",
            "raw_tool_output_ref": f"artifacts/raw/{case_id}.json",
            "output": {"truth_level": "candidate", "candidate": {"food_name": "tea egg"}},
        }
    ]
    packet = {
        "packet_type": "GenericFoodDbPacket",
        "truth_level": "candidate",
        "fixture_id": f"fixture_{case_id}_generic",
        "fixture_hash": f"hash_{case_id}_generic",
        "fixture_only": True,
        "generated_by": "deterministic_fixture",
        "candidates": [{"food_name": "tea egg", "kcal_range": [70, 90]}],
    }

    if self_selected_without_ingredients:
        requested_tools = ["lookup_generic_food", "retrieve_web_food_evidence"]
        allowed_tools = []
        filtered_plan = []
        blocked_tools = ["lookup_generic_food", "retrieve_web_food_evidence"]
        block_reasons = [
            {
                "rule": "self_selected_basket_without_ingredients_blocks_estimate_tools",
                "detail": "Composition is unknown; ask for ingredients before generic DB or web estimate.",
            }
        ]
        read_tool_executions = []
        packet = {
            "packet_type": "TaiwanSkillPacket",
            "truth_level": "rule_hint",
            "rule_id": "self_selected_basket_without_ingredients",
        }

    if listed_luwei:
        requested_tools = ["lookup_generic_food"]
        allowed_tools = ["lookup_generic_food"]
        filtered_plan = ["lookup_generic_food"]
        read_tool_executions = [
            {
                "tool_name": "lookup_generic_food",
                "raw_tool_output_ref": f"artifacts/raw/{case_id}_dougan.json",
                "output": {"truth_level": "candidate", "candidate": {"food_name": "豆干"}},
            },
            {
                "tool_name": "lookup_generic_food",
                "raw_tool_output_ref": f"artifacts/raw/{case_id}_haidai.json",
                "output": {"truth_level": "candidate", "candidate": {"food_name": "海帶"}},
            },
            {
                "tool_name": "lookup_generic_food",
                "raw_tool_output_ref": f"artifacts/raw/{case_id}_gongwan.json",
                "output": {"truth_level": "candidate", "candidate": {"food_name": "貢丸"}},
            },
        ]
        packet = {
            "packet_type": "GenericFoodDbPacket",
            "truth_level": "candidate",
            "candidates": [{"food_name": "豆干"}, {"food_name": "海帶"}, {"food_name": "貢丸"}],
        }

    if canary:
        packet = {
            "packet_type": "SearchCandidatePacket",
            "truth_level": "candidate",
            "query": "matsusaka beef bowl calories",
            "source_quality_label": "brand_menu",
        }

    mutation = (
        _mutation(attempted=False, reason="no_mutation_intent", result=None)
        if no_mutation or canary or self_selected_without_ingredients
        else _mutation(
            attempted=True,
            reason="guard_approved_logging",
            result={"truth_level": "mutation_result", "ledger_item_ids": [f"item_{case_id}"]},
        )
    )

    item_results = [
        {
            "food_name": "tea egg",
            "kcal_range": [70, 90],
            "likely_kcal": 80,
            "uncertainty": "low",
            "evidence_used": ["generic_db_candidate"],
        }
    ]
    packet = _with_fixture_metadata(packet, case_id=case_id)

    return {
        "case_id": case_id,
        "input_message": prompt,
        "case_started_at_utc": "2026-04-25T00:00:00Z",
        "case_ended_at_utc": "2026-04-25T00:00:01Z",
        "case_latency_ms": 1000,
        "is_live_tavily_canary": canary,
        "uses_deterministic_stub_fixtures": not canary,
        "stub_fixture_source": None if canary else "tests/fixtures/phase_b_stub_packets.json",
        "stub_generated_by_llm": False,
        "manager_pass_1": {
            "manager_round": 0,
            "manager_role": "pass_1_tool_request",
            "prompt_hash": f"pass1_hash_{case_id}",
            "started_at_utc": "2026-04-25T00:00:00Z",
            "ended_at_utc": "2026-04-25T00:00:00.400000Z",
            "latency_ms": 400,
            "provider_params": _provider_params(),
            "requested_read_tools": requested_tools,
            "forbidden_final_truth_fields_present": [],
            "decision_payload": {"manager_action": "call_tools"},
            "decision_payload_type": "dict",
            "payload_shape_valid": True,
            "payload_shape_error": None,
        },
        "runtime_tool_router": {
            "requested_read_tools": requested_tools,
            "manager_requested_tools": requested_tools,
            "allowed_tools": allowed_tools,
            "filtered_tool_plan": filtered_plan,
            "blocked_tools": blocked_tools,
            "block_reasons": block_reasons,
            "available_read_tools": [
                "lookup_generic_food",
                "retrieve_web_food_evidence",
                "load_taiwan_food_semantics_skill",
            ],
            "canonical_tool_catalog_hash": "canonical_tools_hash",
        },
        "read_tool_executions": read_tool_executions,
        "packetizer": {
            "outputs": [packet],
            "forbidden_final_truth_fields_present": [],
        },
        "manager_pass_2": {
            "manager_round": 1,
            "manager_role": "pass_2_synthesis",
            "prompt_hash": f"pass2_hash_{case_id}",
            "started_at_utc": "2026-04-25T00:00:00.500000Z",
            "ended_at_utc": "2026-04-25T00:00:00.900000Z",
            "latency_ms": 400,
            "provider_params": _provider_params(),
            "item_results": item_results,
            "mutation_attempted": False,
            "forbidden_mutation_fields_present": [],
            "decision_payload": {"manager_action": "final"},
            "decision_payload_type": "dict",
            "payload_shape_valid": True,
            "payload_shape_error": None,
        },
        "guard": {
            "ran": True,
            "ran_before_mutation": True,
            "result": "no_mutation" if not mutation["mutation_attempted"] else "pass",
        },
        "mutation": mutation,
        "renderer": {
            "input": {
                "allowed_facts": ["tea egg candidate", "logged item ids are from mutation_result"],
                "forbidden_claims": ["invent calories not in item_results"],
                "item_results": item_results,
                "ledger_mutation_result": mutation["mutation_result"],
            },
            "final_response": "Recorded using allowed facts.",
            "invented_facts": [],
        },
        "tavily_canary": {
            "query": "matsusaka beef bowl calories",
            "search_depth": "advanced",
            "max_results": 3,
            "chunks_per_source": 2,
            "provider_params": {"provider": "tavily", "request_id": "tav_123"},
            "raw_results_ref": f"artifacts/raw/{case_id}_tavily.json",
            "latency_ms": 321,
            "call_count": 1,
            "packetized_candidate_present": True,
            "manager_pass_2_saw_search_packet": True,
        }
        if canary
        else None,
    }


def valid_phase_b_report_fixture(tmp_path: Path) -> Path:
    traces = [
        valid_phase_b_trace_fixture("B1-001", prompt="我吃了一顆茶葉蛋"),
        valid_phase_b_trace_fixture("B1-002", prompt="我喝了一杯珍珠奶茶"),
        valid_phase_b_trace_fixture("B1-003", prompt="我吃了一個便當"),
        valid_phase_b_trace_fixture("B1-004", prompt="我吃了滷味", self_selected_without_ingredients=True),
        valid_phase_b_trace_fixture("B1-005", prompt="我吃了豆干、海帶、貢丸的滷味", listed_luwei=True),
        valid_phase_b_trace_fixture("B1-006", prompt="珍珠奶茶大概多少熱量？", no_mutation=True),
        valid_phase_b_trace_fixture("B1-CANARY-001", prompt="松屋特盛牛丼", canary=True),
    ]
    return _write_json(
        tmp_path / "phase_b_report.json",
        {
            "phase": "B1",
            "provider": "builderspace",
            "manager_model": "deepseek",
            "mode": "hybrid_canary",
            "pass1_mode": "forced_tool_request_smoke",
            "forced_tool_request_contract": True,
            "manager_tool_selection_claimed": False,
            "natural_tool_selection_pass": "not_applicable",
            "runtime_latency": {
                "latency_budget_type": "b1_full_smoke_reporting_target",
                "not_user_runtime_budget": True,
                "full_smoke_target_ms": 180000,
                "total_latency_ms": 7000,
                "trace_count": len(traces),
                "completed_trace_count": len(traces),
                "mode": "forced_tool_request_smoke",
            },
            "core_smoke_cases_run": CORE_CASES,
            "tool_loop_traces": traces,
        },
    )


def invalid_phase_b_report_fixture(tmp_path: Path, mutator) -> Path:
    phase_b = valid_phase_b_report_fixture(tmp_path)
    data = json.loads(phase_b.read_text(encoding="utf-8"))
    mutator(data)
    phase_b.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return phase_b


def _active_spec(tmp_path: Path, text: str = "Phase B active spec uses canonical fields only.\n") -> Path:
    spec = tmp_path / "phase_b_spec.md"
    spec.write_text(text, encoding="utf-8")
    return spec


def test_valid_phase_b_trace_fixture_is_ready(tmp_path: Path) -> None:
    report = verify_phase_b_readiness(
        phase_b_report_path=valid_phase_b_report_fixture(tmp_path),
        active_paths=[_active_spec(tmp_path)],
    )

    assert report["ready_for_phase_b1_implementation"] is True
    assert report["blockers"] == []
    assert report["forced_loop_scaffold_pass"] is True
    assert report["runtime_latency_status"] == "pass"
    assert report["runtime_latency_pass"] is True
    assert report["mode_verdicts"]["forced_loop_scaffold_pass"] is True
    assert report["recommended_next_steps_ordered"] == ["proceed_to_phase_b1_minimal_tool_loop_implementation"]


def test_missing_provider_params_blocks_readiness(tmp_path: Path) -> None:
    phase_b = invalid_phase_b_report_fixture(
        tmp_path,
        lambda data: data["tool_loop_traces"][0]["manager_pass_1"]["provider_params"].pop("temperature"),
    )

    report = verify_phase_b_readiness(phase_b_report_path=phase_b, active_paths=[])

    assert any(item["code"] == "provider_params_missing" for item in report["blockers"])


def test_latency_over_target_warns_without_failing_quality(tmp_path: Path) -> None:
    def mutate(data: dict[str, object]) -> None:
        data["runtime_latency"]["total_latency_ms"] = 193000

    phase_b = invalid_phase_b_report_fixture(tmp_path, mutate)

    report = verify_phase_b_readiness(phase_b_report_path=phase_b, active_paths=[])

    assert report["quality_pass"] is True
    assert report["forced_loop_scaffold_pass"] is True
    assert report["runtime_latency_pass"] is False
    assert report["runtime_latency_status"] == "warning"
    assert any(item["code"] == "runtime_latency_over_target" for item in report["latency_warnings"])


def test_missing_latency_fields_block_readiness(tmp_path: Path) -> None:
    phase_b = invalid_phase_b_report_fixture(
        tmp_path,
        lambda data: data["tool_loop_traces"][0]["manager_pass_1"].pop("latency_ms"),
    )

    report = verify_phase_b_readiness(phase_b_report_path=phase_b, active_paths=[])

    assert report["runtime_latency_status"] == "blocker"
    assert any(item["code"] == "runtime_latency_trace_missing" for item in report["latency_blockers"])


def test_provider_timeout_blocks_readiness(tmp_path: Path) -> None:
    def mutate(data: dict[str, object]) -> None:
        data["provider_runtime"] = {
            "configured": True,
            "blocker": True,
            "reason": "provider_timeout",
            "timeout_ms": 180000,
        }

    phase_b = invalid_phase_b_report_fixture(tmp_path, mutate)

    report = verify_phase_b_readiness(phase_b_report_path=phase_b, active_paths=[])

    assert report["ready_for_phase_b1_implementation"] is False
    assert report["runtime_latency_status"] == "blocker"
    assert any(item["code"] == "provider_timeout" for item in report["latency_blockers"])


def test_provider_timeout_does_not_become_wrong_tool_request(tmp_path: Path) -> None:
    def mutate(data: dict[str, object]) -> None:
        data["pass1_mode"] = "natural_tool_selection_probe"
        data["forced_tool_request_contract"] = False
        data["manager_tool_selection_claimed"] = True
        data["provider_runtime"] = {
            "configured": True,
            "blocker": True,
            "reason": "provider_timeout",
            "timeout_ms": 180000,
        }
        data["tool_loop_traces"] = data["tool_loop_traces"][:1]
        trace = data["tool_loop_traces"][0]
        trace["manager_pass_1"]["requested_read_tools"] = []
        trace["runtime_tool_router"]["requested_read_tools"] = []
        trace["runtime_tool_router"]["manager_requested_tools"] = []
        trace["runtime_tool_router"]["allowed_tools"] = []
        trace["runtime_tool_router"]["filtered_tool_plan"] = []
        trace["read_tool_executions"] = []
        trace["packetizer"]["outputs"] = []

    phase_b = invalid_phase_b_report_fixture(tmp_path, mutate)

    report = verify_phase_b_readiness(phase_b_report_path=phase_b, active_paths=[])

    assert report["provider_runtime_attribution"]["tool_selection_status"] == "not_proven"
    assert report["natural_probe_failure_report"]["failure_family_counts"]["wrong_tool_request"] == 0


def test_natural_zero_trace_provider_error_is_not_proven_not_false_green(tmp_path: Path) -> None:
    phase_b = _write_json(
        tmp_path / "natural_provider_error.json",
        {
            "phase": "B-1",
            "provider": "builderspace",
            "manager_model": "deepseek",
            "mode": "hybrid_canary",
            "pass1_mode": "natural_tool_selection_probe",
            "forced_tool_request_contract": False,
            "manager_tool_selection_claimed": True,
            "natural_tool_selection_pass": False,
            "provider_runtime": {
                "configured": True,
                "blocker": True,
                "reason": "provider_runtime_error",
                "error_type": "BuilderSpaceResponseError",
            },
            "runtime_latency": {
                "latency_budget_type": "b1_full_smoke_reporting_target",
                "not_user_runtime_budget": True,
                "full_smoke_target_ms": 180000,
                "total_latency_ms": 15760,
                "trace_count": 0,
                "completed_trace_count": 0,
                "mode": "natural_tool_selection_probe",
            },
            "core_smoke_cases_run": [],
            "tool_loop_traces": [],
        },
    )

    report = verify_phase_b_readiness(phase_b_report_path=phase_b, active_paths=[])

    assert report["scaffold_pass"] is False
    assert report["quality_pass"] is False
    assert report["natural_tool_selection_pass"] == "not_proven"
    assert report["natural_tool_loop_completion_pass"] is False
    assert report["provider_runtime_attribution"]["tool_selection_status"] == "not_proven"
    failure_report = report["natural_probe_failure_report"]
    assert failure_report["provider_blocked_before_cases"] is True
    assert failure_report["completed_trace_count"] == 0
    assert failure_report["expected_case_count"] == len(CORE_CASES)
    assert failure_report["provider_runtime_reason"] == "provider_runtime_error"
    assert failure_report["failure_family_counts"]["manager_no_tool_request"] == 0
    assert failure_report["failure_family_counts"]["wrong_tool_request"] == 0
    assert failure_report["failure_family_counts"]["pass2_no_item_results"] == 0


def test_natural_zero_trace_runtime_blocker_is_not_proven_not_manager_failure(tmp_path: Path) -> None:
    phase_b = _write_json(
        tmp_path / "natural_runtime_blocker.json",
        {
            "phase": "B-1",
            "provider": "builderspace",
            "manager_model": "deepseek",
            "mode": "hybrid_canary",
            "pass1_mode": "natural_tool_selection_probe",
            "forced_tool_request_contract": False,
            "manager_tool_selection_claimed": True,
            "natural_tool_selection_pass": False,
            "runtime_blocker": {
                "blocker": True,
                "reason": "manager_payload_shape_error",
                "stage": "pass_1_tool_request",
                "round_index": 0,
                "decision_payload_type": "list",
                "decision_payload_excerpt": "[\"call_tools\"]",
                "completed_trace_count": 0,
                "expected_case_count": len(CORE_CASES),
            },
            "runtime_latency": {
                "latency_budget_type": "b1_full_smoke_reporting_target",
                "not_user_runtime_budget": True,
                "full_smoke_target_ms": 180000,
                "total_latency_ms": 15760,
                "trace_count": 0,
                "completed_trace_count": 0,
                "mode": "natural_tool_selection_probe",
            },
            "core_smoke_cases_run": CORE_CASES,
            "tool_loop_traces": [],
        },
    )

    report = verify_phase_b_readiness(phase_b_report_path=phase_b, active_paths=[])

    assert report["scaffold_pass"] is False
    assert report["quality_pass"] is False
    assert report["natural_tool_selection_pass"] == "not_proven"
    assert report["natural_tool_loop_completion_pass"] is False
    assert report["provider_runtime_attribution"]["tool_selection_status"] == "not_proven"
    failure_report = report["natural_probe_failure_report"]
    assert failure_report["provider_blocked_before_cases"] is True
    assert failure_report["provider_runtime_reason"] == "manager_payload_shape_error"
    assert failure_report["failure_family_counts"]["manager_no_tool_request"] == 0
    assert failure_report["failure_family_counts"]["wrong_tool_request"] == 0
    assert failure_report["failure_family_counts"]["pass2_no_item_results"] == 0


def test_natural_zero_trace_provider_trace_blocker_is_not_proven_not_manager_failure(tmp_path: Path) -> None:
    phase_b = _write_json(
        tmp_path / "natural_provider_trace_blocker.json",
        {
            "phase": "B-1",
            "provider": "builderspace",
            "manager_model": "deepseek",
            "mode": "hybrid_canary",
            "pass1_mode": "natural_tool_selection_probe",
            "forced_tool_request_contract": False,
            "manager_tool_selection_claimed": True,
            "natural_tool_selection_pass": False,
            "provider_trace_blocker": {
                "blocker": True,
                "reason": "provider_trace_shape_error",
                "trace_field": "request_payload",
                "observed_type": "array",
                "value_excerpt": "[]",
                "value_truncated": False,
                "stage": None,
                "failing_component": "normalize_provider_trace",
                "completed_trace_count": 0,
                "expected_case_count": len(CORE_CASES),
            },
            "runtime_latency": {
                "latency_budget_type": "b1_full_smoke_reporting_target",
                "not_user_runtime_budget": True,
                "full_smoke_target_ms": 180000,
                "total_latency_ms": 15760,
                "trace_count": 0,
                "completed_trace_count": 0,
                "mode": "natural_tool_selection_probe",
            },
            "core_smoke_cases_run": CORE_CASES,
            "tool_loop_traces": [],
        },
    )

    report = verify_phase_b_readiness(phase_b_report_path=phase_b, active_paths=[])

    assert report["scaffold_pass"] is False
    assert report["quality_pass"] is False
    assert report["natural_tool_selection_pass"] == "not_proven"
    assert report["natural_tool_loop_completion_pass"] is False
    assert report["provider_runtime_attribution"]["blocker_kind"] == "provider_trace_blocker"
    assert report["provider_runtime_attribution"]["tool_selection_status"] == "not_proven"
    assert report["provider_runtime_attribution"]["failing_component"] == "normalize_provider_trace"
    failure_report = report["natural_probe_failure_report"]
    assert failure_report["provider_blocked_before_cases"] is True
    assert failure_report["provider_runtime_reason"] == "provider_trace_shape_error"
    assert failure_report["failure_family_counts"]["manager_no_tool_request"] == 0
    assert failure_report["failure_family_counts"]["wrong_tool_request"] == 0
    assert failure_report["failure_family_counts"]["pass2_no_item_results"] == 0


def test_forced_zero_trace_provider_error_fails_forced_scaffold(tmp_path: Path) -> None:
    phase_b = _write_json(
        tmp_path / "forced_provider_error.json",
        {
            "phase": "B-1",
            "provider": "builderspace",
            "manager_model": "deepseek",
            "mode": "hybrid_canary",
            "pass1_mode": "forced_tool_request_smoke",
            "forced_tool_request_contract": True,
            "manager_tool_selection_claimed": False,
            "natural_tool_selection_pass": "not_applicable",
            "provider_runtime": {
                "configured": True,
                "blocker": True,
                "reason": "provider_runtime_error",
                "error_type": "BuilderSpaceResponseError",
            },
            "runtime_latency": {
                "latency_budget_type": "b1_full_smoke_reporting_target",
                "not_user_runtime_budget": True,
                "full_smoke_target_ms": 180000,
                "total_latency_ms": 15760,
                "trace_count": 0,
                "completed_trace_count": 0,
                "mode": "forced_tool_request_smoke",
            },
            "core_smoke_cases_run": [],
            "tool_loop_traces": [],
        },
    )

    report = verify_phase_b_readiness(phase_b_report_path=phase_b, active_paths=[])

    assert report["scaffold_pass"] is False
    assert report["quality_pass"] is False
    assert report["forced_loop_scaffold_pass"] is False
    assert report["natural_tool_selection_pass"] == "not_applicable"


def test_forced_zero_trace_runtime_blocker_fails_forced_scaffold(tmp_path: Path) -> None:
    phase_b = _write_json(
        tmp_path / "forced_runtime_blocker.json",
        {
            "phase": "B-1",
            "provider": "builderspace",
            "manager_model": "deepseek",
            "mode": "hybrid_canary",
            "pass1_mode": "forced_tool_request_smoke",
            "forced_tool_request_contract": True,
            "manager_tool_selection_claimed": False,
            "natural_tool_selection_pass": "not_applicable",
            "runtime_blocker": {
                "blocker": True,
                "reason": "manager_payload_shape_error",
                "stage": "pass_1_tool_request",
                "round_index": 0,
                "decision_payload_type": "list",
                "decision_payload_excerpt": "[\"call_tools\"]",
                "completed_trace_count": 0,
                "expected_case_count": len(CORE_CASES),
            },
            "runtime_latency": {
                "latency_budget_type": "b1_full_smoke_reporting_target",
                "not_user_runtime_budget": True,
                "full_smoke_target_ms": 180000,
                "total_latency_ms": 15760,
                "trace_count": 0,
                "completed_trace_count": 0,
                "mode": "forced_tool_request_smoke",
            },
            "core_smoke_cases_run": CORE_CASES,
            "tool_loop_traces": [],
        },
    )

    report = verify_phase_b_readiness(phase_b_report_path=phase_b, active_paths=[])

    assert report["scaffold_pass"] is False
    assert report["quality_pass"] is False
    assert report["forced_loop_scaffold_pass"] is False
    assert report["natural_tool_selection_pass"] == "not_applicable"


def test_forced_zero_trace_provider_trace_blocker_fails_forced_scaffold(tmp_path: Path) -> None:
    phase_b = _write_json(
        tmp_path / "forced_provider_trace_blocker.json",
        {
            "phase": "B-1",
            "provider": "builderspace",
            "manager_model": "deepseek",
            "mode": "hybrid_canary",
            "pass1_mode": "forced_tool_request_smoke",
            "forced_tool_request_contract": True,
            "manager_tool_selection_claimed": False,
            "natural_tool_selection_pass": "not_applicable",
            "provider_trace_blocker": {
                "blocker": True,
                "reason": "provider_trace_shape_error",
                "trace_field": "trace",
                "observed_type": "array",
                "value_excerpt": "[\"bad-trace\"]",
                "value_truncated": False,
                "stage": None,
                "failing_component": "normalize_provider_trace",
                "completed_trace_count": 0,
                "expected_case_count": len(CORE_CASES),
            },
            "runtime_latency": {
                "latency_budget_type": "b1_full_smoke_reporting_target",
                "not_user_runtime_budget": True,
                "full_smoke_target_ms": 180000,
                "total_latency_ms": 15760,
                "trace_count": 0,
                "completed_trace_count": 0,
                "mode": "forced_tool_request_smoke",
            },
            "core_smoke_cases_run": CORE_CASES,
            "tool_loop_traces": [],
        },
    )

    report = verify_phase_b_readiness(phase_b_report_path=phase_b, active_paths=[])

    assert report["scaffold_pass"] is False
    assert report["quality_pass"] is False
    assert report["forced_loop_scaffold_pass"] is False
    assert report["provider_runtime_attribution"]["blocker_kind"] == "provider_trace_blocker"
    assert report["provider_runtime_attribution"]["failing_component"] == "normalize_provider_trace"


def test_partial_trace_provider_error_keeps_case_report_but_blocks_global_pass(tmp_path: Path) -> None:
    phase_b = valid_phase_b_report_fixture(tmp_path)
    data = json.loads(phase_b.read_text(encoding="utf-8"))
    data["pass1_mode"] = "natural_tool_selection_probe"
    data["forced_tool_request_contract"] = False
    data["manager_tool_selection_claimed"] = True
    data["provider_runtime"] = {
        "configured": True,
        "blocker": True,
        "reason": "provider_runtime_error",
        "error_type": "BuilderSpaceResponseError",
    }
    data["tool_loop_traces"] = data["tool_loop_traces"][:2]
    data["core_smoke_cases_run"] = CORE_CASES[:2]
    data["runtime_latency"]["mode"] = "natural_tool_selection_probe"
    data["runtime_latency"]["trace_count"] = 2
    data["runtime_latency"]["completed_trace_count"] = 2
    phase_b.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    report = verify_phase_b_readiness(phase_b_report_path=phase_b, active_paths=[])

    assert report["quality_pass"] is False
    assert report["natural_tool_selection_pass"] != True
    assert report["natural_tool_loop_completion_pass"] is False
    failure_report = report["natural_probe_failure_report"]
    assert failure_report["provider_blocked_before_all_cases_completed"] is True
    assert failure_report["completed_trace_count"] == 2
    assert failure_report["expected_case_count"] == len(CORE_CASES)
    assert len(failure_report["cases"]) == 2


def test_partial_trace_runtime_blocker_keeps_case_report_but_blocks_global_pass(tmp_path: Path) -> None:
    phase_b = valid_phase_b_report_fixture(tmp_path)
    data = json.loads(phase_b.read_text(encoding="utf-8"))
    data["pass1_mode"] = "natural_tool_selection_probe"
    data["forced_tool_request_contract"] = False
    data["manager_tool_selection_claimed"] = True
    data["runtime_blocker"] = {
        "blocker": True,
        "reason": "manager_payload_shape_error",
        "stage": "pass_2_synthesis",
        "round_index": 1,
        "decision_payload_type": "str",
        "decision_payload_excerpt": "\"final\"",
        "completed_trace_count": 2,
        "expected_case_count": len(CORE_CASES),
    }
    data["tool_loop_traces"] = data["tool_loop_traces"][:2]
    data["core_smoke_cases_run"] = CORE_CASES[:2]
    data["runtime_latency"]["mode"] = "natural_tool_selection_probe"
    data["runtime_latency"]["trace_count"] = 2
    data["runtime_latency"]["completed_trace_count"] = 2
    for trace in data["tool_loop_traces"]:
        trace["pass1_mode"] = "natural_tool_selection_probe"
        trace["forced_tool_request_contract"] = False
        trace["manager_tool_selection_claimed"] = True
    phase_b.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    report = verify_phase_b_readiness(phase_b_report_path=phase_b, active_paths=[])

    assert report["quality_pass"] is False
    assert report["natural_tool_selection_pass"] == "not_proven"
    assert report["natural_tool_loop_completion_pass"] is False
    failure_report = report["natural_probe_failure_report"]
    assert failure_report["provider_blocked_before_all_cases_completed"] is True
    assert failure_report["completed_trace_count"] == 2
    assert len(failure_report["cases"]) == 2


def test_partial_trace_provider_trace_blocker_keeps_case_report_but_blocks_global_pass(tmp_path: Path) -> None:
    phase_b = valid_phase_b_report_fixture(tmp_path)
    data = json.loads(phase_b.read_text(encoding="utf-8"))
    data["pass1_mode"] = "natural_tool_selection_probe"
    data["forced_tool_request_contract"] = False
    data["manager_tool_selection_claimed"] = True
    data["provider_trace_blocker"] = {
        "blocker": True,
        "reason": "provider_trace_shape_error",
        "trace_field": "request_payload",
        "observed_type": "string",
        "value_excerpt": "\"bad-request-payload\"",
        "value_truncated": False,
        "stage": None,
        "failing_component": "normalize_provider_trace",
        "completed_trace_count": 2,
        "expected_case_count": len(CORE_CASES),
    }
    data["tool_loop_traces"] = data["tool_loop_traces"][:2]
    data["core_smoke_cases_run"] = CORE_CASES[:2]
    data["runtime_latency"]["mode"] = "natural_tool_selection_probe"
    data["runtime_latency"]["trace_count"] = 2
    data["runtime_latency"]["completed_trace_count"] = 2
    for trace in data["tool_loop_traces"]:
        trace["pass1_mode"] = "natural_tool_selection_probe"
        trace["forced_tool_request_contract"] = False
        trace["manager_tool_selection_claimed"] = True
    phase_b.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    report = verify_phase_b_readiness(phase_b_report_path=phase_b, active_paths=[])

    assert report["quality_pass"] is False
    assert report["natural_tool_selection_pass"] == "not_proven"
    assert report["natural_tool_loop_completion_pass"] is False
    assert report["provider_runtime_attribution"]["blocker_kind"] == "provider_trace_blocker"
    assert report["provider_runtime_attribution"]["loop_completion_status"] == "blocked"
    failure_report = report["natural_probe_failure_report"]
    assert failure_report["provider_blocked_before_all_cases_completed"] is True
    assert failure_report["completed_trace_count"] == 2
    assert failure_report["expected_case_count"] == len(CORE_CASES)
    assert len(failure_report["cases"]) == 2


def test_pass2_mutation_attempt_blocks_readiness(tmp_path: Path) -> None:
    phase_b = invalid_phase_b_report_fixture(
        tmp_path,
        lambda data: data["tool_loop_traces"][0]["manager_pass_2"].update({"mutation_attempted": True}),
    )

    report = verify_phase_b_readiness(phase_b_report_path=phase_b, active_paths=[])

    assert any(item["code"] == "manager_pass_2_attempted_mutation" for item in report["blockers"])


def test_read_packet_final_truth_blocks_readiness(tmp_path: Path) -> None:
    phase_b = invalid_phase_b_report_fixture(
        tmp_path,
        lambda data: data["tool_loop_traces"][0]["read_tool_executions"][0]["output"].update({"truth_level": "final"}),
    )

    report = verify_phase_b_readiness(phase_b_report_path=phase_b, active_paths=[])

    assert any(item["code"] == "read_tool_truth_level_invalid" for item in report["blockers"])


def test_invalid_missing_allowed_tools_blocks_readiness(tmp_path: Path) -> None:
    phase_b = invalid_phase_b_report_fixture(
        tmp_path,
        lambda data: data["tool_loop_traces"][0]["runtime_tool_router"].pop("allowed_tools"),
    )

    report = verify_phase_b_readiness(phase_b_report_path=phase_b, active_paths=[])

    assert any(item["code"] == "tool_router_trace_incomplete" for item in report["blockers"])


def test_invalid_self_selected_basket_without_ingredients_did_not_block_db_tavily(tmp_path: Path) -> None:
    def mutate(data: dict[str, object]) -> None:
        router = data["tool_loop_traces"][3]["runtime_tool_router"]
        router["allowed_tools"] = ["lookup_generic_food", "retrieve_web_food_evidence"]
        router["filtered_tool_plan"] = ["lookup_generic_food", "retrieve_web_food_evidence"]
        router["blocked_tools"] = []
        router["block_reasons"] = []

    phase_b = invalid_phase_b_report_fixture(tmp_path, mutate)

    report = verify_phase_b_readiness(phase_b_report_path=phase_b, active_paths=[])

    assert any(
        item["code"] == "self_selected_basket_without_ingredients_estimate_tools_not_blocked"
        for item in report["blockers"]
    )


def test_invalid_missing_listed_luwei_case_blocks_readiness(tmp_path: Path) -> None:
    phase_b = invalid_phase_b_report_fixture(
        tmp_path,
        lambda data: data["core_smoke_cases_run"].remove("我吃了豆干、海帶、貢丸的滷味"),
    )

    report = verify_phase_b_readiness(phase_b_report_path=phase_b, active_paths=[])

    assert any(item["code"] == "core_smoke_case_missing" for item in report["blockers"])


def test_invalid_renderer_missing_allowed_facts_or_forbidden_claims_blocks_readiness(tmp_path: Path) -> None:
    def mutate(data: dict[str, object]) -> None:
        renderer_input = data["tool_loop_traces"][0]["renderer"]["input"]
        renderer_input.pop("allowed_facts")
        data["tool_loop_traces"][0]["renderer"]["final_response"] = "已記錄 999 大卡，今天還剩 500 大卡。"

    phase_b = invalid_phase_b_report_fixture(tmp_path, mutate)

    report = verify_phase_b_readiness(phase_b_report_path=phase_b, active_paths=[])

    assert any(item["code"] == "renderer_truth_boundary_failed" for item in report["blockers"])


def test_invalid_no_mutation_missing_reason_or_result_blocks_readiness(tmp_path: Path) -> None:
    def mutate(data: dict[str, object]) -> None:
        data["tool_loop_traces"][5]["mutation"] = {"mutation_attempted": False}

    phase_b = invalid_phase_b_report_fixture(tmp_path, mutate)

    report = verify_phase_b_readiness(phase_b_report_path=phase_b, active_paths=[])

    assert any(item["code"] == "mutation_trace_incomplete" for item in report["blockers"])


def test_invalid_tavily_source_quality_label_blocks_readiness(tmp_path: Path) -> None:
    def mutate(data: dict[str, object]) -> None:
        packet = data["tool_loop_traces"][-1]["packetizer"]["outputs"][0]
        packet["source_quality_label"] = "brand_or_menu_candidate"

    phase_b = invalid_phase_b_report_fixture(tmp_path, mutate)

    report = verify_phase_b_readiness(phase_b_report_path=phase_b, active_paths=[])

    assert any(item["code"] == "tavily_source_quality_label_invalid" for item in report["blockers"])


def test_tavily_canary_mutation_blocks_readiness(tmp_path: Path) -> None:
    phase_b = invalid_phase_b_report_fixture(
        tmp_path,
        lambda data: data["tool_loop_traces"][-1]["mutation"].update(
            {"mutation_attempted": True, "reason": "guard_approved_logging", "mutation_result": {"truth_level": "mutation_result"}}
        ),
    )

    report = verify_phase_b_readiness(phase_b_report_path=phase_b, active_paths=[])

    assert any(item["code"] == "tavily_canary_mutated_ledger" for item in report["blockers"])


def test_llm_generated_stub_blocks_readiness(tmp_path: Path) -> None:
    phase_b = invalid_phase_b_report_fixture(
        tmp_path,
        lambda data: data["tool_loop_traces"][0].update({"stub_generated_by_llm": True}),
    )

    report = verify_phase_b_readiness(phase_b_report_path=phase_b, active_paths=[])

    assert any(item["code"] == "stub_fixture_generated_by_llm" for item in report["blockers"])


def test_active_phase_b_legacy_vocab_blocks_readiness(tmp_path: Path) -> None:
    report = verify_phase_b_readiness(
        phase_b_report_path=valid_phase_b_report_fixture(tmp_path),
        active_paths=[_active_spec(tmp_path, "The active contract depends on thread_result.\n")],
    )

    assert any(item["code"] == "legacy_vocab_in_active_phase_b_surface" for item in report["blockers"])


def test_missing_manager_pass_prompt_trace_blocks_readiness(tmp_path: Path) -> None:
    phase_b = invalid_phase_b_report_fixture(
        tmp_path,
        lambda data: data["tool_loop_traces"][0]["manager_pass_1"].pop("manager_role"),
    )

    report = verify_phase_b_readiness(phase_b_report_path=phase_b, active_paths=[])

    assert any(item["code"] == "manager_pass_prompt_trace_missing" for item in report["blockers"])


def test_packetizer_fixture_metadata_missing_blocks_readiness(tmp_path: Path) -> None:
    phase_b = invalid_phase_b_report_fixture(
        tmp_path,
        lambda data: data["tool_loop_traces"][0]["packetizer"]["outputs"][0].pop("fixture_hash"),
    )

    report = verify_phase_b_readiness(phase_b_report_path=phase_b, active_paths=[])

    assert any(item["code"] == "packetizer_fixture_metadata_missing" for item in report["blockers"])


def test_pass2_forbidden_mutation_fields_block_readiness(tmp_path: Path) -> None:
    phase_b = invalid_phase_b_report_fixture(
        tmp_path,
        lambda data: data["tool_loop_traces"][0]["manager_pass_2"].update(
            {"forbidden_mutation_fields_present": ["mutation_result"]}
        ),
    )

    report = verify_phase_b_readiness(phase_b_report_path=phase_b, active_paths=[])

    assert any(item["code"] == "manager_pass_2_forbidden_mutation_fields_present" for item in report["blockers"])


def test_forced_mode_claiming_natural_tool_selection_blocks_readiness(tmp_path: Path) -> None:
    def mutate(data: dict[str, object]) -> None:
        data["forced_tool_request_contract"] = True
        data["manager_tool_selection_claimed"] = True
        data["natural_tool_selection_pass"] = True

    phase_b = invalid_phase_b_report_fixture(tmp_path, mutate)

    report = verify_phase_b_readiness(phase_b_report_path=phase_b, active_paths=[])

    assert any(item["code"] == "forced_mode_claimed_natural_tool_selection" for item in report["blockers"])
    assert report["natural_tool_selection_pass"] == "not_applicable"


def test_natural_probe_web_only_for_generic_food_fails_tool_selection(tmp_path: Path) -> None:
    def mutate(data: dict[str, object]) -> None:
        data["pass1_mode"] = "natural_tool_selection_probe"
        data["forced_tool_request_contract"] = False
        data["manager_tool_selection_claimed"] = True
        trace = data["tool_loop_traces"][0]
        trace["pass1_mode"] = "natural_tool_selection_probe"
        trace["forced_tool_request_contract"] = False
        trace["manager_tool_selection_claimed"] = True
        trace["manager_pass_1"]["requested_read_tools"] = ["retrieve_web_food_evidence"]
        trace["runtime_tool_router"]["requested_read_tools"] = ["retrieve_web_food_evidence"]
        trace["runtime_tool_router"]["manager_requested_tools"] = ["retrieve_web_food_evidence"]
        trace["runtime_tool_router"]["allowed_tools"] = ["retrieve_web_food_evidence"]
        trace["runtime_tool_router"]["filtered_tool_plan"] = ["retrieve_web_food_evidence"]

    phase_b = invalid_phase_b_report_fixture(tmp_path, mutate)

    report = verify_phase_b_readiness(phase_b_report_path=phase_b, active_paths=[])

    assert report["natural_tool_selection_pass"] is False
    assert any(item["code"] == "expected_tool_policy_mismatch" for item in report["blockers"])
    case_report = report["natural_probe_failure_report"]["cases"][0]
    assert case_report["expected_tool_policy"]["required_tools"] == ["lookup_generic_food"]
    assert case_report["actual_requested_read_tools"] == ["retrieve_web_food_evidence"]
    assert case_report["missing_or_wrong_tools"] == {
        "missing_required_tools": ["lookup_generic_food"],
        "wrong_tools": ["retrieve_web_food_evidence"],
    }
    assert case_report["failure_family"] == "wrong_tool_request"


def test_natural_probe_search_alias_is_router_validated_but_selection_still_fails(tmp_path: Path) -> None:
    def mutate(data: dict[str, object]) -> None:
        data["pass1_mode"] = "natural_tool_selection_probe"
        data["forced_tool_request_contract"] = False
        data["manager_tool_selection_claimed"] = True
        trace = data["tool_loop_traces"][0]
        trace["pass1_mode"] = "natural_tool_selection_probe"
        trace["forced_tool_request_contract"] = False
        trace["manager_tool_selection_claimed"] = True
        trace["manager_pass_1"]["requested_read_tools"] = ["search"]
        trace["runtime_tool_router"].update(
            {
                "requested_read_tools": ["search"],
                "manager_requested_tools": ["search"],
                "allowed_tools": [],
                "filtered_tool_plan": [],
                "blocked_tools": ["search"],
                "block_reasons": [
                    {
                        "tool_name": "search",
                        "reason": "unsupported_read_tool_name",
                        "supported_tools": [
                            "lookup_generic_food",
                            "retrieve_web_food_evidence",
                            "load_taiwan_food_semantics_skill",
                        ],
                        "normalization_attempted": False,
                    }
                ],
                "available_read_tools": [
                    "lookup_generic_food",
                    "retrieve_web_food_evidence",
                    "load_taiwan_food_semantics_skill",
                ],
                "canonical_tool_catalog_hash": "canonical_tools_hash",
            }
        )
        trace["read_tool_executions"] = []
        trace["packetizer"]["outputs"] = []
        trace["manager_pass_2"]["item_results"] = []

    phase_b = invalid_phase_b_report_fixture(tmp_path, mutate)

    report = verify_phase_b_readiness(phase_b_report_path=phase_b, active_paths=[])

    assert report["router_validation_pass"] is True
    assert report["natural_tool_selection_pass"] is False
    case_report = report["natural_probe_failure_report"]["cases"][0]
    assert case_report["failure_family"] == "wrong_tool_request"
    assert case_report["unsupported_tool_names"] == ["search"]
    assert case_report["missing_or_wrong_tools"] == {
        "missing_required_tools": ["lookup_generic_food"],
        "wrong_tools": ["search"],
    }


def test_natural_probe_listed_luwei_without_item_level_generic_lookup_fails_selection(tmp_path: Path) -> None:
    def mutate(data: dict[str, object]) -> None:
        data["pass1_mode"] = "natural_tool_selection_probe"
        data["forced_tool_request_contract"] = False
        data["manager_tool_selection_claimed"] = True
        trace = data["tool_loop_traces"][4]
        trace["pass1_mode"] = "natural_tool_selection_probe"
        trace["forced_tool_request_contract"] = False
        trace["manager_tool_selection_claimed"] = True
        trace["manager_pass_1"]["requested_read_tools"] = ["retrieve_web_food_evidence"]
        trace["runtime_tool_router"]["requested_read_tools"] = ["retrieve_web_food_evidence"]
        trace["runtime_tool_router"]["manager_requested_tools"] = ["retrieve_web_food_evidence"]
        trace["runtime_tool_router"]["allowed_tools"] = ["retrieve_web_food_evidence"]
        trace["runtime_tool_router"]["filtered_tool_plan"] = ["retrieve_web_food_evidence"]

    phase_b = invalid_phase_b_report_fixture(tmp_path, mutate)

    report = verify_phase_b_readiness(phase_b_report_path=phase_b, active_paths=[])

    assert report["natural_tool_selection_pass"] is False
    assert any(item["code"] == "expected_tool_policy_mismatch" for item in report["blockers"])
    case_report = report["natural_probe_failure_report"]["cases"][4]
    assert case_report["expected_tool_policy"]["required_tools"] == ["lookup_generic_food"]
    assert case_report["failure_family"] == "wrong_tool_request"


def test_natural_probe_failure_report_classifies_no_tool_request_and_blocking_boundary(tmp_path: Path) -> None:
    def mutate(data: dict[str, object]) -> None:
        data["pass1_mode"] = "natural_tool_selection_probe"
        data["forced_tool_request_contract"] = False
        data["manager_tool_selection_claimed"] = True
        for trace in data["tool_loop_traces"]:
            trace["pass1_mode"] = "natural_tool_selection_probe"
            trace["forced_tool_request_contract"] = False
            trace["manager_tool_selection_claimed"] = True
            trace["manager_pass_1"]["requested_read_tools"] = []
            trace["runtime_tool_router"]["requested_read_tools"] = []
            trace["runtime_tool_router"]["manager_requested_tools"] = []
            trace["runtime_tool_router"]["allowed_tools"] = []
            trace["runtime_tool_router"]["filtered_tool_plan"] = []
            trace["read_tool_executions"] = []
            trace["packetizer"]["outputs"] = []
            trace["manager_pass_2"]["provider_params"]["provider"] = None
            trace["manager_pass_2"]["provider_params"]["model"] = None
            trace["manager_pass_2"]["provider_params"]["request_id"] = None
            trace["manager_pass_2"]["item_results"] = []

    phase_b = invalid_phase_b_report_fixture(tmp_path, mutate)

    report = verify_phase_b_readiness(phase_b_report_path=phase_b, active_paths=[])
    failure_report = report["natural_probe_failure_report"]

    assert failure_report["failure_family_counts"]["manager_no_tool_request"] >= 1
    assert failure_report["failure_family_counts"]["blocking_boundary_ok"] == 1
    assert failure_report["failure_family_counts"]["manager_blocking_semantics_not_proven"] == 1
    blocking_case = failure_report["cases"][3]
    assert blocking_case["expected_tool_policy"]["estimate_tool_execution"] == "forbidden"
    assert blocking_case["expected_tool_policy"]["lookup_generic_food"] == "not_required"
    assert blocking_case["failure_family"] == "blocking_boundary_ok"
    assert blocking_case["manager_blocking_semantics"] == "not_proven"
    assert blocking_case["pass2_ran"] is False
    assert blocking_case["item_results_source"] == "none"


def test_natural_probe_missing_pass2_item_results_fails_loop_completion_not_selection(tmp_path: Path) -> None:
    def mutate(data: dict[str, object]) -> None:
        data["pass1_mode"] = "natural_tool_selection_probe"
        data["forced_tool_request_contract"] = False
        data["manager_tool_selection_claimed"] = True
        for trace in data["tool_loop_traces"]:
            trace["pass1_mode"] = "natural_tool_selection_probe"
            trace["forced_tool_request_contract"] = False
            trace["manager_tool_selection_claimed"] = True
        data["tool_loop_traces"][0]["manager_pass_2"]["item_results"] = []
        data["tool_loop_traces"][0]["runner_derived_item_results"] = False

    phase_b = invalid_phase_b_report_fixture(tmp_path, mutate)

    report = verify_phase_b_readiness(phase_b_report_path=phase_b, active_paths=[])

    assert report["natural_tool_selection_pass"] is True
    assert report["natural_tool_loop_completion_pass"] is False
    assert any(item["code"] == "manager_pass2_item_results_missing" for item in report["blockers"])


def test_natural_probe_runner_derived_item_results_fails_loop_completion(tmp_path: Path) -> None:
    def mutate(data: dict[str, object]) -> None:
        data["pass1_mode"] = "natural_tool_selection_probe"
        data["forced_tool_request_contract"] = False
        data["manager_tool_selection_claimed"] = True
        trace = data["tool_loop_traces"][0]
        trace["pass1_mode"] = "natural_tool_selection_probe"
        trace["forced_tool_request_contract"] = False
        trace["manager_tool_selection_claimed"] = True
        trace["runner_derived_item_results"] = True

    phase_b = invalid_phase_b_report_fixture(tmp_path, mutate)

    report = verify_phase_b_readiness(phase_b_report_path=phase_b, active_paths=[])

    assert report["natural_tool_loop_completion_pass"] is False
    assert any(item["code"] == "natural_probe_runner_derived_item_results" for item in report["blockers"])


def test_logged_estimable_case_without_tool_path_fails_quality_but_not_scaffold(tmp_path: Path) -> None:
    def mutate(data: dict[str, object]) -> None:
        trace = data["tool_loop_traces"][0]
        trace["manager_pass_1"]["requested_read_tools"] = []
        trace["runtime_tool_router"]["requested_read_tools"] = []
        trace["runtime_tool_router"]["manager_requested_tools"] = []
        trace["runtime_tool_router"]["allowed_tools"] = []
        trace["runtime_tool_router"]["filtered_tool_plan"] = []
        trace["read_tool_executions"] = []
        trace["packetizer"]["outputs"] = []

    phase_b = invalid_phase_b_report_fixture(tmp_path, mutate)

    report = verify_phase_b_readiness(phase_b_report_path=phase_b, active_paths=[])

    assert report["scaffold_pass"] is True
    assert report["quality_pass"] is False
    assert any(item["code"] == "expected_tool_request_coverage_missing" for item in report["blockers"])
    assert any(item["code"] == "expected_packetizer_output_coverage_missing" for item in report["blockers"])
    assert "tighten_manager_pass1_tool_request_contract" in report["recommended_next_steps_ordered"]


def test_pass2_provider_trace_null_values_fail_quality(tmp_path: Path) -> None:
    def mutate(data: dict[str, object]) -> None:
        params = data["tool_loop_traces"][0]["manager_pass_2"]["provider_params"]
        params["provider"] = None
        params["model"] = None
        params["request_id"] = None

    phase_b = invalid_phase_b_report_fixture(tmp_path, mutate)

    report = verify_phase_b_readiness(phase_b_report_path=phase_b, active_paths=[])

    assert report["quality_pass"] is False
    assert any(item["code"] == "pass2_provider_trace_missing" for item in report["blockers"])


def test_mutation_with_empty_item_results_fails_quality(tmp_path: Path) -> None:
    def mutate(data: dict[str, object]) -> None:
        data["tool_loop_traces"][0]["manager_pass_2"]["item_results"] = []
        data["tool_loop_traces"][0]["renderer"]["input"]["item_results"] = []

    phase_b = invalid_phase_b_report_fixture(tmp_path, mutate)

    report = verify_phase_b_readiness(phase_b_report_path=phase_b, active_paths=[])

    assert report["quality_pass"] is False
    assert any(item["code"] == "mutation_without_item_results" for item in report["blockers"])


def test_spec_exit_criteria_warns_accuracy_not_production_ready() -> None:
    spec = Path("docs/specs/WAVE_1_PHASE_B_MINIMAL_TOOL_LOOP_SPEC.md").read_text(encoding="utf-8-sig")

    assert "does not mean nutrition accuracy is production-ready" in spec
