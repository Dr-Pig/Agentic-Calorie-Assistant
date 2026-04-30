from __future__ import annotations

import importlib
import json
from pathlib import Path


def test_founder_live_diagnostic_source_avoids_legacy_and_activation_shortcuts() -> None:
    runner_path = Path("scripts/run_wave1_founder_e2e_live_diagnostic.py")
    source = runner_path.read_text(encoding="utf-8")

    forbidden_markers = (
        "app.runtime.application.phase_a_context",
        "old_" + "c001_" + "draft" + "_first_oracle",
        "run_v2_" + "bundle1" + "_live_eval",
        "run_v2_" + "bundle2" + "_live_eval",
        "docs/" + "archive",
        "allow_search=True",
        "readiness_claimed=True",
        "production_selected=True",
    )
    for marker in forbidden_markers:
        assert marker not in source


def test_founder_live_provider_profile_is_diagnostic_only() -> None:
    module = importlib.import_module("scripts.run_wave1_founder_e2e_live_diagnostic")

    profile = module.provider_profile(module.DEFAULT_FOUNDER_LIVE_DIAGNOSTIC_PROVIDER_PROFILE_ID)

    assert profile["provider_profile_id"] == "builderspace-grok-4-fast-founder-live-contract"
    assert profile["model"] == "grok-4-fast"
    assert profile["provider_profile_role"] == "founder_live_contract_diagnostic"
    assert profile["production_selected"] is False
    assert profile["not_production_selection"] is True
    assert profile["readiness_owner"] is False
    assert profile["transport_policy"]["primary"] == "synthetic_tool_transport"
    assert profile["transport_policy"]["fallback"] == "json_schema"
    assert "plain_json_object_without_schema_validation" in profile["transport_policy"]["forbidden_as_success"]
    assert profile["schema_name"] == "founder_live_manager_contract"
    assert profile["schema_version"] == "v1"


def test_founder_live_diagnostic_artifact_contract_with_fake_provider(tmp_path: Path) -> None:
    module = importlib.import_module("scripts.run_wave1_founder_e2e_live_diagnostic")
    deterministic = importlib.import_module("scripts.run_wave1_founder_e2e_deterministic_diagnostic")
    output_path = tmp_path / "wave1_founder_e2e_live_diagnostic.json"
    db_path = tmp_path / "wave1_founder_e2e_live.sqlite3"

    report = module.run_diagnostic(
        output_path=output_path,
        db_path=db_path,
        local_date="2026-04-30",
        provider_override=deterministic.DeterministicFounderProvider(),
        provider_mode="fake_provider_contract_test",
        live_invoked=False,
    )

    assert output_path.exists()
    assert json.loads(output_path.read_text(encoding="utf-8")) == report
    assert report["artifact_type"] == "wave1_founder_e2e_live_diagnostic"
    assert report["provider_mode"] == "fake_provider_contract_test"
    assert report["live_invoked"] is False
    assert report["readiness_claimed"] is False
    assert report["user_facing_enabled"] is False
    assert report["mutation_enabled"] is False
    assert report["runtime_web_activation_approved"] is False
    assert report["tavily_or_web_activated"] is False
    assert report["production_selected"] is False
    assert report["provider_profile_id"] == module.DEFAULT_FOUNDER_LIVE_DIAGNOSTIC_PROVIDER_PROFILE_ID
    assert report["provider_profile_model"] == "grok-4-fast"
    assert report["active_entrypoint_verified"] is True
    assert report["legacy_guard"]["legacy_dependency_detected"] is False
    assert report["readiness_claim"]["claim_scope"] == "unit_contract"
    assert "product_ready" in report["readiness_claim"]["forbidden_claims"]
    assert "mutation_ready" in report["readiness_claim"]["forbidden_claims"]

    case_ids = [case["case_id"] for case in report["cases"]]
    assert case_ids == [
        "pearl_milk_tea_logged_followup",
        "luwei_ask_first",
        "generic_stable_tea_egg",
        "exact_brand_matsuya_beef_bowl",
        "query_only_pearl_milk_tea_calories",
        "correction_prior_pearl_milk_tea_half_sugar",
        "today_ledger_read_model",
    ]
    assert all(case["provider_profile_id"] == report["provider_profile_id"] for case in report["cases"])
    assert all(case["provider_profile_model"] == "grok-4-fast" for case in report["cases"])
    assert all(case["case_contract_status"] in {"strict_pass", "repaired_pass", "fail"} for case in report["cases"])
    assert all(case["failure_layer"] != "legacy_dependency" for case in report["cases"])
    assert report["summary"]["pass_count"] + report["summary"]["fail_count"] + report["summary"][
        "product_decision_required_count"
    ] + report["summary"]["deferred_count"] == len(report["cases"])
    assert report["summary"]["strict_pass_count"] + report["summary"]["repaired_pass_count"] + report["summary"][
        "contract_fail_count"
    ] == len(report["cases"])


