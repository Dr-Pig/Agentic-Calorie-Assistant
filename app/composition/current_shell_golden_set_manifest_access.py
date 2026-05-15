from __future__ import annotations

from typing import Any


FAKE_PASS_GENERALIZATION_FLAGS = (
    "exact_utterance_only_pass",
    "keyword_or_fixture_shortcut_used",
    "pre_manager_estimability_shortcut_used",
    "pre_manager_websearch_routing_used",
    "deterministic_search_routing_used",
    "case_id_or_fixture_label_routing_used",
    "raw_user_input_semantic_oracle_used",
    "runner_inferred_workflow_effect",
)


def golden_set_cases(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    cases = [_case for _case in list(manifest.get("cases") or []) if isinstance(_case, dict)]
    websearch_extension = manifest.get("websearch_extension")
    if isinstance(websearch_extension, dict):
        cases.extend(
            _case
            for _case in list(websearch_extension.get("cases") or [])
            if isinstance(_case, dict)
        )
    return cases


def golden_case_by_id(manifest: dict[str, Any], case_id: str) -> dict[str, Any]:
    for case in golden_set_cases(manifest):
        if case.get("case_id") == case_id:
            return dict(case)
    return {}


def fake_pass_generalization_blockers(generalization: dict[str, Any]) -> list[str]:
    return [
        f"generalization.{flag}"
        for flag in FAKE_PASS_GENERALIZATION_FLAGS
        if generalization.get(flag) is True
    ]


__all__ = [
    "FAKE_PASS_GENERALIZATION_FLAGS",
    "fake_pass_generalization_blockers",
    "golden_case_by_id",
    "golden_set_cases",
]
