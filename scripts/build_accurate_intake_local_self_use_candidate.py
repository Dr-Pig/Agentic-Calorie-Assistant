from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SHELL_ARTIFACT_PATH = ROOT / "artifacts" / "accurate_intake_local_self_use_shell.json"
DEFAULT_OUTPUT_PATH = ROOT / "artifacts" / "accurate_intake_local_self_use_candidate.json"

NOT_CLAIMING = [
    "product_ready",
    "private_self_use_approved",
    "production_model_selected",
    "mutation_rollout_approved",
    "live_manager_ready",
    "web_ready",
    "production_db_ready",
]


def _base_packet(*, shell_artifact_path: Path) -> dict[str, Any]:
    return {
        "artifact_schema_version": "1.0",
        "candidate_id": "accurate_intake_local_self_use_candidate_v1",
        "claim_scope": "local_deterministic_self_use_candidate",
        "status": "blocked",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "shell_artifact_path": str(shell_artifact_path),
        "local_self_use_candidate_prepared": False,
        "private_self_use_approved": False,
        "live_manager_required": False,
        "production_selected": False,
        "product_readiness_claimed": False,
        "mutation_rollout_approved": False,
        "live_llm_invoked": False,
        "web_tavily_invoked": False,
        "production_db_used": False,
        "human_review_required_before_activation": True,
        "not_claiming": list(NOT_CLAIMING),
        "blockers": [],
        "evidence": {},
    }


def _read_json(path: Path) -> tuple[dict[str, Any] | None, list[str]]:
    if not path.exists():
        return None, ["shell_artifact_missing"]
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None, ["shell_artifact_invalid_json"]
    if not isinstance(parsed, dict):
        return None, ["shell_artifact_not_object"]
    return parsed, []


def _truthy(value: object) -> bool:
    return bool(value)


def _collect_blockers(shell_artifact: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if shell_artifact.get("status") != "pass":
        blockers.append("shell_artifact_not_passed")
    if shell_artifact.get("manager_mode") != "fixture":
        blockers.append("unsupported_manager_mode")
    if _truthy(shell_artifact.get("runner_inferred_semantics")):
        blockers.append("runner_inferred_semantics")
    if _truthy(shell_artifact.get("raw_text_routing_used")):
        blockers.append("raw_text_routing_used")
    if _truthy(shell_artifact.get("product_readiness_claimed")):
        blockers.append("shell_artifact_claimed_product_readiness")
    if _truthy(shell_artifact.get("private_self_use_approved")):
        blockers.append("shell_artifact_claimed_private_self_use")
    if _truthy(shell_artifact.get("live_llm_invoked")):
        blockers.append("shell_artifact_invoked_live_llm")
    if _truthy(shell_artifact.get("web_tavily_invoked")):
        blockers.append("shell_artifact_invoked_web_tavily")
    if _truthy(shell_artifact.get("production_db_used")):
        blockers.append("shell_artifact_used_production_db")

    operator_surface = dict(shell_artifact.get("operator_surface") or {})
    if operator_surface.get("read_only") is not True:
        blockers.append("operator_surface_not_read_only")
    same_truth = dict(operator_surface.get("same_truth") or {})
    if same_truth.get("status") != "pass":
        blockers.append("same_truth_not_passed")
    return blockers


def _evidence_from_shell(shell_artifact: dict[str, Any]) -> dict[str, Any]:
    operator_surface = dict(shell_artifact.get("operator_surface") or {})
    scenario_artifact = dict(shell_artifact.get("scenario_artifact") or {})
    same_truth = dict(operator_surface.get("same_truth") or {})
    today_summary = dict(operator_surface.get("today_summary") or {})
    return {
        "shell_artifact": {
            "shell_id": shell_artifact.get("shell_id"),
            "status": shell_artifact.get("status"),
            "scenario": shell_artifact.get("scenario"),
            "manager_mode": shell_artifact.get("manager_mode"),
            "runner_inferred_semantics": bool(shell_artifact.get("runner_inferred_semantics")),
            "raw_text_routing_used": bool(shell_artifact.get("raw_text_routing_used")),
            "live_llm_invoked": bool(shell_artifact.get("live_llm_invoked")),
        },
        "one_day_scenario": {
            "status": scenario_artifact.get("status"),
            "scenario_id": scenario_artifact.get("scenario_id"),
            "turn_count": scenario_artifact.get("turn_count")
            or len(operator_surface.get("chat_style_transcript") or []),
        },
        "operator_surface": {
            "read_only": operator_surface.get("read_only"),
            "truth_source": operator_surface.get("truth_source"),
            "today_summary": today_summary,
            "meal_thread_count": operator_surface.get("meal_thread_count"),
            "pending_draft_count": operator_surface.get("pending_draft_count"),
            "correction_history_count": len(operator_surface.get("correction_history") or []),
            "same_truth_status": same_truth.get("status"),
        },
    }


def build_local_self_use_candidate_packet(*, shell_artifact_path: Path = DEFAULT_SHELL_ARTIFACT_PATH) -> dict[str, Any]:
    packet = _base_packet(shell_artifact_path=shell_artifact_path)
    shell_artifact, read_blockers = _read_json(shell_artifact_path)
    if shell_artifact is None:
        packet["blockers"] = read_blockers
        return packet

    blockers = _collect_blockers(shell_artifact)
    packet["blockers"] = blockers
    packet["evidence"] = _evidence_from_shell(shell_artifact)
    if blockers:
        return packet

    packet["status"] = "prepared"
    packet["local_self_use_candidate_prepared"] = True
    return packet


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the Accurate Intake local self-use candidate packet.")
    parser.add_argument("--shell-artifact", default=str(DEFAULT_SHELL_ARTIFACT_PATH))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH))
    args = parser.parse_args(argv)

    packet = build_local_self_use_candidate_packet(shell_artifact_path=Path(args.shell_artifact))
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(packet, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(packet, ensure_ascii=False, indent=2))
    return 0 if packet["status"] == "prepared" else 1


if __name__ == "__main__":
    raise SystemExit(main())