def test_founder_live_missing_provider_token_report_is_not_live_readiness() -> None:
    module = importlib.import_module("scripts.run_wave1_founder_e2e_live_diagnostic")
    profile = module.provider_profile(module.DEFAULT_FOUNDER_LIVE_DIAGNOSTIC_PROVIDER_PROFILE_ID)

    report = module.build_missing_provider_report(profile=profile)

    assert report["artifact_type"] == "wave1_founder_e2e_live_diagnostic"
    assert report["provider_mode"] == "not_invoked"
    assert report["live_invoked"] is False
    assert report["failure_layer"] == "provider_runtime_error"
    assert report["failure_family"] == "missing_provider_token"
    assert report["readiness_claimed"] is False
    assert report["readiness_claim"]["claim_scope"] == "unit_contract"
    assert report["runtime_web_activation_approved"] is False
    assert report["cases"] == []


def test_founder_live_classifies_manager_contract_parse_error() -> None:
    module = importlib.import_module("scripts.run_wave1_founder_e2e_live_diagnostic")
    profile = module.provider_profile(module.DEFAULT_FOUNDER_LIVE_DIAGNOSTIC_PROVIDER_PROFILE_ID)
    case = {
        "case_id": "pearl_milk_tea_logged_followup",
        "verdict": "fail",
        "failure_layer": "runtime",
        "actual_behavior": {
            "runtime_error": {
                "type": "BuilderSpaceResponseError",
                "message": (
                    "BuilderSpace manager error at stage=intake_manager_round: "
                    "BuilderSpaceParseError: manager payload missing required fields"
                ),
            }
        },
    }

    decorated = module._decorate_case(case, profile=profile)  # noqa: SLF001 - diagnostic taxonomy is runner contract.

    assert decorated["failure_layer"] == "provider_contract_non_adherence"
    assert decorated["failure_family"] == "provider_contract_non_adherence"
    assert decorated["case_contract_status"] == "fail"


def test_founder_live_classifies_repaired_pass_as_diagnostic_only() -> None:
    module = importlib.import_module("scripts.run_wave1_founder_e2e_live_diagnostic")
    profile = module.provider_profile(module.DEFAULT_FOUNDER_LIVE_DIAGNOSTIC_PROVIDER_PROFILE_ID)
    case = {
        "case_id": "pearl_milk_tea_logged_followup",
        "verdict": "pass",
        "actual_behavior": {
            "manager_rounds": [
                {
                    "trace": {
                        "repair_attempted": True,
                        "repair_result": "passed_after_repair",
                    }
                }
            ]
        },
    }

    decorated = module._decorate_case(case, profile=profile)  # noqa: SLF001 - diagnostic taxonomy is runner contract.

    assert decorated["case_contract_status"] == "repaired_pass"
    assert decorated["readiness_claimed"] is False
    assert decorated["production_selected"] is False


def test_founder_live_contract_status_is_strict_when_runtime_consumed_manager_payload() -> None:
    module = importlib.import_module("scripts.run_wave1_founder_e2e_live_diagnostic")
    profile = module.provider_profile(module.DEFAULT_FOUNDER_LIVE_DIAGNOSTIC_PROVIDER_PROFILE_ID)
    case = {
        "case_id": "pearl_milk_tea_logged_followup",
        "verdict": "fail",
        "failure_layer": "mutation",
        "actual_behavior": {
            "runtime_error": None,
            "manager_intent": "log_meal",
            "manager_semantic_decision": {"semantic_authority": "manager_llm"},
        },
    }

    decorated = module._decorate_case(case, profile=profile)  # noqa: SLF001 - diagnostic taxonomy is runner contract.

    assert decorated["failure_layer"] == "mutation"
    assert decorated["case_contract_status"] == "strict_pass"
