from __future__ import annotations

import json
from pathlib import Path

from app.composition.accurate_intake_context_live_diagnostic_anti_overfit_guard import (
    build_context_live_diagnostic_anti_overfit_guard_artifact,
)
from app.composition.accurate_intake_context_live_diagnostic_case_matrix import (
    REQUIRED_CASE_IDS,
    build_context_live_diagnostic_case_matrix_artifact,
)
from app.composition.accurate_intake_context_live_provider_input_preflight import (
    REQUIRED_RESPONSE_FIELDS,
    RESPONSE_SCHEMA_NAME,
    build_context_live_provider_input_preflight_artifact,
)


def test_context_live_provider_input_preflight_builds_fixed_strict_schema_inputs_without_live_calls() -> None:
    artifact = build_context_live_provider_input_preflight_artifact()

    assert artifact["artifact_type"] == "accurate_intake_context_live_provider_input_preflight"
    assert artifact["status"] == "pass"
    assert artifact["diagnostic_only"] is True
    assert artifact["plan_only"] is True
    assert artifact["fixture_only"] is True
    assert artifact["provider_call_ready"] is False
    assert artifact["human_approval_required_before_live_provider"] is True
    assert artifact["fixed_case_matrix_used"] is True
    assert artifact["response_schema_name"] == RESPONSE_SCHEMA_NAME
    assert artifact["response_schema_strict"] is True
    assert artifact["required_response_fields"] == list(REQUIRED_RESPONSE_FIELDS)
    assert artifact["semantic_owner"] == "future_live_manager_provider_when_human_approved"
    assert artifact["deterministic_role"] == "validate_provider_input_contract_not_select_intent"
    assert artifact["deterministic_selected_intent"] is False
    assert artifact["raw_text_intent_router_used"] is False
    assert artifact["live_llm_invoked"] is False
    assert artifact["live_provider_invoked"] is False
    assert artifact["fooddb_used"] is False
    assert artifact["web_tavily_used"] is False
    assert artifact["mutation_changed"] is False
    assert artifact["manager_context_packet_schema_changed"] is False
    assert artifact["product_readiness_claimed"] is False
    assert artifact["private_self_use_approved"] is False
    assert artifact["blockers"] == []
    assert artifact["summary"]["case_count"] == len(REQUIRED_CASE_IDS)
    assert artifact["summary"]["provider_input_count"] == len(REQUIRED_CASE_IDS)
    assert artifact["summary"]["blocked_input_count"] == 0
    assert artifact["summary"]["strict_schema_input_count"] == len(REQUIRED_CASE_IDS)
    assert artifact["summary"]["target_candidate_inputs"] >= 1
    assert artifact["summary"]["pending_pin_inputs"] >= 1


def test_context_live_provider_input_preflight_omits_forbidden_context_from_every_input() -> None:
    artifact = build_context_live_provider_input_preflight_artifact()
    required_omissions = {
        "raw_trace_dump",
        "dogfood_review_artifact",
        "fooddb_gap_candidate_as_truth",
        "long_term_memory",
        "debug_artifact",
    }

    for provider_input in artifact["provider_inputs"]:
        context = provider_input["manager_context_sidecar"]
        assert required_omissions.issubset(set(context["omitted_context_summary"]))
        assert provider_input["tool_policy"]["tools_available"] == []
        assert provider_input["tool_policy"]["tool_outputs_as_truth"] is False
        assert provider_input["expected_semantic_contract"]["mutation_allowed"] is False
        assert "deterministic_selected_intent" in provider_input["expected_semantic_contract"][
            "must_not_happen"
        ]
        assert (
            provider_input["expected_semantic_contract"]["target_resolution_scope"]
            == "prior_meal_or_item_reference_only_not_daily_budget_or_food_identity"
        )


def test_context_live_provider_input_preflight_schema_defines_target_resolution_scope() -> None:
    artifact = build_context_live_provider_input_preflight_artifact()
    schema = artifact["provider_inputs"][0]["response_schema"]
    target_resolution = schema["properties"]["target_resolution"]

    assert "Correction/removal target resolution only" in target_resolution["description"]
    assert "daily targets" in target_resolution["description"]
    assert "never include numeric daily calorie targets" in target_resolution["properties"]["candidate_ids"][
        "description"
    ]


