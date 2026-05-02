from __future__ import annotations

import importlib
import json
from pathlib import Path


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
    assert report["summary"]["case_count"] == len(report["cases"])
    assert report["summary"]["strict_pass_count"] + report["summary"]["repaired_pass_count"] + report["summary"][
        "contract_fail_count"
    ] + report["summary"]["timeout_count"] == len(report["cases"])


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
        case_timeout_ms=1,
    )

    assert output_path.exists()
    assert report["summary"]["timeout_count"] == report["summary"]["case_count"]
    assert set(report["summary"]["failure_families"]) == {"environment_or_provider_blocker"}
    assert all(case["case_contract_status"] == "timeout" for case in report["cases"])
