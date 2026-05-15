from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from app.composition.current_shell_golden_set_correction_matchers import (
    matches_remove_meal_workflow,
    matches_unique_recent_or_named_slot_attachment,
)
from app.composition.current_shell_golden_set_manifest_access import (
    fake_pass_generalization_blockers,
    golden_case_by_id,
)
from app.composition.current_shell_golden_set_ui_feedback_grader import (
    browser_entrypoint_blockers,
    dogfood_trace_blockers,
)


GOLDEN_SET_MANIFEST_PATH = Path("docs/quality/current_shell_self_use_golden_set_manifest.yaml")


def load_golden_set_manifest(path: Path = GOLDEN_SET_MANIFEST_PATH) -> dict[str, Any]:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8-sig"))
    return dict(loaded) if isinstance(loaded, dict) else {}


def grade_golden_case_result(
    result: dict[str, Any],
    *,
    manifest: dict[str, Any] | None = None,
) -> dict[str, Any]:
    golden_manifest = manifest or load_golden_set_manifest()
    case_id = str(result.get("case_id") or "")
    case = golden_case_by_id(golden_manifest, case_id)
    blockers: list[str] = []
    warnings: list[str] = []

    if not case:
        return _grade_result(case_id=case_id, blockers=[f"case_id_unknown:{case_id}"], warnings=[])

    blockers.extend(_fixture_decision_blockers(result, golden_manifest))
    blockers.extend(_trace_layer_blockers(result, case, golden_manifest))
    blockers.extend(browser_entrypoint_blockers(result, case))
    blockers.extend(_expected_mapping_blockers("runtime", result.get("runtime"), case.get("expected_runtime")))
    blockers.extend(_expected_mapping_blockers("ui", result.get("ui"), case.get("ui_assertions")))
    blockers.extend(_response_blockers(result))
    blockers.extend(_latency_blockers(result, case))
    blockers.extend(dogfood_trace_blockers(result, case))
    blockers.extend(_generalization_blockers(result))

    return _grade_result(case_id=case_id, blockers=blockers, warnings=warnings)


def _grade_result(*, case_id: str, blockers: list[str], warnings: list[str]) -> dict[str, Any]:
    return {
        "artifact_type": "current_shell_self_use_golden_case_grade",
        "case_id": case_id,
        "status": "blocked" if blockers else "pass",
        "blockers": blockers,
        "warnings": warnings,
        "deterministic_grader_owns_semantics": False,
    }


