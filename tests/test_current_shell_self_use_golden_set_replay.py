from __future__ import annotations

import json
from pathlib import Path

from scripts.build_current_shell_self_use_golden_set_replay import (
    build_golden_set_replay,
    write_golden_set_replay,
)


def _manifest() -> dict[str, object]:
    from app.composition.current_shell_golden_set_grader import load_golden_set_manifest

    return load_golden_set_manifest()


def _gs5_trace_case() -> dict[str, object]:
    return {
        "case_id": "GS5",
        "trace_id": "trace-gs5",
        "prompt_registry": {"manager_prompt_version": "v18"},
        "current_turn_context_packet": {"current_turn": "breakfast combo", "pending_question": None},
        "react_trace": {
            "manager_pass_1": {"decision_payload": {"workflow_effect": "ask_followup"}},
            "requested_tools": ["fooddb.lookup"],
            "executed_tools": ["fooddb.lookup"],
            "manager_pass_final": {"decision_payload": {"workflow_effect": "ask_followup"}},
            "guard_result": {"mutation_allowed": False},
            "total_latency_ms": 12000,
            "tool_call_count": 1,
        },
        "filtered_tool_plan": {"allowed_tools": ["fooddb.lookup"]},
        "compact_packets": [{"packet_id": "teppan-no-anchor", "posture": "ask_followup"}],
        "mutation_result": {"mutation_allowed": False},
        "renderer_input_basis": {"today_consumed_updates": False},
        "final_response_basis": {"basis": "composition_unknown"},
        "runtime": {
            "workflow_effect": "ask_followup",
            "mutation_allowed": False,
            "fallback_400_allowed": False,
            "pre_manager_estimability_shortcut_allowed": False,
            "pending_followup_saved": True,
            "assumed_slot_question_required": True,
        },
        "ui": {
            "today_consumed_updates": False,
            "pending_question_visible": True,
            "frontend_nutrition_math_allowed": False,
        },
        "response": {
            "visible_text": "這個套餐內容可能差很多，請補一下主餐、蛋、飲料或其他配菜，我再幫你估。",
            "zh_tw_primary": True,
            "internal_debug_words_present": False,
            "state_contradiction": False,
            "invented_nutrition_fact": False,
        },
        "latency": {"timeout_is_product_target": False, "llm_calls": 2, "tool_calls": 1},
        "dogfood_trace": {"feedback_links_to_trace": True},
        "generalization": {
            "exact_utterance_only_pass": False,
            "keyword_or_fixture_shortcut_used": False,
        },
    }


def _gsw1_trace_case() -> dict[str, object]:
    return {
        "case_id": "GSW1",
        "trace_id": "trace-gsw1",
        "prompt_registry": {"manager_prompt_version": "v18"},
        "current_turn_context_packet": {"current_turn": "exact item lookup", "pending_question": None},
        "react_trace": {
            "manager_pass_1": {"decision_payload": {"workflow_effect": "call_websearch"}},
            "requested_tools": ["websearch.lookup_candidate"],
            "executed_tools": ["websearch.lookup_candidate"],
            "manager_pass_final": {"decision_payload": {"workflow_effect": "answer_or_ask_followup_no_mutation"}},
            "guard_result": {"mutation_allowed": False},
            "total_latency_ms": 14000,
            "tool_call_count": 1,
        },
        "filtered_tool_plan": {"allowed_tools": ["websearch.lookup_candidate"]},
        "compact_packets": [{"packet_id": "web-candidate-1", "source_role": "candidate_only"}],
        "mutation_result": {"mutation_allowed": False},
        "renderer_input_basis": {"today_consumed_updates": False},
        "final_response_basis": {"basis": "websearch_candidate_only"},
        "runtime": {
            "workflow_effect": "answer_or_ask_followup_no_mutation",
            "websearch_tool_call_expected": True,
            "websearch_candidate_only": True,
            "websearch_snippet_as_truth_allowed": False,
            "runtime_mutation_allowed": False,
            "fooddb_truth_promotion_allowed": False,
            "pre_manager_websearch_routing_allowed": False,
            "websearch_candidate_to_commit_allowed": False,
        },
        "ui": {
            "today_consumed_updates": False,
            "frontend_nutrition_math_allowed": False,
            "candidate_source_label_visible": True,
        },
        "response": {
            "visible_text": "我找到候選來源，但目前還不能當成已核准的營養資料，所以先不記錄。",
            "zh_tw_primary": True,
            "internal_debug_words_present": False,
            "state_contradiction": False,
            "invented_nutrition_fact": False,
        },
        "latency": {"timeout_is_product_target": False, "llm_calls": 2, "tool_calls": 1},
        "dogfood_trace": {"feedback_links_to_trace": True},
        "generalization": {
            "exact_utterance_only_pass": False,
            "keyword_or_fixture_shortcut_used": False,
        },
    }


def _trace_artifact(*cases: dict[str, object]) -> dict[str, object]:
    return {
        "artifact_type": "current_shell_self_use_golden_set_trace_artifact",
        "claim_scope": "offline_runtime_trace_replay",
        "live_invoked_by_replay": False,
        "readiness_claimed": False,
        "private_self_use_approved": False,
        "cases": list(cases),
    }


