from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_accurate_intake_mvp_self_use_smoke import (
    build_one_day_self_use_reopen_report,
    build_one_day_self_use_scenario_wall_report,
)

DEFAULT_DB_PATH = ROOT / ".pytest_tmp_local" / "accurate_intake_self_use.sqlite"
DEFAULT_OUTPUT_PATH = ROOT / "artifacts" / "accurate_intake_local_self_use_shell.json"
SUPPORTED_SCENARIOS = {"one_day_v1"}
NOT_CLAIMING = [
    "product_ready",
    "rollout_ready",
    "live_llm_ready",
    "web_ready",
    "production_db_ready",
]


def _base_report(*, scenario: str, status: str, blockers: list[str]) -> dict[str, Any]:
    return {
        "artifact_schema_version": "1.0",
        "shell_id": "accurate_intake_local_self_use_shell_v1",
        "claim_scope": "local_deterministic_mvp_gate",
        "status": status,
        "blockers": list(blockers),
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "scenario": scenario,
        "manager_mode": "fixture",
        "runner_inferred_semantics": False,
        "raw_text_input_supported": False,
        "raw_text_routing_used": False,
        "product_readiness_claimed": False,
        "private_self_use_approved": False,
        "live_llm_invoked": False,
        "web_tavily_invoked": False,
        "production_db_used": False,
        "user_facing_rollout": False,
        "not_claiming": list(NOT_CLAIMING),
    }


def _chat_style_transcript(turns: list[dict[str, Any]]) -> list[dict[str, Any]]:
    transcript: list[dict[str, Any]] = []
    for turn in turns:
        manager_decision = dict(turn.get("manager_decision") or {})
        commit_result = dict(turn.get("commit_result") or {})
        state_after = dict(turn.get("state_after") or {})
        transcript.append(
            {
                "turn": turn.get("turn"),
                "turn_id": turn.get("turn_id"),
                "user_text": turn.get("raw_user_input"),
                "manager_intent": manager_decision.get("intent_type"),
                "workflow_effect": manager_decision.get("workflow_effect"),
                "final_action": manager_decision.get("final_action"),
                "mutation_applied": bool(commit_result.get("mutation_applied")),
                "today_summary_after": dict(state_after.get("today_summary") or {}),
            }
        )
    return transcript


def _operator_surface(*, debug_surface: dict[str, Any], turns: list[dict[str, Any]]) -> dict[str, Any]:
    model = dict(debug_surface.get("model") or {})
    meal_threads = list(model.get("meal_threads") or [])
    pending_drafts = list(model.get("pending_drafts") or [])
    correction_history = list(model.get("correction_history") or [])
    return {
        "view_id": "accurate_intake_local_self_use_operator_surface_v1",
        "read_only": True,
        "truth_source": "canonical_debug_read_model",
        "today_summary": dict(model.get("today_summary") or {}),
        "meal_threads": meal_threads,
        "meal_thread_count": len(meal_threads),
        "pending_drafts": pending_drafts,
        "pending_draft_count": len(pending_drafts),
        "correction_history": correction_history,
        "same_truth": dict(model.get("same_truth") or {}),
        "chat_style_transcript": _chat_style_transcript(turns),
    }


def build_local_self_use_shell_report(
    *,
    scenario: str,
    db_path: Path = DEFAULT_DB_PATH,
    reset_db: bool = True,
) -> dict[str, Any]:
    if scenario not in SUPPORTED_SCENARIOS:
        report = _base_report(
            scenario=scenario,
            status="blocked",
            blockers=["manager_fixture_missing_for_scenario"],
        )
        report.update(
            {
                "mutation_applied": False,
                "operator_surface": None,
                "db_mode": "not_opened",
            }
        )
        return report

    if not reset_db and db_path.exists():
        reopen = build_one_day_self_use_reopen_report(db_path=db_path)
        report = _base_report(
            scenario=scenario,
            status=str(reopen.get("status") or "fail"),
            blockers=[str(item) for item in reopen.get("blockers", [])],
        )
        report.update(
            {
                "mutation_applied": False,
                "db_mode": "keep_existing_local_sqlite",
                "scenario_artifact": reopen,
                "operator_surface": _operator_surface(
                    debug_surface=dict(reopen.get("debug_surface") or {}),
                    turns=[],
                ),
            }
        )
        return report

    scenario_report = build_one_day_self_use_scenario_wall_report(db_path=db_path, reset_db=reset_db)
    report = _base_report(
        scenario=scenario,
        status=str(scenario_report.get("status") or "fail"),
        blockers=[str(item) for item in scenario_report.get("blockers", [])],
    )
    report.update(
        {
            "mutation_applied": True,
            "db_mode": "reset_local_sqlite" if reset_db else "create_local_sqlite",
            "scenario_artifact": scenario_report,
            "operator_surface": _operator_surface(
                debug_surface=dict(scenario_report.get("final_debug_surface") or {}),
                turns=list(scenario_report.get("turns") or []),
            ),
        }
    )
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the Accurate Intake local self-use operator shell.")
    parser.add_argument("--scenario", default="one_day_v1")
    parser.add_argument("--db-path", default=str(DEFAULT_DB_PATH))
    reset_group = parser.add_mutually_exclusive_group()
    reset_group.add_argument("--reset-db", action="store_true", default=True)
    reset_group.add_argument("--keep-db", action="store_true")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH))
    parser.add_argument("--print-debug-surface", action="store_true")
    args = parser.parse_args(argv)

    reset_db = not bool(args.keep_db)
    report = build_local_self_use_shell_report(
        scenario=args.scenario,
        db_path=Path(args.db_path),
        reset_db=reset_db,
    )
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