def _fixture_decision_blockers(result: dict[str, Any], manifest: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    fixture_policy = dict(manifest.get("fixture_policy") or {})
    fixture_decisions = dict(result.get("fixture_decisions") or {})
    decision_fields = {
        "intent": "fixtures_may_decide_intent",
        "action": "fixtures_may_decide_action",
        "attach_target": "fixtures_may_decide_attach_target",
        "mutation_outcome": "fixtures_may_decide_mutation_outcome",
        "response_meaning": "fixtures_may_decide_response_meaning",
    }
    for field, policy_key in decision_fields.items():
        if fixture_policy.get(policy_key) is False and fixture_decisions.get(field) is True:
            blockers.append(f"fixture_decisions.{field}_not_allowed")
    return blockers


def _trace_layer_blockers(
    result: dict[str, Any],
    case: dict[str, Any],
    manifest: dict[str, Any],
) -> list[str]:
    blockers: list[str] = []
    trace_layers = dict(result.get("trace_layers") or {})
    blocking_layers = set(list(dict(manifest.get("trace_layers") or {}).get("blocking") or []))
    for layer_id in list(case.get("required_trace_layers") or []):
        if layer_id not in trace_layers and layer_id in blocking_layers:
            blockers.append(f"trace_layers.{layer_id}_missing")
    return blockers


def _expected_mapping_blockers(
    prefix: str,
    actual_value: Any,
    expected_value: Any,
) -> list[str]:
    blockers: list[str] = []
    actual = dict(actual_value or {}) if isinstance(actual_value, dict) else {}
    expected = dict(expected_value or {}) if isinstance(expected_value, dict) else {}

    for key, expected_item in expected.items():
        if _skip_expected_item(expected_item):
            continue
        actual_item = actual.get(key)
        if not _expected_item_matches(
            prefix=prefix,
            key=key,
            expected_item=expected_item,
            actual_item=actual_item,
            actual=actual,
        ):
            blockers.append(
                f"{prefix}.{key}_expected:{_display(expected_item)}_actual:{_display(actual_item)}"
            )
    return blockers


def _skip_expected_item(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    return value.startswith("depends_on_") or value in {
        "commit_or_commit_with_optional_refinement",
        "commit_or_ask_clarification",
    }


def _expected_item_matches(
    *,
    prefix: str,
    key: str,
    expected_item: Any,
    actual_item: Any,
    actual: dict[str, Any],
) -> bool:
    if actual_item == expected_item:
        return True
    if (
        prefix == "runtime"
        and key == "workflow_effect"
        and expected_item == "commit"
        and actual_item == "canonical_write"
    ):
        return (
            actual.get("final_action") == "commit"
            and actual.get("canonical_commit_status") == "committed"
        )
    if (
        prefix == "runtime"
        and key == "workflow_effect"
        and expected_item in {
            "answer_or_ask_followup_no_mutation",
            "ask_followup_or_answer_insufficient_evidence",
            "answer_or_ask_followup_no_mutation_until_approved_packet",
        }
        and actual_item in {"ask_followup", "answer_only", "answer_query"}
    ):
        return actual.get("runtime_mutation_allowed") is False or actual.get("mutation_allowed") is False
    if (
        prefix == "runtime"
        and key == "workflow_effect"
        and expected_item == "correction"
        and actual_item in {"correction", "correction_write", "correction_applied", "canonical_write"}
    ):
        return (
            actual.get("final_action") == "correction_applied"
            and actual.get("canonical_commit_status") == "committed"
            and actual.get("old_version_superseded") is True
        )
    if (
        prefix == "runtime"
        and key == "workflow_effect"
        and expected_item == "remove_meal"
    ):
        return matches_remove_meal_workflow(actual, actual_item)
    if (
        prefix == "runtime"
        and key == "workflow_effect"
        and expected_item == "commit_then_refine"
        and actual_item in {"canonical_write", "correction_write", "correction_applied"}
    ):
        return (
            actual.get("final_action") == "correction_applied"
            and actual.get("canonical_commit_status") == "committed"
            and actual.get("old_version_superseded") is True
        )
    if (
        prefix == "runtime"
        and key == "target_attachment"
        and expected_item in {"pending_followup", "pending_teppan_combo"}
    ):
        return _matches_pending_followup_attachment(actual_item)
    if (
        prefix == "runtime"
        and key == "target_attachment"
        and expected_item == "previous_teppan_meal"
    ):
        return _matches_previous_meal_attachment(actual_item)
    if (
        prefix == "runtime"
        and key == "target_attachment"
        and expected_item == "unique_recent_or_named_slot"
    ):
        return matches_unique_recent_or_named_slot_attachment(actual_item)
    if (
        prefix == "runtime"
        and key == "target_attachment"
        and expected_item == "prior_optional_followup"
    ):
        return _matches_prior_optional_followup_attachment(actual_item)
    return False


def _matches_pending_followup_attachment(actual_item: Any) -> bool:
    if not isinstance(actual_item, dict):
        return False
    operation = str(actual_item.get("operation") or actual_item.get("mode") or "").strip()
    source = str(actual_item.get("target_resolution_source") or "").strip()
    return operation in {"attach_to_pending_followup", "draft_followup"} or source == "pending_followup_state"


def _matches_prior_optional_followup_attachment(actual_item: Any) -> bool:
    if not isinstance(actual_item, dict):
        return False
    operation = str(actual_item.get("operation") or actual_item.get("mode") or "").strip()
    source = str(actual_item.get("target_resolution_source") or "").strip()
    has_target_identity = any(
        actual_item.get(field) not in (None, "")
        for field in ("meal_thread_id", "meal_item_id", "target_object_id", "canonical_name")
    )
    return has_target_identity and (
        operation in {"attach_to_pending_followup", "refine_item", "same_item_refinement"}
        or source in {"pending_followup_state", "active_meal_view", "latest_active_meal"}
    )


def _matches_previous_meal_attachment(actual_item: Any) -> bool:
    if not isinstance(actual_item, dict):
        return False
    source = str(actual_item.get("target_resolution_source") or "").strip()
    return bool(actual_item.get("meal_thread_id")) and source in {
        "active_meal_view",
        "recent_committed_meal",
        "latest_active_meal",
        "tool_result",
        "tool_result_validated",
        "manager_target_proposal_validated",
    }


def _display(value: Any) -> str:
    if isinstance(value, bool):
        return str(value)
    if value is None:
        return "None"
    return str(value)


def _response_blockers(result: dict[str, Any]) -> list[str]:
    response = dict(result.get("response") or {})
    blockers: list[str] = []
    visible_text = str(
        response.get("assistant_message")
        or response.get("visible_text")
        or response.get("reply_text")
        or ""
    ).strip()
    if not visible_text:
        blockers.append("response.visible_text_missing")
    for forbidden_flag in (
        "internal_debug_words_present",
        "state_contradiction",
        "invented_nutrition_fact",
    ):
        if response.get(forbidden_flag) is True:
            blockers.append(f"response.{forbidden_flag}")
    if response.get("zh_tw_primary") is False:
        blockers.append("response.zh_tw_primary_false")
    return blockers


def _latency_blockers(result: dict[str, Any], case: dict[str, Any]) -> list[str]:
    latency = dict(result.get("latency") or {})
    budget = dict(case.get("latency_call_budget") or {})
    blockers: list[str] = []

    if latency.get("timeout_is_product_target") is not False:
        blockers.append("latency.timeout_is_product_target_not_false")

    for field in ("llm_calls", "tool_calls"):
        max_field = f"max_{field}"
        if field in latency and max_field in budget and int(latency[field]) > int(budget[max_field]):
            blockers.append(f"latency.{field}_exceeds_budget:{latency[field]}>{budget[max_field]}")
    return blockers


def _generalization_blockers(result: dict[str, Any]) -> list[str]:
    return fake_pass_generalization_blockers(dict(result.get("generalization") or {}))


__all__ = [
    "GOLDEN_SET_MANIFEST_PATH",
    "grade_golden_case_result",
    "load_golden_set_manifest",
]
