from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


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
    case = _case_by_id(golden_manifest, case_id)
    blockers: list[str] = []
    warnings: list[str] = []

    if not case:
        return _grade_result(case_id=case_id, blockers=[f"case_id_unknown:{case_id}"], warnings=[])

    blockers.extend(_fixture_decision_blockers(result, golden_manifest))
    blockers.extend(_trace_layer_blockers(result, case, golden_manifest))
    blockers.extend(_expected_mapping_blockers("runtime", result.get("runtime"), case.get("expected_runtime")))
    blockers.extend(_expected_mapping_blockers("ui", result.get("ui"), case.get("ui_assertions")))
    blockers.extend(_response_blockers(result))
    blockers.extend(_latency_blockers(result, case))
    blockers.extend(_dogfood_trace_blockers(result, case))
    blockers.extend(_generalization_blockers(result))

    return _grade_result(case_id=case_id, blockers=blockers, warnings=warnings)


def _case_by_id(manifest: dict[str, Any], case_id: str) -> dict[str, Any]:
    for case in list(manifest.get("cases") or []):
        if isinstance(case, dict) and case.get("case_id") == case_id:
            return dict(case)
    return {}


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
        if actual_item != expected_item:
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


def _dogfood_trace_blockers(result: dict[str, Any], case: dict[str, Any]) -> list[str]:
    trace = dict(result.get("dogfood_trace") or {})
    expected = dict(case.get("dogfood_trace") or {})
    blockers: list[str] = []
    if expected.get("trace_id_required") is True and not str(trace.get("trace_id") or "").strip():
        blockers.append("dogfood_trace.trace_id_missing")
    if expected.get("feedback_links_to_trace") is True and trace.get("feedback_links_to_trace") is not True:
        blockers.append("dogfood_trace.feedback_links_to_trace_not_true")
    if (
        expected.get("correlates_ui_runtime_read_model_response") is True
        and trace.get("correlates_ui_runtime_read_model_response") is not True
    ):
        blockers.append("dogfood_trace.correlates_ui_runtime_read_model_response_not_true")
    return blockers


def _generalization_blockers(result: dict[str, Any]) -> list[str]:
    generalization = dict(result.get("generalization") or {})
    blockers: list[str] = []
    for forbidden_flag in ("exact_utterance_only_pass", "keyword_or_fixture_shortcut_used"):
        if generalization.get(forbidden_flag) is True:
            blockers.append(f"generalization.{forbidden_flag}")
    return blockers


__all__ = [
    "GOLDEN_SET_MANIFEST_PATH",
    "grade_golden_case_result",
    "load_golden_set_manifest",
]
