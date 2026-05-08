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
            assert turn["provider_invocation_summary"]["provider_invocation_count"] >= 1
            assert isinstance(turn["provider_invocation_summary"]["provider_invocation_latency_ms"], int)
        assert case["provider_invocation_count"] >= len(case["turns"])
        assert isinstance(case["provider_invocation_latency_ms"], int)
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
    case_invocations = [item for item in report["provider_invocations"] if item.get("diagnostic_case_id")]
    assert case_invocations
    assert all(item["span_kind"] == "provider_request" for item in case_invocations)
    assert all(item.get("diagnostic_turn") for item in case_invocations)
    assert report["summary"]["case_count"] == len(report["cases"])
    assert report["summary"]["strict_pass_count"] + report["summary"]["repaired_pass_count"] + report["summary"][
        "contract_fail_count"
    ] + report["summary"]["timeout_count"] == len(report["cases"])


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
    assert case["runner_inferred_semantics"] is False
    assert case["raw_text_routing_used"] is False


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
    tool_names = [
        call["name"]
        for turn in case["turns"]
        for round_item in turn["manager_rounds"]
        for call in round_item["decision"].get("tool_calls", [])
    ]
    assert tool_names == ["estimate_nutrition", "estimate_nutrition"]
    assert case["debug_surface"]["model"]["same_truth"]["status"] == "pass"


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