def test_golden_set_replay_grades_present_runtime_trace_case_without_inferred_semantics() -> None:
    replay = build_golden_set_replay(manifest=_manifest(), trace_artifact=_trace_artifact(_gs5_trace_case()))

    gs5 = next(case for case in replay["cases"] if case["case_id"] == "GS5")
    assert replay["artifact_type"] == "current_shell_self_use_golden_set_replay"
    assert replay["live_invoked_by_replay"] is False
    assert replay["readiness_claimed"] is False
    assert replay["summary"]["core_case_count"] == 19
    assert replay["summary"]["websearch_extension_case_count"] == 4
    assert replay["summary"]["total_closeout_case_count"] == 23
    assert replay["summary"]["manifest_case_count"] == 23
    assert replay["summary"]["source_case_count"] == 1
    assert replay["summary"]["missing_case_count"] == 22
    assert replay["summary"]["failed_case_count"] == 22
    assert replay["summary"]["strict_golden_set_replay_passed"] is False
    assert replay["runner_inferred_semantics"] is False
    assert gs5["status"] == "pass"
    assert gs5["deterministic_grader_owns_semantics"] is False


def test_golden_set_replay_grades_websearch_extension_case() -> None:
    replay = build_golden_set_replay(manifest=_manifest(), trace_artifact=_trace_artifact(_gsw1_trace_case()))

    gsw1 = next(case for case in replay["cases"] if case["case_id"] == "GSW1")
    assert replay["summary"]["core_case_count"] == 19
    assert replay["summary"]["websearch_extension_case_count"] == 4
    assert replay["summary"]["total_closeout_case_count"] == 23
    assert replay["summary"]["manifest_case_count"] == 23
    assert gsw1["status"] == "pass"
    assert gsw1["deterministic_grader_owns_semantics"] is False


def test_golden_set_replay_blocks_raw_utterance_only_case() -> None:
    raw_only = {"case_id": "GS5", "raw_user_input": "早餐吃早餐店鐵板麵套餐", "trace_id": "trace-gs5"}

    replay = build_golden_set_replay(manifest=_manifest(), trace_artifact=_trace_artifact(raw_only))

    gs5 = next(case for case in replay["cases"] if case["case_id"] == "GS5")
    assert gs5["status"] == "blocked"
    assert "runtime.workflow_effect_expected:ask_followup_actual:None" in gs5["blockers"]
    assert "trace_layers.manager_pass_1_decision_missing" in gs5["blockers"]


def test_golden_set_replay_blocks_forbidden_source_flags() -> None:
    source = _trace_artifact(_gs5_trace_case())
    source["runner_inferred_semantics"] = True

    replay = build_golden_set_replay(manifest=_manifest(), trace_artifact=source)

    assert replay["input_integrity"]["passed"] is False
    assert "source.runner_inferred_semantics_not_allowed" in replay["input_integrity"]["blockers"]
    assert replay["summary"]["strict_golden_set_replay_passed"] is False


def test_golden_set_replay_blocks_websearch_fake_pass_source_flags() -> None:
    source = _trace_artifact(_gsw1_trace_case())
    source["pre_manager_websearch_routing_used"] = True
    source["websearch_candidate_promoted_to_truth"] = True
    source["visible_macro_from_candidate_only"] = True

    replay = build_golden_set_replay(manifest=_manifest(), trace_artifact=source)

    assert replay["input_integrity"]["passed"] is False
    assert "source.pre_manager_websearch_routing_used_not_allowed" in replay["input_integrity"]["blockers"]
    assert "source.websearch_candidate_promoted_to_truth_not_allowed" in replay["input_integrity"]["blockers"]
    assert "source.visible_macro_from_candidate_only_not_allowed" in replay["input_integrity"]["blockers"]
    assert replay["summary"]["strict_golden_set_replay_passed"] is False


def test_golden_set_replay_blocks_fixture_manager_case_from_passing() -> None:
    case = _gs5_trace_case()
    case["manager_provider"] = {
        "provider": "deterministic_self_use_manager_fixture",
        "live_llm_invoked": False,
    }

    replay = build_golden_set_replay(manifest=_manifest(), trace_artifact=_trace_artifact(case))

    gs5 = next(item for item in replay["cases"] if item["case_id"] == "GS5")
    assert gs5["status"] == "blocked"
    assert "fixture_decisions.action_not_allowed" in gs5["blockers"]
    assert replay["summary"]["strict_golden_set_replay_passed"] is False


def test_golden_set_replay_writer_creates_artifact(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.yaml"
    trace_path = tmp_path / "trace.json"
    output_path = tmp_path / "replay.json"
    manifest = _manifest()
    import yaml

    manifest_path.write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")
    trace_path.write_text(json.dumps(_trace_artifact(_gs5_trace_case()), ensure_ascii=False), encoding="utf-8")

    output = write_golden_set_replay(
        manifest_path=manifest_path,
        trace_artifact_path=trace_path,
        output_path=output_path,
    )

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert output == output_path
    assert payload["artifact_type"] == "current_shell_self_use_golden_set_replay"
    assert payload["summary"]["source_case_count"] == 1
