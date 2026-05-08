from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.runtime.agent.manager_system_prompt import (  # noqa: E402
    SINGLE_MANAGER_SYSTEM_PROMPT,
    SINGLE_MANAGER_SYSTEM_PROMPT_VERSION,
)
from app.shared.infra.json_artifacts import write_json_artifact  # noqa: E402


DEFAULT_OUTPUT_PATH = ROOT / "artifacts" / "accurate_intake_rt14g_response_language_prompt_polish.json"
DYNAMIC_REQUEST_MARKERS = (
    "raw_user_input",
    "user_id",
    "local_date",
    "current_turn_context",
    "manager_context_packet",
    "FoodDB packet",
    "tool_results:",
)


def build_rt14g_response_language_prompt_polish_artifact(
    *,
    output_path: Path | None = None,
) -> dict[str, Any]:
    cases = [
        _user_language_policy_case(),
        _debug_surface_suppression_case(),
        _macro_visibility_policy_case(),
        _blocking_followup_policy_case(),
        _no_plan_budget_honesty_policy_case(),
        _prompt_cache_static_prefix_policy_case(),
    ]
    blockers = [f"{case['case_id']}.{blocker}" for case in cases for blocker in case["blockers"]]
    resolved_output_path = Path(output_path) if output_path is not None else DEFAULT_OUTPUT_PATH
    return {
        "artifact_schema_version": "1.0",
        "artifact_name": resolved_output_path.name,
        "artifact_path": str(resolved_output_path),
        "artifact_type": "accurate_intake_rt14g_response_language_prompt_polish",
        "claim_scope": "response_language_prompt_policy_contract",
        "launch_scope": "current_shell_v1",
        "producer_track": "CurrentShell/ManagerRuntime",
        "target_manager_runtime_gate": "rt14g_response_language_prompt_polish",
        "pass_type": "contract",
        "runtime_backed": False,
        "live_llm_invoked": False,
        "production_db_used": False,
        "fooddb_truth_updated": False,
        "supports_journeys": ["B", "C", "D", "E", "J", "K"],
        "status": _status(blockers),
        "blockers": blockers,
        "summary": {
            "case_count": len(cases),
            "passed_case_count": sum(1 for case in cases if case["status"] == "pass"),
            "system_prompt_version": SINGLE_MANAGER_SYSTEM_PROMPT_VERSION,
            "prompt_cache_safe_static_policy": _dynamic_request_markers_absent(),
        },
        "cases": cases,
        "best_practice_basis": {
            "prompt_versioning_required": True,
            "stable_prefix_dynamic_suffix_preserved": True,
            "eval_required_after_prompt_change": True,
            "structured_output_schema_still_primary": True,
        },
        "non_claims": {
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
            "whole_product_mvp_ready": False,
            "production_selected": False,
            "mutation_rollout_approved": False,
        },
    }


def _user_language_policy_case() -> dict[str, Any]:
    required = (
        "answer_contract.reply_text is visible to the user",
        "Match the user's language",
        "Traditional Chinese",
        "zh-TW",
    )
    return _case(
        "user_language_policy",
        _missing(required),
        {"required_markers": list(required), "system_prompt_version": SINGLE_MANAGER_SYSTEM_PROMPT_VERSION},
    )


def _debug_surface_suppression_case() -> dict[str, Any]:
    required = (
        "Do not expose debug",
        "trace",
        "provider",
        "request_id",
        "tool_calls",
        "internal schema names",
    )
    return _case("debug_surface_suppression_policy", _missing(required), {"required_markers": list(required)})


def _macro_visibility_policy_case() -> dict[str, Any]:
    required = (
        "Mention macros only when",
        "show_macro",
        "visible macro facts",
        "macro data is insufficient",
    )
    return _case("macro_visibility_policy", _missing(required), {"required_markers": list(required)})


def _blocking_followup_policy_case() -> dict[str, Any]:
    required = (
        "State logged, not logged, or updated status plainly",
        "Ask at most one necessary follow-up question",
        "blocking cases",
    )
    return _case("blocking_followup_policy", _missing(required), {"required_markers": list(required)})


def _no_plan_budget_honesty_policy_case() -> dict[str, Any]:
    required = (
        "When there is no active plan or the read model has no daily target",
        "do not describe missing target or remaining budget as 0",
        "daily_target_kcal or remaining_kcal is null",
        "answer consumed/logged state only from read-model facts",
    )
    return _case("no_plan_budget_honesty_policy", _missing(required), {"required_markers": list(required)})


def _prompt_cache_static_prefix_policy_case() -> dict[str, Any]:
    blockers: list[str] = []
    if SINGLE_MANAGER_SYSTEM_PROMPT_VERSION != "v10":
        blockers.append("system_prompt_version_not_v10")
    if not _dynamic_request_markers_absent():
        blockers.append("dynamic_request_marker_in_system_prompt")
    if "User-facing reply policy:" not in SINGLE_MANAGER_SYSTEM_PROMPT:
        blockers.append("stable_reply_policy_missing")
    if "think step by step" in SINGLE_MANAGER_SYSTEM_PROMPT.lower():
        blockers.append("chain_of_thought_prompt_present")
    return _case(
        "prompt_cache_static_prefix_policy",
        blockers,
        {
            "dynamic_request_markers_absent": _dynamic_request_markers_absent(),
            "stable_policy_in_system_prompt": "User-facing reply policy:" in SINGLE_MANAGER_SYSTEM_PROMPT,
            "chain_of_thought_prompt_absent": "think step by step" not in SINGLE_MANAGER_SYSTEM_PROMPT.lower(),
        },
    )


def _missing(required_markers: tuple[str, ...]) -> list[str]:
    return [
        f"missing_marker:{marker}"
        for marker in required_markers
        if marker not in SINGLE_MANAGER_SYSTEM_PROMPT
    ]


def _dynamic_request_markers_absent() -> bool:
    return all(marker not in SINGLE_MANAGER_SYSTEM_PROMPT for marker in DYNAMIC_REQUEST_MARKERS)


def _case(case_id: str, blockers: list[str], observed: dict[str, Any]) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "status": _status(blockers),
        "blockers": blockers,
        "observed": observed,
    }


def _status(blockers: list[str]) -> str:
    return "pass" if not blockers else "fail"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the RT14g response language prompt polish artifact.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    args = parser.parse_args(argv)
    artifact = build_rt14g_response_language_prompt_polish_artifact(output_path=args.output)
    write_json_artifact(args.output, artifact)
    print(json.dumps(artifact, ensure_ascii=False, indent=2))
    return 0 if artifact["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
