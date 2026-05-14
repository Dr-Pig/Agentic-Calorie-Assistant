from __future__ import annotations

import asyncio
import importlib
import json
from pathlib import Path
import subprocess
import sys


def _write_strict_offline_replay(path: Path) -> Path:
    path.write_text(
        json.dumps(
            {
                "artifact_type": "accurate_intake_mvp_offline_shadow_replay",
                "input_integrity": {"passed": True, "blockers": []},
                "summary": {
                    "sample_run_count": 1,
                    "strict_replay_ready": True,
                    "pass_after_retry_count": 0,
                    "timeout_count": 0,
                    "failed_stage_count": 0,
                    "model_diversity_status": "model_diversity_missing",
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return path


def test_accurate_intake_live_diagnostic_source_avoids_activation_shortcuts() -> None:
    runner_path = Path("scripts/run_accurate_intake_mvp_live_diagnostic.py")
    source = runner_path.read_text(encoding="utf-8")

    forbidden_markers = (
        "allow_search=True",
        "readiness_claimed=True",
        "product_readiness_claimed=True",
        "private_self_use_approved=True",
        "production_selected=True",
        "mutation_rollout_approved=True",
        "live_provider_used_as_truth=True",
        "runtime_web_activation_approved=True",
        "tavily_or_web_activated=True",
        "_looks_like_intake_request",
        "looks_like_correction",
        "looks_like_budget_query",
    )
    for marker in forbidden_markers:
        assert marker not in source


def test_accurate_intake_live_provider_profile_is_diagnostic_only() -> None:
    module = importlib.import_module("scripts.run_accurate_intake_mvp_live_diagnostic")

    profile = module.provider_profile(module.DEFAULT_ACCURATE_INTAKE_LIVE_DIAGNOSTIC_PROVIDER_PROFILE_ID)

    assert profile["provider_profile_id"] == "builderspace-grok-4-fast-accurate-intake-mvp-live-diagnostic"
    assert profile["model"] == "grok-4-fast"
    assert profile["provider_profile_role"] == "accurate_intake_mvp_live_diagnostic"
    assert profile["production_selected"] is False
    assert profile["not_production_selection"] is True
    assert profile["readiness_owner"] is False
    assert profile["transport_policy"]["primary"] == "synthetic_tool_transport"
    assert profile["transport_policy"]["fallback"] == "json_schema"
    assert "plain_json_object_without_schema_validation" in profile["transport_policy"]["forbidden_as_success"]
    assert isinstance(profile["schema_name"], str) and profile["schema_name"]
    assert isinstance(profile["schema_version"], str) and profile["schema_version"]


def test_scripted_provider_target_proposal_uses_manager_context_packet_v1_candidates() -> None:
    module = importlib.import_module("scripts.run_accurate_intake_mvp_live_diagnostic")
    provider = module.ScriptedAccurateIntakeLiveProvider()
    provider.begin_step({"target_canonical_name": "soup"})

    proposal = provider._target_proposal(  # noqa: SLF001
        user_payload={
            "resolved_state": {
                "prompt_payload_kind": "resolved_state_compact_summary",
                "full_state_omitted_from_prompt": True,
            },
            "manager_context_packet_v1": {
                "target_candidates": {
                    "for_correction_or_removal": [
                        {
                            "meal_thread_id": 77,
                            "meal_version_id": 88,
                            "meal_item_id": 501,
                            "canonical_name": "soup",
                            "read_only": True,
                            "mutation_authority": False,
                        }
                    ]
                }
            },
        }
    )

    assert proposal["meal_thread_id"] == 77
    assert proposal["meal_item_id"] == 501
    assert proposal["canonical_name"] == "soup"
    assert proposal["target_proposal_source"] == "manager_structured_tool_arguments"


def test_provider_invocation_summary_surfaces_prompt_cache_identity() -> None:
    module = importlib.import_module("scripts.run_accurate_intake_mvp_live_diagnostic")

    summary = module._provider_invocation_summary(  # noqa: SLF001 - script report-shape contract.
        [
            {
                "latency_ms": 10,
                "provider_trace": {
                    "usage": {"prompt_tokens": 100, "completion_tokens": 10, "prompt_tokens_details": {"cached_tokens": 0}},
                    "prompt_cache_request": {
                        "identity_version": "provider_prompt_cache_request.v1",
                        "provider_request_includes_prompt_cache_key": True,
                        "stable_prefix_sha256": "stable-a",
                        "dynamic_suffix_sha256": "dynamic-a",
                        "request_payload_utf8_bytes": 1200,
                        "stable_prefix_utf8_bytes": 800,
                        "dynamic_suffix_utf8_bytes": 400,
                    },
                },
            },
            {
                "latency_ms": 20,
                "provider_trace": {
                    "usage": {"prompt_tokens": 110, "completion_tokens": 12, "prompt_tokens_details": {"cached_tokens": 70}},
                    "prompt_cache_request": {
                        "identity_version": "provider_prompt_cache_request.v1",
                        "provider_request_includes_prompt_cache_key": True,
                        "stable_prefix_sha256": "stable-a",
                        "dynamic_suffix_sha256": "dynamic-b",
                        "request_payload_utf8_bytes": 1300,
                        "stable_prefix_utf8_bytes": 800,
                        "dynamic_suffix_utf8_bytes": 500,
                    },
                },
            },
        ]
    )

    assert summary["cached_tokens"] == 70
    assert summary["cache_reporting_call_count"] == 2
    assert summary["cached_tokens_known"] is True
    assert summary["cache_miss_claim_allowed"] is False
    assert summary["prompt_cache"] == {
        "provider_usage_is_cache_truth": True,
        "identity_count": 2,
        "missing_identity_count": 0,
        "prompt_cache_key_count": 2,
        "stable_prefix_unique_count": 1,
        "dynamic_suffix_unique_count": 2,
        "repeated_stable_prefix_observed": True,
        "request_payload_utf8_bytes": 2500,
        "stable_prefix_utf8_bytes": 1600,
        "dynamic_suffix_utf8_bytes": 900,
    }


def test_provider_invocation_summary_counts_cache_read_and_creation_usage_fields() -> None:
    module = importlib.import_module("scripts.run_accurate_intake_mvp_live_diagnostic")

    summary = module._provider_invocation_summary(  # noqa: SLF001 - script report-shape contract.
        [
            {
                "latency_ms": 10,
                "provider_trace": {
                    "usage": {
                        "input_tokens": 64,
                        "output_tokens": 12,
                        "cache_creation_input_tokens": 1024,
                    },
                },
            },
            {
                "latency_ms": 20,
                "provider_trace": {
                    "usage": {
                        "input_tokens": 50,
                        "output_tokens": 8,
                        "cache_read_input_tokens": 900,
                        "cache_creation_input_tokens": 100,
                    },
                },
            },
        ]
    )

    assert summary["prompt_tokens"] == 2138
    assert summary["completion_tokens"] == 20
    assert summary["cached_tokens"] == 900
    assert summary["cache_reporting_call_count"] == 2
    assert summary["cache_hit_call_count"] == 1
    assert summary["cached_tokens_known"] is True
    assert summary["cache_miss_claim_allowed"] is False
    assert summary["cached_tokens_unknown"] is False


def test_accurate_intake_live_diagnostic_artifact_contract_with_fake_provider(tmp_path: Path) -> None:
    module = importlib.import_module("scripts.run_accurate_intake_mvp_live_diagnostic")
    output_path = tmp_path / "accurate_intake_mvp_live_diagnostic.json"
    db_path = tmp_path / "accurate_intake_mvp_live.sqlite3"

    report = module.run_diagnostic(
        output_path=output_path,
        db_path=db_path,
        local_date="2026-05-02",
        provider_override=module.ScriptedAccurateIntakeLiveProvider(),
        provider_mode="fake_provider_contract_test",
        live_invoked=False,
        offline_replay_artifact_path=_write_strict_offline_replay(tmp_path / "offline_replay.json"),
    )

    assert output_path.exists()
    assert json.loads(output_path.read_text(encoding="utf-8")) == report
    assert report["artifact_type"] == "accurate_intake_mvp_live_diagnostic"
    assert report["claim_scope"] == "live_diagnostic"
    assert report["provider_mode"] == "fake_provider_contract_test"
    assert report["live_invoked"] is False
    assert report["live_llm_invoked"] is False
    assert report["readiness_claimed"] is False
    assert report["product_readiness_claimed"] is False
    assert report["private_self_use_approved"] is False
    assert report["production_selected"] is False
    assert report["mutation_rollout_approved"] is False
    assert report["live_provider_used_as_truth"] is False
    assert report["runtime_web_activation_approved"] is False
    assert report["tavily_or_web_activated"] is False
    assert report["web_tavily_invoked"] is False
    assert report["production_db_used"] is False
    assert report["user_facing_rollout"] is False
    assert report["provider_profile_id"] == module.DEFAULT_ACCURATE_INTAKE_LIVE_DIAGNOSTIC_PROVIDER_PROFILE_ID
    assert report["provider_profile_model"] == "grok-4-fast"
    assert report["timeout_policy"] == {
        "provider_request_timeout_ms": 180_000,
        "case_timeout_ms": 195_000,
        "case_timeout_override_supplied": False,
        "case_timeout_grace_ms": 15_000,
        "provider_request_retry_count": 0,
        "provider_request_retry_backoff_ms": 250,
        "provider_request_retry_jitter_ms": 100,
        "strict_pass_requires_first_attempt": True,
        "timeout_values_are_failure_boundaries_not_product_latency_targets": True,
    }
    assert report["active_entrypoint_verified"] is True
    assert report["runner_inferred_semantics"] is False
    assert report["raw_text_routing_used"] is False
    assert report["readiness_claim"]["claim_scope"] == "unit_contract"
    assert [stage["stage_id"] for stage in report["stages"]] == [
        "provider_health_smoke",
        "schema_contract_probe",
        "fake_provider_active_runtime_gate",
        "single_case_live_probe",
        "full_suite_live_diagnostic",
    ]
    assert all(stage["status"] == "pass" for stage in report["stages"])
    for stage in report["stages"]:
        assert stage["provider_profile_id"] == report["provider_profile_id"]
        assert stage["model"] == "grok-4-fast"
        assert stage["transport_mode"] == "synthetic_tool_transport"
        assert isinstance(stage["attempt_count"], int)
        assert isinstance(stage["latency_ms"], int)
        assert isinstance(stage["timeout_budget_ms"], int)
        assert "failure_layer" in stage
        assert "failure_family" in stage
        assert stage["retry_policy_applied"] in {False, True}

    case_ids = [case["case_id"] for case in report["cases"]]
    assert case_ids == [
        "chinese_chicken_rice_correction_removal_debug",
        "bubble_milk_tea_refinement",
        "luwei_bare_to_listed_basket",
        "today_consumed_query_only",
        "no_plan_consumed_without_budget_target",
    ]
    assert all(case["provider_profile_id"] == report["provider_profile_id"] for case in report["cases"])
    assert all(case["provider_profile_model"] == "grok-4-fast" for case in report["cases"])
    assert all(case["case_contract_status"] in {"strict_pass", "repaired_pass", "fail", "timeout"} for case in report["cases"])
    assert all(case["runner_inferred_semantics"] is False for case in report["cases"])
    assert all(case["raw_text_routing_used"] is False for case in report["cases"])
    for case in report["cases"]:
        for turn in case["turns"]:
            assert "coach_message" in turn
            assert "show_macro" in turn
            assert "macro_guard_reason" in turn
            assert turn["prompt_footprint_summary"]["measurement"] == "json_utf8_bytes_trace_only"
            assert turn["prompt_footprint_summary"]["provider_usage_is_token_truth"] is True
            prompt_backed_round_count = sum(
                1 for round_item in turn["manager_rounds"] if round_item.get("prompt_layer_contract")
            )
            assert turn["prompt_footprint_summary"]["manager_round_count"] == prompt_backed_round_count
            if prompt_backed_round_count:
                assert turn["prompt_footprint_summary"]["system_prompt_utf8_bytes_sent"] > 0
                assert turn["prompt_footprint_summary"]["dynamic_payload_utf8_bytes_sent"] > 0
                assert turn["prompt_footprint_summary"]["largest_dynamic_section_id"]
                assert turn["prompt_footprint_summary"]["largest_dynamic_key"]["key"]
                assert turn["prompt_footprint_summary"]["dynamic_key_utf8_bytes"]
            else:
                assert turn["prompt_footprint_summary"]["system_prompt_utf8_bytes_sent"] == 0
                assert turn["prompt_footprint_summary"]["dynamic_payload_utf8_bytes_sent"] == 0
                assert turn["prompt_footprint_summary"]["largest_dynamic_section_id"] is None
                assert turn["prompt_footprint_summary"]["largest_dynamic_key"] is None
                assert turn["prompt_footprint_summary"]["dynamic_key_utf8_bytes"] == {}
            assert isinstance(turn["latency_ms"], int)
            assert isinstance(turn["non_provider_latency_ms"], int)
            assert turn["latency_attribution"] == {
                "turn_total_ms": turn["latency_ms"],
                "provider_invocation_ms": turn["provider_invocation_summary"]["provider_invocation_latency_ms"],
                "non_provider_runtime_ms": turn["non_provider_latency_ms"],
            }
            assert turn["provider_invocation_summary"]["provider_invocation_count"] >= 1
            assert isinstance(turn["provider_invocation_summary"]["provider_invocation_latency_ms"], int)
            assert isinstance(turn["provider_invocation_summary"]["provider_wrapper_overhead_ms"], int)
            assert isinstance(turn["provider_invocation_summary"]["transport_attempt_count"], int)
            assert isinstance(turn["provider_invocation_summary"]["transport_attempt_latency_ms"], int)
            assert isinstance(turn["provider_invocation_summary"]["slowest_transport_attempt_ms"], int)
            prompt_cache = turn["provider_invocation_summary"]["prompt_cache"]
            assert prompt_cache["provider_usage_is_cache_truth"] is True
            assert isinstance(prompt_cache["identity_count"], int)
            assert isinstance(prompt_cache["missing_identity_count"], int)
            assert isinstance(prompt_cache["prompt_cache_key_count"], int)
            assert isinstance(prompt_cache["stable_prefix_unique_count"], int)
            assert isinstance(prompt_cache["dynamic_suffix_unique_count"], int)
            assert isinstance(prompt_cache["repeated_stable_prefix_observed"], bool)
            assert isinstance(prompt_cache["request_payload_utf8_bytes"], int)
            assert isinstance(prompt_cache["stable_prefix_utf8_bytes"], int)
            assert isinstance(prompt_cache["dynamic_suffix_utf8_bytes"], int)
            assert isinstance(turn["runtime_stage_timings"], list)
            assert all("stage" in item and "duration_ms" in item for item in turn["runtime_stage_timings"])
            assert turn["runtime_stage_timing_summary"]["recorded_stage_count"] == len(turn["runtime_stage_timings"])
            assert turn["runtime_stage_timing_summary"]["recorded_stage_total_ms"] == sum(
                int(item["duration_ms"]) for item in turn["runtime_stage_timings"]
            )
            assert isinstance(turn["runtime_stage_timing_summary"]["slowest_stage_name"], str)
            assert isinstance(turn["runtime_stage_timing_summary"]["slowest_stage_ms"], int)
            if prompt_backed_round_count:
                assert turn["runtime_stage_timings"]
        assert case["provider_invocation_count"] >= len(case["turns"])
        assert case["prompt_footprint_summary"]["measurement"] == "json_utf8_bytes_trace_only"
        assert case["prompt_footprint_summary"]["manager_round_count"] == sum(
            turn["prompt_footprint_summary"]["manager_round_count"]
            for turn in case["turns"]
        )
        assert case["prompt_footprint_summary"]["dynamic_payload_utf8_bytes_sent"] == sum(
            turn["prompt_footprint_summary"]["dynamic_payload_utf8_bytes_sent"]
            for turn in case["turns"]
        )
        if case["prompt_footprint_summary"]["manager_round_count"] > 0:
            assert case["prompt_footprint_summary"]["dynamic_key_utf8_bytes"]
        else:
            assert case["prompt_footprint_summary"]["dynamic_key_utf8_bytes"] == {}
        assert isinstance(case["provider_invocation_latency_ms"], int)
        assert isinstance(case["latency_ms"], int)
        assert isinstance(case["non_provider_latency_ms"], int)
        assert case["latency_attribution"] == {
            "case_total_ms": case["latency_ms"],
            "provider_invocation_ms": case["provider_invocation_latency_ms"],
            "non_provider_runtime_ms": case["non_provider_latency_ms"],
        }
        for invocation in case["provider_invocations"]:
            assert invocation["span_kind"] == "provider_request"
            assert invocation["diagnostic_stage_id"] in {
                "fake_provider_active_runtime_gate",
                "single_case_live_probe",
                "full_suite_live_diagnostic",
            }
            assert invocation["diagnostic_case_id"] == case["case_id"]
            assert isinstance(invocation["diagnostic_turn"], int)
            assert invocation["diagnostic_turn_kind"]
            assert "manager_round_index" in invocation
            assert invocation["manager_loop_scope"] in {"turn_entry_or_read_only", "intake_execution"}
    case_invocations = [item for item in report["provider_invocations"] if item.get("diagnostic_case_id")]
    assert case_invocations
    assert all(item["span_kind"] == "provider_request" for item in case_invocations)
    assert all(item.get("diagnostic_turn") for item in case_invocations)
    assert {item["manager_loop_scope"] for item in case_invocations} == {"turn_entry_or_read_only", "intake_execution"}
    assert report["summary"]["case_count"] == len(report["cases"])
    assert report["summary"]["strict_pass_count"] + report["summary"]["repaired_pass_count"] + report["summary"][
        "contract_fail_count"
    ] + report["summary"]["timeout_count"] == len(report["cases"])
    assert report["summary"]["prompt_footprint_summary"]["measurement"] == "json_utf8_bytes_trace_only"
    assert report["summary"]["prompt_footprint_summary"]["manager_round_count"] == sum(
        case["prompt_footprint_summary"]["manager_round_count"]
        for case in report["cases"]
    )
    assert report["summary"]["prompt_footprint_summary"]["dynamic_key_utf8_bytes"]
    assert report["summary"]["prompt_footprint_summary"]["largest_dynamic_key"]["key"]


def test_accurate_intake_live_diagnostic_timeout_defaults_preserve_latency_observation_window() -> None:
    module = importlib.import_module("scripts.run_accurate_intake_mvp_live_diagnostic")

    assert module.DEFAULT_PROVIDER_REQUEST_TIMEOUT_MS == 180_000
    assert module.DEFAULT_PROVIDER_REQUEST_TIMEOUT_MS > 30_000
    assert module.DEFAULT_PROVIDER_REQUEST_RETRY_COUNT == 0


def test_accurate_intake_live_cli_blocks_implicit_all_stage(tmp_path: Path) -> None:
    output_path = tmp_path / "should_not_be_written.json"

    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_accurate_intake_mvp_live_diagnostic.py",
            "--output",
            str(output_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 2
    assert "stage all is disabled for live CLI diagnostics" in result.stderr
    assert not output_path.exists()


def test_accurate_intake_live_full_suite_is_blocked_without_offline_replay(tmp_path: Path) -> None:
    module = importlib.import_module("scripts.run_accurate_intake_mvp_live_diagnostic")

    report = module.run_diagnostic(
        output_path=tmp_path / "accurate_intake_mvp_live_diagnostic.json",
        db_path=tmp_path / "accurate_intake_mvp_live.sqlite3",
        provider_override=module.ScriptedAccurateIntakeLiveProvider(),
        provider_mode="fake_provider_contract_test",
        live_invoked=False,
        stage="full_suite_live_diagnostic",
        offline_replay_artifact_path=tmp_path / "missing_offline_replay.json",
    )

    assert report["cases"] == []
    assert report["failure_family"] == "offline_replay_required"
    assert len(report["stages"]) == 1
    stage = report["stages"][0]
    assert stage["stage_id"] == "full_suite_live_diagnostic"
    assert stage["status"] == "blocked"
    assert stage["provider_profile_id"] == module.DEFAULT_ACCURATE_INTAKE_LIVE_DIAGNOSTIC_PROVIDER_PROFILE_ID
    assert stage["model"] == "grok-4-fast"
    assert stage["failure_layer"] == "diagnostic_ordering"
    assert stage["failure_family"] == "offline_replay_required"
    assert stage["result_kind"] == "blocked"
    assert stage["summary"]["offline_replay_gate"]["allowed"] is False
    assert stage["summary"]["offline_replay_gate"]["failure_family"] == "offline_replay_required"


def test_accurate_intake_live_full_suite_can_run_after_strict_offline_replay(tmp_path: Path) -> None:
    module = importlib.import_module("scripts.run_accurate_intake_mvp_live_diagnostic")

    report = module.run_diagnostic(
        output_path=tmp_path / "accurate_intake_mvp_live_diagnostic.json",
        db_path=tmp_path / "accurate_intake_mvp_live.sqlite3",
        provider_override=module.ScriptedAccurateIntakeLiveProvider(),
        provider_mode="fake_provider_contract_test",
        live_invoked=False,
        stage="full_suite_live_diagnostic",
        offline_replay_artifact_path=_write_strict_offline_replay(tmp_path / "offline_replay.json"),
    )

    assert report["failure_family"] is None
    assert report["stages"][0]["stage_id"] == "full_suite_live_diagnostic"
    assert report["stages"][0]["status"] == "pass"
    assert report["stages"][0]["summary"]["offline_replay_gate"]["allowed"] is True
    assert [case["case_id"] for case in report["cases"]] == [
        "chinese_chicken_rice_correction_removal_debug",
        "bubble_milk_tea_refinement",
        "luwei_bare_to_listed_basket",
        "today_consumed_query_only",
        "no_plan_consumed_without_budget_target",
    ]
    for case in report["cases"]:
        grade = case["trace_expectation_grade"]
        assert grade["expectation_id"] == f"{case['case_id']}.trace.v1"
        assert grade["required_status"] == "pass"


def test_accurate_intake_live_seeded_explicit_removal_single_turn_probe(tmp_path: Path) -> None:
    module = importlib.import_module("scripts.run_accurate_intake_mvp_live_diagnostic")

    report = module.run_diagnostic(
        output_path=tmp_path / "accurate_intake_mvp_live_diagnostic.json",
        db_path=tmp_path / "accurate_intake_mvp_live.sqlite3",
        provider_override=module.ScriptedAccurateIntakeLiveProvider(),
        provider_mode="fake_provider_contract_test",
        live_invoked=False,
        stage="single_case_live_probe",
        case_id="explicit_item_removal_seeded",
    )

    assert report["stages"][-1]["stage_id"] == "single_case_live_probe"
    assert report["stages"][-1]["case_ids"] == ["explicit_item_removal_seeded"]
    assert report["stages"][-1]["status"] == "pass"
    assert report["cases"][0]["case_id"] == "explicit_item_removal_seeded"
    assert report["cases"][0]["case_contract_status"] == "strict_pass"
    grade = report["cases"][0]["trace_expectation_grade"]
    assert grade["expectation_id"] == "explicit_item_removal_seeded.trace.v1"
    assert grade["required_status"] == "pass"
    assert {check["check_id"]: check["status"] for check in grade["checks"]} == {
        "entry_scope_not_repeated": "pass",
        "call_topology_matches_expected": "pass",
        "intake_execution_scope_present": "pass",
        "provider_invocation_count_at_most_2": "pass",
        "resolve_target_used": "pass",
        "estimate_nutrition_not_used_for_removal": "pass",
        "correction_final_present": "pass",
    }
    scopes = [item["manager_loop_scope"] for item in report["cases"][0]["provider_invocations"]]
    assert scopes == ["turn_entry_or_read_only", "intake_execution"]
    assert report["cases"][0]["seeded_state"]["seed_kind"] == "canonical_two_item_meal"
    assert report["cases"][0]["runner_inferred_semantics"] is False
    assert report["cases"][0]["raw_text_routing_used"] is False
    assert report["cases"][0]["debug_surface"]["model"]["correction_history"][-1]["removed_item_names"] == ["soup"]
    tool_names = [
        call["name"]
        for turn in report["cases"][0]["turns"]
        for round_item in turn["manager_rounds"]
        for call in round_item["decision"].get("tool_calls", [])
    ]
    assert "resolve_correction_target" in tool_names
    assert "estimate_nutrition" not in tool_names


def test_accurate_intake_live_trace_expectation_catches_entry_loop_regression() -> None:
    from app.composition.accurate_intake_live_trace_expectations import grade_live_trace_expectations

    case = {
        "case_id": "explicit_item_removal_seeded",
        "provider_invocations": [
            {"manager_loop_scope": "turn_entry_or_read_only"},
            {"manager_loop_scope": "turn_entry_or_read_only"},
            {"manager_loop_scope": "turn_entry_or_read_only"},
            {"manager_loop_scope": "intake_execution"},
            {"manager_loop_scope": "intake_execution"},
        ],
        "turns": [
            {
                "manager_rounds": [
                    {
                        "decision": {
                            "tool_calls": [{"name": "resolve_correction_target"}],
                            "final_action": "correction_applied",
                        }
                    }
                ]
            }
        ],
    }

    grade = grade_live_trace_expectations(case)

    assert grade["required_status"] == "fail"
    checks = {check["check_id"]: check["status"] for check in grade["checks"]}
    assert checks["entry_scope_not_repeated"] == "fail"
    assert checks["provider_invocation_count_at_most_2"] == "fail"


def test_accurate_intake_live_trace_expectation_allows_exact_item_tool_pass_and_synthesis() -> None:
    from app.composition.accurate_intake_live_trace_expectations import grade_live_trace_expectations

    case = {
        "case_id": "exact_item_official_label",
        "provider_invocations": [
            {"diagnostic_turn": 1, "manager_loop_scope": "turn_entry_or_read_only"},
            {"diagnostic_turn": 1, "manager_loop_scope": "intake_execution"},
            {"diagnostic_turn": 1, "manager_loop_scope": "intake_execution"},
        ],
        "turns": [
            {
                "turn": 1,
                "manager_final_action": "commit",
                "manager_rounds": [
                    {"decision": {"tool_calls": [{"name": "estimate_nutrition"}]}},
                ],
                "state_delta": {"canonical_commit": True},
            }
        ],
    }

    grade = grade_live_trace_expectations(case)

    checks = {check["check_id"]: check for check in grade["checks"]}
    assert checks["call_topology_matches_expected"]["status"] == "pass"


def test_accurate_intake_live_trace_expectation_catches_more_than_one_exact_item_synthesis_call() -> None:
    from app.composition.accurate_intake_live_trace_expectations import grade_live_trace_expectations

    case = {
        "case_id": "exact_item_official_label",
        "provider_invocations": [
            {"diagnostic_turn": 1, "manager_loop_scope": "turn_entry_or_read_only"},
            {"diagnostic_turn": 1, "manager_loop_scope": "intake_execution"},
            {"diagnostic_turn": 1, "manager_loop_scope": "intake_execution"},
            {"diagnostic_turn": 1, "manager_loop_scope": "intake_execution"},
        ],
        "turns": [
            {
                "turn": 1,
                "manager_final_action": "commit",
                "manager_rounds": [
                    {"decision": {"tool_calls": [{"name": "estimate_nutrition"}]}},
                ],
                "state_delta": {"canonical_commit": True},
            }
        ],
    }

    grade = grade_live_trace_expectations(case)

    assert grade["required_status"] == "fail"
    checks = {check["check_id"]: check for check in grade["checks"]}
    assert checks["call_topology_matches_expected"]["status"] == "fail"
    assert checks["call_topology_matches_expected"]["observed"] == {
        "expected_by_turn": {1: ["turn_entry_or_read_only", "intake_execution", "intake_execution"]},
        "observed_by_turn": {1: ["turn_entry_or_read_only", "intake_execution", "intake_execution", "intake_execution"]},
        "unexpected_turns": [],
        "accepted_alternates": {1: [["turn_entry_or_read_only", "intake_execution"]]},
    }


def test_accurate_intake_live_trace_expectation_allows_listed_basket_tool_pass_and_synthesis() -> None:
    from app.composition.accurate_intake_live_trace_expectations import grade_live_trace_expectations

    case = {
        "case_id": "luwei_bare_to_listed_basket",
        "provider_invocations": [
            {"diagnostic_turn": 1, "manager_loop_scope": "turn_entry_or_read_only"},
            {"diagnostic_turn": 1, "manager_loop_scope": "intake_execution"},
            {"diagnostic_turn": 2, "manager_loop_scope": "turn_entry_or_read_only"},
            {"diagnostic_turn": 2, "manager_loop_scope": "intake_execution"},
            {"diagnostic_turn": 2, "manager_loop_scope": "intake_execution"},
        ],
        "turns": [
            {
                "turn": 1,
                "manager_final_action": "ask_followup",
                "state_delta": {"draft_saved": True, "canonical_commit": False},
                "manager_rounds": [{"decision": {"tool_calls": [], "final_action": "ask_followup"}}],
            },
            {
                "turn": 2,
                "manager_final_action": "commit",
                "state_delta": {"canonical_commit": True},
                "manager_rounds": [
                    {"decision": {"tool_calls": [{"name": "estimate_nutrition"}], "final_action": "commit"}},
                    {"decision": {"tool_calls": [], "final_action": "commit"}},
                ],
            },
        ],
    }

    grade = grade_live_trace_expectations(case)

    checks = {check["check_id"]: check for check in grade["checks"]}
    assert checks["call_topology_matches_expected"]["status"] == "pass"


def test_accurate_intake_live_trace_expectation_allows_bubble_tool_pass_and_synthesis() -> None:
    from app.composition.accurate_intake_live_trace_expectations import grade_live_trace_expectations

    case = {
        "case_id": "bubble_milk_tea_refinement",
        "provider_invocations": [
            {"diagnostic_turn": 1, "manager_loop_scope": "turn_entry_or_read_only"},
            {"diagnostic_turn": 1, "manager_loop_scope": "intake_execution"},
            {"diagnostic_turn": 2, "manager_loop_scope": "turn_entry_or_read_only"},
            {"diagnostic_turn": 2, "manager_loop_scope": "intake_execution"},
        ],
        "turns": [
            {
                "turn": 1,
                "manager_final_action": "commit",
                "state_delta": {"canonical_commit": True, "old_version_superseded": False},
                "manager_rounds": [
                    {"decision": {"tool_calls": [{"name": "estimate_nutrition"}], "final_action": "commit"}},
                    {"decision": {"tool_calls": [], "final_action": "commit"}},
                ],
            },
            {
                "turn": 2,
                "manager_final_action": "correction_applied",
                "state_delta": {"old_version_superseded": True},
                "manager_rounds": [
                    {"decision": {"tool_calls": [{"name": "estimate_nutrition"}], "final_action": "commit"}},
                    {"decision": {"tool_calls": [], "final_action": "correction_applied"}},
                ],
            },
        ],
        "debug_surface": {"model": {"same_truth": {"status": "pass"}}},
    }

    grade = grade_live_trace_expectations(case)

    checks = {check["check_id"]: check for check in grade["checks"]}
    assert checks["call_topology_matches_expected"]["status"] == "pass"


def test_accurate_intake_live_trace_expectation_rejects_extra_bubble_execution_round_after_entry_handoff() -> None:
    from app.composition.accurate_intake_live_trace_expectations import grade_live_trace_expectations

    case = {
        "case_id": "bubble_milk_tea_refinement",
        "provider_invocations": [
            {"diagnostic_turn": 1, "manager_loop_scope": "turn_entry_or_read_only"},
            {"diagnostic_turn": 1, "manager_loop_scope": "intake_execution"},
            {"diagnostic_turn": 1, "manager_loop_scope": "intake_execution"},
            {"diagnostic_turn": 2, "manager_loop_scope": "turn_entry_or_read_only"},
            {"diagnostic_turn": 2, "manager_loop_scope": "intake_execution"},
            {"diagnostic_turn": 2, "manager_loop_scope": "intake_execution"},
        ],
        "turns": [
            {"turn": 1, "manager_final_action": "commit", "state_delta": {"canonical_commit": True}},
            {
                "turn": 2,
                "manager_final_action": "commit",
                "state_delta": {"canonical_commit": True, "old_version_superseded": True},
            },
        ],
        "debug_surface": {"model": {"same_truth": {"status": "pass"}}},
    }

    grade = grade_live_trace_expectations(case)

    assert grade["required_status"] == "fail"
    checks = {check["check_id"]: check for check in grade["checks"]}
    assert checks["call_topology_matches_expected"]["status"] == "fail"


def test_accurate_intake_live_trace_expectation_allows_teppan_explain_then_refine() -> None:
    from app.composition.accurate_intake_live_trace_expectations import grade_live_trace_expectations

    case = {
        "case_id": "teppan_breakfast_explain_refine_dogfood",
        "provider_invocations": [
            {"diagnostic_turn": 1, "manager_loop_scope": "turn_entry_or_read_only"},
            {"diagnostic_turn": 1, "manager_loop_scope": "intake_execution"},
            {"diagnostic_turn": 2, "manager_loop_scope": "turn_entry_or_read_only"},
            {"diagnostic_turn": 3, "manager_loop_scope": "turn_entry_or_read_only"},
            {"diagnostic_turn": 3, "manager_loop_scope": "intake_execution"},
        ],
        "turns": [
            {
                "turn": 1,
                "manager_final_action": "commit",
                "workflow_effect": "commit",
                "state_delta": {
                    "canonical_commit": True,
                    "ledger_updated": True,
                    "new_meal_version_created": True,
                    "old_version_superseded": False,
                },
                "manager_rounds": [
                    {"decision": {"tool_calls": [{"name": "estimate_nutrition"}], "final_action": "commit"}},
                    {"decision": {"tool_calls": [], "final_action": "commit"}},
                ],
            },
            {
                "turn": 2,
                "manager_final_action": "answer_only",
                "workflow_effect": "answer_only",
                "state_delta": {
                    "canonical_commit": False,
                    "ledger_updated": False,
                    "new_meal_version_created": False,
                    "old_version_superseded": False,
                },
                "answer_basis": {
                    "meal_thread_id": "meal-1",
                    "references_active_meal": True,
                    "assumption_or_composition_explained": True,
                },
                "manager_rounds": [{"decision": {"tool_calls": [], "final_action": "answer_only"}}],
            },
            {
                "turn": 3,
                "manager_final_action": "correction_applied",
                "workflow_effect": "commit",
                "state_delta": {
                    "canonical_commit": True,
                    "ledger_updated": True,
                    "new_meal_version_created": True,
                    "old_version_superseded": True,
                },
                "estimation_summary": {
                    "component_names": ["teppan noodles", "pork slice", "fried egg"],
                    "used_default_fallback_400_macro": False,
                },
                "manager_rounds": [
                    {"decision": {"tool_calls": [{"name": "estimate_nutrition"}], "final_action": "commit"}},
                    {"decision": {"tool_calls": [], "final_action": "correction_applied"}},
                ],
            },
        ],
        "debug_surface": {"model": {"same_truth": {"status": "pass"}}},
    }

    grade = grade_live_trace_expectations(case)

    assert grade["expectation_id"] == "teppan_breakfast_explain_refine_dogfood.trace.v1"
    assert grade["required_status"] == "pass"
    assert {check["check_id"]: check["status"] for check in grade["checks"]} == {
        "three_turn_explain_refine_path": "pass",
        "call_topology_matches_expected": "pass",
        "turn1_estimate_and_commit": "pass",
        "turn2_answer_only_workflow": "pass",
        "turn2_no_tools": "pass",
        "turn2_no_mutation": "pass",
        "turn2_uses_active_meal_basis": "pass",
        "turn3_refines_existing_meal": "pass",
        "turn3_component_basis_present": "pass",
        "same_truth_pass": "pass",
    }


def test_accurate_intake_live_trace_expectation_catches_teppan_query_logged_as_meal() -> None:
    from app.composition.accurate_intake_live_trace_expectations import grade_live_trace_expectations

    case = {
        "case_id": "teppan_breakfast_explain_refine_dogfood",
        "provider_invocations": [
            {"diagnostic_turn": 1, "manager_loop_scope": "turn_entry_or_read_only"},
            {"diagnostic_turn": 1, "manager_loop_scope": "intake_execution"},
            {"diagnostic_turn": 2, "manager_loop_scope": "turn_entry_or_read_only"},
            {"diagnostic_turn": 2, "manager_loop_scope": "intake_execution"},
            {"diagnostic_turn": 3, "manager_loop_scope": "turn_entry_or_read_only"},
            {"diagnostic_turn": 3, "manager_loop_scope": "intake_execution"},
        ],
        "turns": [
            {
                "turn": 1,
                "manager_final_action": "commit",
                "workflow_effect": "commit",
                "state_delta": {
                    "canonical_commit": True,
                    "ledger_updated": True,
                    "new_meal_version_created": True,
                    "old_version_superseded": False,
                },
                "manager_rounds": [{"decision": {"tool_calls": [{"name": "estimate_nutrition"}]}}],
            },
            {
                "turn": 2,
                "manager_final_action": "commit",
                "workflow_effect": "commit",
                "state_delta": {
                    "canonical_commit": True,
                    "ledger_updated": True,
                    "new_meal_version_created": True,
                    "old_version_superseded": True,
                },
                "answer_basis": {},
                "manager_rounds": [{"decision": {"tool_calls": [{"name": "estimate_nutrition"}]}}],
            },
            {
                "turn": 3,
                "manager_final_action": "correction_applied",
                "workflow_effect": "commit",
                "state_delta": {
                    "canonical_commit": True,
                    "ledger_updated": True,
                    "new_meal_version_created": True,
                    "old_version_superseded": True,
                },
                "estimation_summary": {
                    "component_names": [],
                    "used_default_fallback_400_macro": True,
                },
                "manager_rounds": [{"decision": {"tool_calls": [{"name": "estimate_nutrition"}]}}],
            },
        ],
        "debug_surface": {"model": {"same_truth": {"status": "pass"}}},
    }

    grade = grade_live_trace_expectations(case)

    assert grade["required_status"] == "fail"
    checks = {check["check_id"]: check["status"] for check in grade["checks"]}
    assert checks["call_topology_matches_expected"] == "fail"
    assert checks["turn2_answer_only_workflow"] == "fail"
    assert checks["turn2_no_tools"] == "fail"
    assert checks["turn2_no_mutation"] == "fail"
    assert checks["turn2_uses_active_meal_basis"] == "fail"
    assert checks["turn3_component_basis_present"] == "fail"


def test_accurate_intake_live_trace_expectation_marks_entry_tool_call_as_ideal_target_gap() -> None:
    from app.composition.accurate_intake_live_trace_expectations import grade_live_trace_expectations

    case = {
        "case_id": "explicit_item_removal_seeded",
        "provider_invocations": [
            {
                "manager_loop_scope": "turn_entry_or_read_only",
                "provider_trace": {
                    "parsed_object": {
                        "manager_action": "call_tools",
                        "tool_calls": [{"name": "resolve_correction_target"}],
                    }
                },
            },
            {"manager_loop_scope": "intake_execution"},
            {"manager_loop_scope": "intake_execution"},
        ],
        "turns": [
            {
                "manager_rounds": [
                    {
                        "decision": {
                            "tool_calls": [{"name": "resolve_correction_target"}],
                            "final_action": "correction_applied",
                        }
                    }
                ]
            }
        ],
    }

    grade = grade_live_trace_expectations(case)

    assert grade["required_status"] == "fail"
    assert grade["ideal_target_status"] == "fail"
    checks = {check["check_id"]: check["status"] for check in grade["checks"]}
    assert checks["provider_invocation_count_at_most_2"] == "fail"


def test_accurate_intake_live_trace_expectation_catches_no_plan_zero_budget_reply() -> None:
    from app.composition.accurate_intake_live_trace_expectations import grade_live_trace_expectations

    case = {
        "case_id": "no_plan_consumed_without_budget_target",
        "provider_invocations": [
            {
                "provider_trace": {
                    "parsed_object": {
                        "answer_contract": {
                            "reply_text": "今天已消耗 0 卡路里，但預算為 0 卡路里，剩餘 0 卡路里。"
                        }
                    }
                }
            }
        ],
        "turns": [
            {
                "turn": 1,
                "workflow_effect": "answer_only",
                "state_delta": {"canonical_commit": False, "ledger_updated": False},
                "remaining_budget": {
                    "status": "onboarding_required",
                    "daily_target_kcal": None,
                    "remaining_kcal": None,
                    "consumed_kcal": 0,
                },
                "manager_rounds": [
                    {
                        "decision": {
                            "answer_contract": {
                                "reply_text": "今天已消耗 0 卡路里，但預算為 0 卡路里，剩餘 0 卡路里。"
                            }
                        }
                    }
                ],
            }
        ],
    }

    grade = grade_live_trace_expectations(case)

    assert grade["required_status"] == "fail"
    checks = {check["check_id"]: check for check in grade["checks"]}
    assert checks["no_plan_reply_does_not_claim_zero_budget_or_remaining"]["status"] == "fail"


def test_accurate_intake_live_single_case_probe_supports_turn_limit(tmp_path: Path) -> None:
    module = importlib.import_module("scripts.run_accurate_intake_mvp_live_diagnostic")

    report = module.run_diagnostic(
        output_path=tmp_path / "accurate_intake_mvp_live_diagnostic.json",
        db_path=tmp_path / "accurate_intake_mvp_live.sqlite3",
        provider_override=module.ScriptedAccurateIntakeLiveProvider(),
        provider_mode="fake_provider_contract_test",
        live_invoked=False,
        stage="single_case_live_probe",
        case_id="chinese_chicken_rice_correction_removal_debug",
        max_turn=2,
    )

    case = report["cases"][0]
    assert [turn["turn"] for turn in case["turns"]] == [1, 2]
    assert case["turn_limit"] == {
        "max_turn": 2,
        "original_turn_count": 4,
        "executed_turn_count": 2,
        "completed_turns": [1, 2],
        "last_completed_turn": 2,
        "is_turn_limited": True,
    }
    assert report["stages"][-1]["summary"]["turn_limited_case_count"] == 1


def test_accurate_intake_live_single_case_probe_supports_exact_item_official_label(tmp_path: Path) -> None:
    module = importlib.import_module("scripts.run_accurate_intake_mvp_live_diagnostic")

    report = module.run_diagnostic(
        output_path=tmp_path / "accurate_intake_mvp_live_diagnostic.json",
        db_path=tmp_path / "accurate_intake_mvp_live.sqlite3",
        provider_override=module.ScriptedAccurateIntakeLiveProvider(),
        provider_mode="fake_provider_contract_test",
        live_invoked=False,
        stage="single_case_live_probe",
        case_id="exact_item_official_label",
    )

    case = report["cases"][0]
    assert report["stages"][-1]["stage_id"] == "single_case_live_probe"
    assert report["stages"][-1]["case_ids"] == ["exact_item_official_label"]
    assert report["stages"][-1]["status"] == "pass"
    assert case["case_id"] == "exact_item_official_label"
    assert case["case_contract_status"] == "strict_pass"
    assert case["turns"][0]["state_delta"]["canonical_commit"] is True
    grade = case["trace_expectation_grade"]
    assert grade["expectation_id"] == "exact_item_official_label.trace.v1"
    assert grade["required_status"] == "pass"
    assert {check["check_id"]: check["status"] for check in grade["checks"]} == {
        "single_turn_only": "pass",
        "call_topology_matches_expected": "pass",
        "estimate_nutrition_used": "pass",
        "target_resolution_not_used": "pass",
        "commit_final_present": "pass",
        "canonical_commit_recorded": "pass",
    }
    assert grade["expected_trace"] == [
        "entry: route_to_intake",
        "pass2: estimate_nutrition",
        "guard: commit allowed",
        "mutation: canonical meal commit",
    ]
    assert case["runner_inferred_semantics"] is False
    assert case["raw_text_routing_used"] is False


def test_accurate_intake_live_single_case_probe_supports_manifest_no_plan(tmp_path: Path) -> None:
    module = importlib.import_module("scripts.run_accurate_intake_mvp_live_diagnostic")

    report = module.run_diagnostic(
        output_path=tmp_path / "accurate_intake_mvp_live_diagnostic.json",
        db_path=tmp_path / "accurate_intake_mvp_live.sqlite3",
        provider_override=module.ScriptedAccurateIntakeLiveProvider(),
        provider_mode="fake_provider_contract_test",
        live_invoked=False,
        stage="single_case_live_probe",
        manifest_case_id="MVP-LIVE-001",
    )

    case = report["cases"][0]
    assert report["stages"][-1]["case_ids"] == ["no_plan_consumed_without_budget_target"]
    assert report["stages"][-1]["manifest_case_ids"] == ["MVP-LIVE-001"]
    assert case["case_id"] == "no_plan_consumed_without_budget_target"
    assert case["manifest_case_id"] == "MVP-LIVE-001"
    assert case["case_family"] == "no_plan_degraded"
    assert case["case_contract_status"] == "strict_pass"
    assert case["turns"][0]["state_delta"]["canonical_commit"] is False
    assert case["turns"][0]["remaining_budget"]["daily_target_kcal"] is None
    assert case["turns"][0]["remaining_budget"]["remaining_kcal"] is None
    assert case["provider_invocations"][0]["diagnostic_manifest_case_id"] == "MVP-LIVE-001"


def test_accurate_intake_live_single_case_probe_supports_manifest_generic_range(tmp_path: Path) -> None:
    module = importlib.import_module("scripts.run_accurate_intake_mvp_live_diagnostic")

    report = module.run_diagnostic(
        output_path=tmp_path / "accurate_intake_mvp_live_diagnostic.json",
        db_path=tmp_path / "accurate_intake_mvp_live.sqlite3",
        provider_override=module.ScriptedAccurateIntakeLiveProvider(),
        provider_mode="fake_provider_contract_test",
        live_invoked=False,
        stage="single_case_live_probe",
        manifest_case_id="MVP-LIVE-005",
    )

    case = report["cases"][0]
    assert report["stages"][-1]["case_ids"] == ["generic_common_food_range"]
    assert report["stages"][-1]["manifest_case_ids"] == ["MVP-LIVE-005"]
    assert case["case_id"] == "generic_common_food_range"
    assert case["manifest_case_id"] == "MVP-LIVE-005"
    assert case["case_family"] == "generic_food_range"
    assert case["case_contract_status"] == "strict_pass"
    assert case["turns"][0]["state_delta"]["canonical_commit"] is True
    grade = case["trace_expectation_grade"]
    assert grade["expectation_id"] == "generic_common_food_range.trace.v1"
    assert grade["required_status"] == "pass"
    assert {check["check_id"]: check["status"] for check in grade["checks"]} == {
        "manifest_case_mapped": "pass",
        "single_turn_only": "pass",
        "call_topology_matches_expected": "pass",
        "estimate_nutrition_used": "pass",
        "target_resolution_not_used": "pass",
        "commit_final_present": "pass",
        "canonical_commit_recorded": "pass",
        "same_truth_pass": "pass",
    }
    assert case["provider_invocations"][0]["diagnostic_manifest_case_id"] == "MVP-LIVE-005"


def test_accurate_intake_live_rejects_mixed_runtime_and_manifest_case_selection(tmp_path: Path) -> None:
    module = importlib.import_module("scripts.run_accurate_intake_mvp_live_diagnostic")

    try:
        module.run_diagnostic(
            output_path=tmp_path / "accurate_intake_mvp_live_diagnostic.json",
            db_path=tmp_path / "accurate_intake_mvp_live.sqlite3",
            provider_override=module.ScriptedAccurateIntakeLiveProvider(),
            provider_mode="fake_provider_contract_test",
            live_invoked=False,
            stage="single_case_live_probe",
            case_id="no_plan_consumed_without_budget_target",
            manifest_case_id="MVP-LIVE-001",
        )
    except ValueError as exc:
        assert "Use either case_id or manifest_case_id" in str(exc)
    else:
        raise AssertionError("mixed case selectors should fail before running a diagnostic")


def test_accurate_intake_live_single_case_probe_bubble_refinement_inventory_contract(tmp_path: Path) -> None:
    module = importlib.import_module("scripts.run_accurate_intake_mvp_live_diagnostic")

    report = module.run_diagnostic(
        output_path=tmp_path / "accurate_intake_mvp_live_diagnostic.json",
        db_path=tmp_path / "accurate_intake_mvp_live.sqlite3",
        provider_override=module.ScriptedAccurateIntakeLiveProvider(),
        provider_mode="fake_provider_contract_test",
        live_invoked=False,
        stage="single_case_live_probe",
        case_id="bubble_milk_tea_refinement",
    )

    case = report["cases"][0]
    assert case["case_id"] == "bubble_milk_tea_refinement"
    assert case["case_contract_status"] == "strict_pass"
    assert case["verdict"] == "pass"
    assert [turn["turn"] for turn in case["turns"]] == [1, 2]
    assert all(turn["state_delta"]["canonical_commit"] is True for turn in case["turns"])
    assert all(turn["state_delta"]["draft_saved"] is False for turn in case["turns"])
    assert case["turns"][0]["state_delta"]["old_version_superseded"] is False
    assert case["turns"][1]["state_delta"]["old_version_superseded"] is True
    grade = case["trace_expectation_grade"]
    assert grade["expectation_id"] == "bubble_milk_tea_refinement.trace.v1"
    assert grade["required_status"] == "pass"
    assert {check["check_id"]: check["status"] for check in grade["checks"]} == {
        "two_turn_refinement": "pass",
        "call_topology_matches_expected": "pass",
        "turn1_estimate_and_commit": "pass",
        "turn2_attaches_to_committed_thread": "pass",
        "turn2_supersedes_old_version": "pass",
        "same_truth_pass": "pass",
    }
    tool_names = [
        call["name"]
        for turn in case["turns"]
        for round_item in turn["manager_rounds"]
        for call in round_item["decision"].get("tool_calls", [])
    ]
    assert tool_names == ["estimate_nutrition", "estimate_nutrition"]
    assert case["debug_surface"]["model"]["same_truth"]["status"] == "pass"


def test_accurate_intake_live_luwei_trace_expectation_blocks_bare_basket_commit(
    tmp_path: Path,
) -> None:
    module = importlib.import_module("scripts.run_accurate_intake_mvp_live_diagnostic")

    report = module.run_diagnostic(
        output_path=tmp_path / "accurate_intake_mvp_live_diagnostic.json",
        db_path=tmp_path / "accurate_intake_mvp_live.sqlite3",
        provider_override=module.ScriptedAccurateIntakeLiveProvider(),
        provider_mode="fake_provider_contract_test",
        live_invoked=False,
        stage="single_case_live_probe",
        case_id="luwei_bare_to_listed_basket",
    )

    case = report["cases"][0]
    grade = case["trace_expectation_grade"]
    assert grade["expectation_id"] == "luwei_bare_to_listed_basket.trace.v1"
    assert grade["required_status"] == "pass"
    assert {check["check_id"]: check["status"] for check in grade["checks"]} == {
        "two_turn_blocking_clarify": "pass",
        "call_topology_matches_expected": "pass",
        "turn1_asks_followup": "pass",
        "turn1_draft_saved_without_commit": "pass",
        "turn2_estimates_after_listed_basket": "pass",
        "turn2_commits_after_clarification": "pass",
    }


def test_accurate_intake_live_diagnostic_releases_stage_sqlite_handles(tmp_path: Path) -> None:
    module = importlib.import_module("scripts.run_accurate_intake_mvp_live_diagnostic")
    db_path = tmp_path / "accurate_intake_mvp_live.sqlite3"

    module.run_diagnostic(
        output_path=tmp_path / "accurate_intake_mvp_live_diagnostic.json",
        db_path=db_path,
        provider_override=module.ScriptedAccurateIntakeLiveProvider(),
        provider_mode="fake_provider_contract_test",
        live_invoked=False,
        stage="single_case_live_probe",
        case_id="explicit_item_removal_seeded",
    )

    stage_db_path = db_path.with_name(f"{db_path.stem}.single_case_live_probe{db_path.suffix}")
    assert stage_db_path.exists()
    stage_db_path.unlink()
    assert not stage_db_path.exists()


def test_accurate_intake_live_original_multiturn_blocks_noop_removal_turn() -> None:
    module = importlib.import_module("scripts.run_accurate_intake_mvp_live_diagnostic")
    case = module._single_case_probe_inventory(  # noqa: SLF001 - diagnostic case contract.
        case_id="chinese_chicken_rice_correction_removal_debug",
    )[0]
    turns = [
        {"turn": 1, "state_delta": {"canonical_commit": True}, "runtime_error": None},
        {"turn": 2, "state_delta": {"canonical_commit": True, "old_version_superseded": True}, "runtime_error": None},
        {
            "turn": 3,
            "manager_final_action": "no_commit",
            "workflow_effect": "safe_failure",
            "state_delta": {"canonical_commit": False, "new_meal_version_created": False},
            "runtime_error": None,
        },
        {"turn": 4, "state_delta": {"canonical_commit": False}, "runtime_error": None},
    ]

    verdict, blockers, failure_layer = module._validate_case(  # noqa: SLF001 - diagnostic grader contract.
        case=case,
        turns=turns,
        debug_surface={"model": {"same_truth": {"status": "pass"}}},
    )

    assert verdict == "fail"
    assert failure_layer == "runtime"
    assert "turn_3_expected_canonical_mutation_missing" in blockers


def test_accurate_intake_live_local_evidence_preserves_chicken_rice_and_soup_components() -> None:
    from app.nutrition.application.estimate_artifacts import _shadow_stub_components  # noqa: PLC2701

    components = _shadow_stub_components("\u96de\u8089\u98ef\u548c\u6e6f")

    assert [(component.name, int(component.estimated_kcal or 0)) for component in components] == [
        ("\u96de\u8089\u98ef", 500),
        ("\u6e6f", 150),
    ]


def test_accurate_intake_live_original_turn3_fake_probe_removes_soup_component(tmp_path: Path) -> None:
    module = importlib.import_module("scripts.run_accurate_intake_mvp_live_diagnostic")

    report = module.run_diagnostic(
        output_path=tmp_path / "accurate_intake_mvp_live_diagnostic.json",
        db_path=tmp_path / "accurate_intake_mvp_live.sqlite3",
        provider_override=module.ScriptedAccurateIntakeLiveProvider(),
        provider_mode="fake_provider_contract_test",
        live_invoked=False,
        stage="single_case_live_probe",
        case_id="chinese_chicken_rice_correction_removal_debug",
        max_turn=3,
    )

    case = report["cases"][0]
    assert case["verdict"] == "pass"
    assert case["case_contract_status"] == "strict_pass"
    assert case["turns"][2]["state_delta"]["canonical_commit"] is True
    assert case["turns"][2]["state_delta"]["new_meal_version_created"] is True
    correction_history = case["debug_surface"]["model"]["correction_history"]
    assert correction_history[-1]["removed_item_names"] == ["\u6e6f"]
    active_items = case["debug_surface"]["model"]["meal_threads"][0]["active_version"]["items"]
    assert [item["name"] for item in active_items] == ["\u96de\u8089\u98ef"]


def test_accurate_intake_live_schema_probe_blocks_product_loop_cases(tmp_path: Path) -> None:
    module = importlib.import_module("scripts.run_accurate_intake_mvp_live_diagnostic")

    class SchemaFailingProvider:
        def __init__(self) -> None:
            self.calls = 0

        def readiness(self) -> dict[str, object]:
            return {"provider": "schema-failing", "configured": True}

        async def complete_with_trace(self, **_: object) -> tuple[dict[str, object], dict[str, object]]:
            self.calls += 1
            if self.calls == 1:
                return module.ScriptedAccurateIntakeLiveProvider()._entry_decision(), {"stage": "health"}  # noqa: SLF001
            return {"intent": "log_meal"}, {"stage": "schema"}

    report = module.run_diagnostic(
        output_path=tmp_path / "accurate_intake_mvp_live_diagnostic.json",
        db_path=tmp_path / "accurate_intake_mvp_live.sqlite3",
        provider_override=SchemaFailingProvider(),
        provider_mode="fake_schema_contract_test",
        live_invoked=False,
    )

    assert [stage["stage_id"] for stage in report["stages"]] == [
        "provider_health_smoke",
        "schema_contract_probe",
    ]
    assert report["stages"][0]["status"] == "pass"
    assert report["stages"][1]["status"] == "fail"
    assert report["stages"][1]["failure_layer"] == "provider_contract_non_adherence"
    assert report["stages"][1]["failure_family"] == "schema_contract_blocked"
    assert report["cases"] == []
    assert report["failure_family"] == "schema_contract_blocked"


def test_accurate_intake_live_schema_probe_seeds_public_read_tools() -> None:
    module = importlib.import_module("scripts.run_accurate_intake_mvp_live_diagnostic")
    provider = module.ScriptedAccurateIntakeLiveProvider()

    asyncio.run(
        module._provider_probe(  # noqa: SLF001
            provider=provider,
            stage_id=module.STAGE_SCHEMA_CONTRACT_PROBE,
        )
    )

    assert provider.calls[0]["available_tools"] == [
        "body.get_active_plan",
        "budget.get_today_summary",
    ]


def test_scripted_live_provider_treats_public_read_tools_as_entry_surface() -> None:
    module = importlib.import_module("scripts.run_accurate_intake_mvp_live_diagnostic")
    provider = module.ScriptedAccurateIntakeLiveProvider()
    provider.begin_step({"entry_intent": "answer_remaining_budget", "kind": module.STAGE_SCHEMA_CONTRACT_PROBE})

    payload, trace = asyncio.run(
        provider.complete_with_trace(
            user_payload={
                "round_index": 0,
                "available_tools": ["body.get_active_plan", "budget.get_today_summary"],
                "tool_results": [],
            }
        )
    )

    assert trace["stage"] == "entry_decision"
    assert payload["intent_type"] == "answer_remaining_budget"


def test_accurate_intake_live_unknown_case_id_fails_fast(tmp_path: Path) -> None:
    module = importlib.import_module("scripts.run_accurate_intake_mvp_live_diagnostic")

    try:
        module.run_diagnostic(
            output_path=tmp_path / "accurate_intake_mvp_live_diagnostic.json",
            db_path=tmp_path / "accurate_intake_mvp_live.sqlite3",
            provider_override=module.ScriptedAccurateIntakeLiveProvider(),
            provider_mode="fake_provider_contract_test",
            live_invoked=False,
            stage="single_case_live_probe",
            case_id="missing-case",
        )
    except ValueError as exc:
        assert "Unsupported Accurate Intake live diagnostic case_id" in str(exc)
    else:
        raise AssertionError("unknown case_id should fail before running a diagnostic")


def test_accurate_intake_live_missing_provider_report_is_environment_blocker() -> None:
    module = importlib.import_module("scripts.run_accurate_intake_mvp_live_diagnostic")
    profile = module.provider_profile(module.DEFAULT_ACCURATE_INTAKE_LIVE_DIAGNOSTIC_PROVIDER_PROFILE_ID)

    report = module.build_missing_provider_report(profile=profile)

    assert report["artifact_type"] == "accurate_intake_mvp_live_diagnostic"
    assert report["provider_mode"] == "not_invoked"
    assert report["live_invoked"] is False
    assert report["failure_layer"] == "provider_runtime_error"
    assert report["failure_family"] == "environment_or_provider_blocker"
    assert report["readiness_claimed"] is False
    assert report["private_self_use_approved"] is False
    assert report["production_selected"] is False
    assert report["mutation_rollout_approved"] is False
    assert report["runtime_web_activation_approved"] is False
    assert report["cases"] == []


def test_accurate_intake_live_provider_failure_taxonomy_splits_missing_synthetic_tool_call() -> None:
    module = importlib.import_module("scripts.run_accurate_intake_mvp_live_diagnostic")

    assert (
        module._failure_family_for_error_dict(  # noqa: SLF001 - diagnostic taxonomy contract.
            {
                "type": "RuntimeError",
                "message": "BuilderSpace did not return the synthetic decision tool call.",
            }
        )
        == "synthetic_decision_tool_call_missing"
    )
    assert (
        module._failure_family_for_error_dict(  # noqa: SLF001 - diagnostic taxonomy contract.
            {
                "type": "RuntimeError",
                "message": "manager payload missing required fields for intake_manager_round: ['semantic_decision']",
            }
        )
        == "schema_payload_invalid"
    )


def test_accurate_intake_live_repaired_pass_remains_diagnostic_only() -> None:
    module = importlib.import_module("scripts.run_accurate_intake_mvp_live_diagnostic")
    profile = module.provider_profile(module.DEFAULT_ACCURATE_INTAKE_LIVE_DIAGNOSTIC_PROVIDER_PROFILE_ID)
    case = {
        "case_id": "bubble_milk_tea_refinement",
        "verdict": "pass",
        "turns": [
            {
                "manager_rounds": [
                    {
                        "trace": {
                            "repair_attempted": True,
                            "repair_result": "passed_after_repair",
                            "request_failure_family": "commit_without_evidence",
                        }
                    }
                ]
            }
        ],
    }

    decorated = module._decorate_case(case, profile=profile)  # noqa: SLF001 - diagnostic taxonomy contract.

    assert decorated["case_contract_status"] == "repaired_pass"
    assert decorated["private_self_use_unlock_allowed"] is False
    assert decorated["readiness_claimed"] is False
    assert decorated["production_selected"] is False


def test_accurate_intake_live_timeout_is_tracked_separately() -> None:
    module = importlib.import_module("scripts.run_accurate_intake_mvp_live_diagnostic")

    summary = module._summary(  # noqa: SLF001 - artifact summary contract.
        [
            {
                "case_id": "timeout-case",
                "verdict": "fail",
                "case_contract_status": "timeout",
                "failure_family": "environment_or_provider_blocker",
            },
            {
                "case_id": "strict-case",
                "verdict": "pass",
                "case_contract_status": "strict_pass",
            },
        ]
    )

    assert summary["timeout_count"] == 1
    assert summary["provider_timeout_count"] == 1


def test_accurate_intake_live_case_timeout_writes_environment_blocker_artifact(tmp_path: Path) -> None:
    module = importlib.import_module("scripts.run_accurate_intake_mvp_live_diagnostic")

    class HangingProvider:
        def readiness(self) -> dict[str, object]:
            return {"provider": "hanging", "configured": True}

        async def complete_with_trace(self, **_: object) -> tuple[dict[str, object], dict[str, object]]:
            import asyncio

            await asyncio.sleep(5)
            return {}, {}

    output_path = tmp_path / "accurate_intake_mvp_live_diagnostic.json"
    report = module.run_diagnostic(
        output_path=output_path,
        db_path=tmp_path / "accurate_intake_mvp_live.sqlite3",
        local_date="2026-05-02",
        provider_override=HangingProvider(),
        provider_mode="fake_timeout_contract_test",
        live_invoked=False,
        provider_timeout_ms=1,
        case_timeout_ms=1,
        provider_request_retry_count=0,
        stage="single_case_live_probe",
        case_id="explicit_item_removal_seeded",
    )

    assert output_path.exists()
    assert report["summary"]["timeout_count"] == report["summary"]["case_count"]
    assert set(report["summary"]["failure_families"]) == {"environment_or_provider_blocker"}
    assert all(case["case_contract_status"] == "timeout" for case in report["cases"])
    assert any(stage["failure_family"] == "environment_or_provider_blocker" for stage in report["stages"])


def test_accurate_intake_live_provider_request_retry_pass_is_not_strict(tmp_path: Path) -> None:
    module = importlib.import_module("scripts.run_accurate_intake_mvp_live_diagnostic")

    class FlakyProvider:
        def __init__(self) -> None:
            self.calls = 0

        def readiness(self) -> dict[str, object]:
            return {"provider": "flaky", "configured": True}

        async def complete_with_trace(self, **_: object) -> tuple[dict[str, object], dict[str, object]]:
            self.calls += 1
            if self.calls == 1:
                raise TimeoutError("simulated provider timeout")
            return {"ok": True}, {"provider_trace": {"simulated": True}}

    report = module.run_diagnostic(
        output_path=tmp_path / "accurate_intake_mvp_live_diagnostic.json",
        db_path=tmp_path / "accurate_intake_mvp_live.sqlite3",
        provider_override=FlakyProvider(),
        provider_mode="fake_retry_contract_test",
        live_invoked=False,
        stage="provider_health_smoke",
        provider_timeout_ms=50,
        provider_request_retry_count=1,
        provider_request_retry_backoff_ms=0,
    )

    stage = report["stages"][0]
    assert stage["status"] == "pass"
    assert stage["attempt_count"] == 2
    assert stage["result_kind"] == "pass_after_retry"
    assert stage["retry_policy_applied"] is True
    assert report["summary"]["retried_pass_count"] == 1
    assert report["summary"]["strict_pass_count"] == 0


def test_accurate_intake_live_repaired_case_surfaces_failed_invariant() -> None:
    module = importlib.import_module("scripts.run_accurate_intake_mvp_live_diagnostic")
    profile = module.provider_profile(module.DEFAULT_ACCURATE_INTAKE_LIVE_DIAGNOSTIC_PROVIDER_PROFILE_ID)

    decorated = module._decorate_case(  # noqa: SLF001 - diagnostic artifact contract.
        {
            "case_id": "chinese_chicken_rice_correction_removal_debug",
            "verdict": "pass",
            "turns": [
                {
                    "turn": 3,
                    "manager_rounds": [
                        {
                            "trace": {
                                "repair_attempted": True,
                                "repair_result": "passed_after_repair",
                                "repair_attempt_count": 1,
                                "parse_attempts": [
                                    {
                                        "failure_family": "manager_output_contract_violation",
                                        "error": "founder live manager contract requires non-empty tool_calls when manager_action='call_tools'",
                                    }
                                ],
                            }
                        }
                    ],
                }
            ],
        },
        profile=profile,
    )

    assert decorated["case_contract_status"] == "repaired_pass"
    assert decorated["repair_failure_family"] == "manager_output_contract_violation"
    assert decorated["failed_invariant"] == "call_tools_requires_tool_calls"
    assert decorated["repair_diagnostics"] == [
        {
            "turn": 3,
            "repair_result": "passed_after_repair",
            "repair_attempt_count": 1,
            "repair_failure_family": "manager_output_contract_violation",
            "failed_invariant": "call_tools_requires_tool_calls",
        }
    ]


def test_accurate_intake_live_repaired_remove_item_surfaces_target_evidence_invariant() -> None:
    module = importlib.import_module("scripts.run_accurate_intake_mvp_live_diagnostic")
    profile = module.provider_profile(module.DEFAULT_ACCURATE_INTAKE_LIVE_DIAGNOSTIC_PROVIDER_PROFILE_ID)

    decorated = module._decorate_case(  # noqa: SLF001 - diagnostic artifact contract.
        {
            "case_id": "explicit_item_removal_seeded",
            "verdict": "pass",
            "turns": [
                {
                    "turn": 1,
                    "manager_rounds": [
                        {
                            "trace": {
                                "repair_attempted": True,
                                "repair_result": "passed_after_repair",
                                "repair_attempt_count": 1,
                                "parse_attempts": [
                                    {
                                        "failure_family": "manager_output_contract_violation",
                                        "error": (
                                            "remove_item finalization requires target evidence before "
                                            "final_action='correction_applied'"
                                        ),
                                    }
                                ],
                            }
                        }
                    ],
                }
            ],
        },
        profile=profile,
    )

    assert decorated["case_contract_status"] == "repaired_pass"
    assert decorated["repair_failure_family"] == "manager_output_contract_violation"
    assert decorated["failed_invariant"] == "remove_item_requires_target_evidence"
    assert decorated["repair_diagnostics"][0]["failed_invariant"] == "remove_item_requires_target_evidence"


def test_accurate_intake_live_provider_request_timeout_after_retry_remains_blocker(tmp_path: Path) -> None:
    module = importlib.import_module("scripts.run_accurate_intake_mvp_live_diagnostic")

    class AlwaysTimeoutProvider:
        def readiness(self) -> dict[str, object]:
            return {"provider": "always-timeout", "configured": True}

        async def complete_with_trace(self, **_: object) -> tuple[dict[str, object], dict[str, object]]:
            raise TimeoutError("simulated provider timeout")

    report = module.run_diagnostic(
        output_path=tmp_path / "accurate_intake_mvp_live_diagnostic.json",
        db_path=tmp_path / "accurate_intake_mvp_live.sqlite3",
        provider_override=AlwaysTimeoutProvider(),
        provider_mode="fake_retry_contract_test",
        live_invoked=False,
        stage="provider_health_smoke",
        provider_timeout_ms=50,
        provider_request_retry_count=1,
        provider_request_retry_backoff_ms=0,
    )

    stage = report["stages"][0]
    assert stage["status"] == "timeout"
    assert stage["attempt_count"] == 2
    assert stage["result_kind"] == "timeout_after_retry"
    assert stage["retry_policy_applied"] is True
    assert stage["failure_family"] == "environment_or_provider_blocker"
    assert report["summary"]["provider_timeout_count"] == 1
