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
    "external_assertion_override_used",
)


SUITE_SCOPES = ("core", "holdout", "closeout", "websearch", "all_defined", "explicit")


def golden_set_cases(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    return golden_set_cases_for_scope(manifest, "all_defined")


def golden_set_cases_for_scope(manifest: dict[str, Any], suite_scope: str) -> list[dict[str, Any]]:
    core_cases = golden_set_core_cases(manifest)
    holdout_cases = golden_set_holdout_cases(manifest)
    websearch_cases = golden_set_websearch_cases(manifest)
    if suite_scope == "core":
        return core_cases
    if suite_scope == "holdout":
        return holdout_cases
    if suite_scope == "closeout":
        return [*core_cases, *holdout_cases]
    if suite_scope == "websearch":
        return websearch_cases
    if suite_scope in {"all_defined", "explicit"}:
        return [*core_cases, *holdout_cases, *websearch_cases]
    raise ValueError(f"unsupported golden set suite_scope: {suite_scope}")


def golden_set_core_cases(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    return [_case for _case in list(manifest.get("cases") or []) if isinstance(_case, dict)]


def golden_set_holdout_cases(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    holdout_extension = manifest.get("holdout_extension")
    if not isinstance(holdout_extension, dict):
        return []
    return [_case for _case in list(holdout_extension.get("cases") or []) if isinstance(_case, dict)]


def golden_set_websearch_cases(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    websearch_extension = manifest.get("websearch_extension")
    if not isinstance(websearch_extension, dict):
        return []
    return [_case for _case in list(websearch_extension.get("cases") or []) if isinstance(_case, dict)]


def golden_set_suite_inventory(manifest: dict[str, Any]) -> dict[str, Any]:
    core_count = len(golden_set_core_cases(manifest))
    holdout_count = len(golden_set_holdout_cases(manifest))
    websearch_count = len(golden_set_websearch_cases(manifest))
    websearch_extension = manifest.get("websearch_extension") if isinstance(manifest.get("websearch_extension"), dict) else {}
    return {
        "core_case_count": core_count,
        "holdout_case_count": holdout_count,
        "websearch_extension_case_count": websearch_count,
        "core_closeout_case_count": core_count,
        "self_use_closeout_case_count": core_count + holdout_count,
        "total_defined_case_count": core_count + holdout_count + websearch_count,
        "default_runner_scope": str(dict(manifest.get("suite_inventory") or {}).get("default_runner_scope") or "core"),
        "default_replay_scope": str(dict(manifest.get("suite_inventory") or {}).get("default_replay_scope") or "closeout"),
        "websearch_extension_blocking": bool(websearch_extension.get("core_closeout_blocking")),
        "websearch_extension_status": str(websearch_extension.get("status") or ""),
    }


def assert_golden_set_suite_inventory(manifest: dict[str, Any]) -> None:
    declared = dict(manifest.get("suite_inventory") or {})
    observed = golden_set_suite_inventory(manifest)
    if declared != observed:
        raise ValueError(f"golden set suite_inventory mismatch: declared={declared!r} observed={observed!r}")


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
    "SUITE_SCOPES",
    "assert_golden_set_suite_inventory",
    "fake_pass_generalization_blockers",
    "golden_case_by_id",
    "golden_set_cases_for_scope",
    "golden_set_core_cases",
    "golden_set_holdout_cases",
    "golden_set_cases",
    "golden_set_suite_inventory",
    "golden_set_websearch_cases",
]