def test_context_live_provider_input_preflight_blocks_non_fixed_matrix_or_failed_guard() -> None:
    matrix = build_context_live_diagnostic_case_matrix_artifact()
    matrix["cases"][0]["case_id"] = "ad_hoc_easy_case"
    guard = build_context_live_diagnostic_anti_overfit_guard_artifact(matrix)

    artifact = build_context_live_provider_input_preflight_artifact(
        context_live_diagnostic_case_matrix=matrix,
        context_live_diagnostic_anti_overfit_guard=guard,
    )

    assert artifact["status"] == "blocked"
    assert "matrix.fixed_case_order_mismatch" in artifact["blockers"]
    assert "anti_overfit_guard.status_not_pass" in artifact["blockers"]
    assert "anti_overfit_guard.fixed_case_matrix_not_used" in artifact["blockers"]
    assert "provider_input_fixed_case_order_mismatch" in artifact["blockers"]


def test_context_live_provider_input_preflight_blocks_loose_schema_and_tools() -> None:
    artifact = build_context_live_provider_input_preflight_artifact()
    provider_inputs = list(artifact["provider_inputs"])
    provider_inputs[0] = {
        **dict(provider_inputs[0]),
        "response_schema": {
            **dict(provider_inputs[0]["response_schema"]),
            "strict": False,
            "required": ["case_id"],
        },
        "tool_policy": {
            "tools_available": ["fooddb_lookup"],
            "fooddb_used": True,
            "web_tavily_used": False,
            "tool_outputs_as_truth": True,
        },
        "live_provider_invoked": True,
    }

    blocked = build_context_live_provider_input_preflight_artifact(provider_inputs=provider_inputs)

    case_id = str(provider_inputs[0]["case_id"])
    assert blocked["status"] == "blocked"
    assert f"{case_id}.response_schema_not_strict" in blocked["blockers"]
    assert f"{case_id}.response_schema_required_fields_mismatch" in blocked["blockers"]
    assert f"{case_id}.tools_available_not_empty" in blocked["blockers"]
    assert f"{case_id}.tool_outputs_as_truth" in blocked["blockers"]
    assert f"{case_id}.live_provider_invoked" in blocked["blockers"]


def test_context_live_provider_input_preflight_blocks_missing_context_omissions() -> None:
    artifact = build_context_live_provider_input_preflight_artifact()
    provider_inputs = list(artifact["provider_inputs"])
    provider_inputs[3] = {
        **dict(provider_inputs[3]),
        "manager_context_sidecar": {
            **dict(provider_inputs[3]["manager_context_sidecar"]),
            "omitted_context_summary": ["raw_trace_dump"],
            "loaded_context_summary": [],
        },
    }

    blocked = build_context_live_provider_input_preflight_artifact(provider_inputs=provider_inputs)

    case_id = str(provider_inputs[3]["case_id"])
    assert blocked["status"] == "blocked"
    assert f"{case_id}.loaded_context_summary_missing_policy" in blocked["blockers"]
    assert f"{case_id}.forbidden_key_not_omitted:dogfood_review_artifact" in blocked["blockers"]
    assert f"{case_id}.forbidden_key_not_omitted:long_term_memory" in blocked["blockers"]


def test_context_live_provider_input_preflight_cli_writes_artifact(tmp_path: Path) -> None:
    from scripts.build_accurate_intake_context_live_provider_input_preflight import main

    output_path = tmp_path / "provider-input-preflight.json"

    assert main(["--output", str(output_path)]) == 0
    artifact = json.loads(output_path.read_text(encoding="utf-8"))
    assert artifact["status"] == "pass"
    assert artifact["summary"]["case_count"] == len(REQUIRED_CASE_IDS)


def test_context_live_provider_input_preflight_source_stays_out_of_forbidden_boundaries() -> None:
    source_paths = [
        Path("app/composition/accurate_intake_context_live_provider_input_preflight.py"),
        Path("scripts/build_accurate_intake_context_live_provider_input_preflight.py"),
    ]
    forbidden = [
        "NutritionEvidenceStorePort",
        "FoodEvidenceRecord",
        "PacketReadyAnchor",
        "TavilyClient",
        "BuilderSpaceAdapter",
        "builderspace_adapter",
        "live_llm_invoked = True",
        "live_provider_invoked = True",
        "fooddb_used = True",
        "manager_context_packet_schema_changed = True",
    ]

    for path in source_paths:
        source = path.read_text(encoding="utf-8")
        for fragment in forbidden:
            assert fragment not in source
