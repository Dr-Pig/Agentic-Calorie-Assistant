from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.database import SessionLocal, init_db
from app.routes import planner_provider, primary_provider
from app.schemas import EstimateRequest
from app.usecases.text_meal import run_text_meal_canary
from scripts.audit_io_guard import enforce_file_backed_audit_input, load_json_audit_fixture


PACK_PATH = ROOT / "docs" / "quality" / "benchmarks" / "intake" / "multi_turn" / "turn2_hybrid_replay_pack_v1.json"
LOG_ROOT = ROOT / ".logs" / "turn2_hybrid_replay"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run turn-2 hybrid replay cases.")
    parser.add_argument("--case-id", required=True, help="Case id from turn2_hybrid_replay_pack_v1.json")
    parser.add_argument("--mode", choices=["turn1", "turn2", "full"], default="full")
    return parser


def _provider_ready() -> bool:
    return bool(primary_provider.readiness().get("configured")) and bool(planner_provider.readiness().get("configured"))


def _load_case(case_id: str) -> dict[str, Any]:
    payload = load_json_audit_fixture(path=PACK_PATH, audit_name="turn2_hybrid_replay")
    for case in payload.get("cases", []):
        if str(case.get("case_id")) == case_id:
            return dict(case)
    raise SystemExit(f"Unknown case_id: {case_id}")


def _case_dir(case_id: str) -> Path:
    path = LOG_ROOT / case_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def _build_run_user_id(case_id: str) -> str:
    return f"turn2-hybrid-{case_id}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"


def _save_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def _latest_turn1_artifact(case_id: str) -> Path | None:
    path = _case_dir(case_id)
    files = sorted(path.glob("turn1_*.json"))
    return files[-1] if files else None


def _load_artifact(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


async def _run_turn(case: dict[str, Any], *, turn_label: str, text: str, user_id: str) -> dict[str, Any]:
    db = SessionLocal()
    request_id = f"{case['case_id']}-{turn_label}-{datetime.now(timezone.utc).strftime('%H%M%S')}"
    try:
        payload = await run_text_meal_canary(
            EstimateRequest(text=text, allow_search=False, user_id=user_id),
            provider=primary_provider,
            primary_provider=primary_provider,
            planner_provider=planner_provider,
            request_id=request_id,
            db=db,
        )
        return {
            "case_id": case["case_id"],
            "turn_id": turn_label,
            "user_id": user_id,
            "request_id": request_id,
            "input": text,
            "saved_at_utc": datetime.now(timezone.utc).isoformat(),
            "payload": payload.model_dump(mode="json"),
            "trace_contract": payload.trace_contract,
            "llm_traces": payload.llm_traces,
            "persistence_decision": (payload.trace_contract or {}).get("persistence_decision"),
        }
    finally:
        db.close()


def _build_summary(case: dict[str, Any], *, user_id: str, turn1_path: Path, turn2_path: Path, turn1: dict[str, Any], turn2: dict[str, Any]) -> dict[str, Any]:
    first_persist = dict(turn1.get("persistence_decision") or {})
    second_persist = dict(turn2.get("persistence_decision") or {})
    same_intake_attached = second_persist.get("parent_log_id") == first_persist.get("persisted_log_id")
    turn2_has_commit = bool(second_persist.get("canonical_commit"))
    turn2_status = second_persist.get("status")
    expected_persistence = dict(case.get("expected_persistence") or {})
    forbidden_outcomes = list(case.get("forbidden_outcomes") or [])
    return {
        "case_id": case["case_id"],
        "lane": case["lane"],
        "lane_family": case.get("lane_family"),
        "user_id": user_id,
        "turn1_artifact": str(turn1_path.relative_to(ROOT)),
        "turn2_artifact": str(turn2_path.relative_to(ROOT)),
        "turn1_status": first_persist.get("status"),
        "turn2_status": turn2_status,
        "turn2_parent_log_id": second_persist.get("parent_log_id"),
        "turn1_persisted_log_id": first_persist.get("persisted_log_id"),
        "same_intake_attached": same_intake_attached,
        "canonical_commit_present_on_turn2": turn2_has_commit,
        "expected_turn1_lane": case.get("expected_turn1_lane"),
        "expected_turn2_outcome": case.get("expected_turn2_outcome"),
        "expected_attachment": case.get("expected_attachment"),
        "expected_persistence": expected_persistence,
        "forbidden_outcomes": forbidden_outcomes,
        "matched_expected_attachment": same_intake_attached == (case.get("expected_attachment") == "same_intake_thread"),
        "matched_expected_turn2_status": (
            turn2_status == expected_persistence.get("turn2_status")
            if expected_persistence.get("turn2_status") is not None
            else None
        ),
        "matched_expected_commit_presence": (
            turn2_has_commit == bool(expected_persistence.get("canonical_commit_required"))
            if "canonical_commit_required" in expected_persistence
            else None
        ),
        "forbidden_outcome_hits": [
            outcome
            for outcome in forbidden_outcomes
            if (
                (outcome == "new_meal_thread" and not same_intake_attached)
                or (outcome == "turn2_draft_unresolved" and turn2_status == "draft_unresolved")
                or (outcome == "missing_canonical_commit" and not turn2_has_commit)
            )
        ],
    }


async def _run_full(case: dict[str, Any]) -> int:
    if not _provider_ready():
        print("provider_not_configured")
        return 2

    init_db()
    user_id = _build_run_user_id(case["case_id"])
    case_dir = _case_dir(case["case_id"])

    turn1 = await _run_turn(case, turn_label="turn1", text=str(case["turn1_input"]), user_id=user_id)
    turn1_path = case_dir / f"turn1_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    _save_json(turn1_path, turn1)

    turn2 = await _run_turn(case, turn_label="turn2", text=str(case["turn2_input"]), user_id=user_id)
    turn2_path = case_dir / f"turn2_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    _save_json(turn2_path, turn2)

    summary = _build_summary(case, user_id=user_id, turn1_path=turn1_path, turn2_path=turn2_path, turn1=turn1, turn2=turn2)
    summary_path = case_dir / f"summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    _save_json(summary_path, summary)
    print(summary_path)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


async def _run_single_stage(case: dict[str, Any], mode: str) -> int:
    if not _provider_ready():
        print("provider_not_configured")
        return 2

    init_db()
    user_id = _build_run_user_id(case["case_id"])
    case_dir = _case_dir(case["case_id"])

    if mode == "turn1":
        artifact = await _run_turn(case, turn_label="turn1", text=str(case["turn1_input"]), user_id=user_id)
        path = case_dir / f"turn1_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        _save_json(path, artifact)
        print(path)
        return 0

    prior = _latest_turn1_artifact(case["case_id"])
    if prior is None:
        print("missing_turn1_artifact")
        return 3
    prior_artifact = _load_artifact(prior)
    user_id = str(prior_artifact.get("user_id") or user_id)
    artifact = await _run_turn(case, turn_label="turn2", text=str(case["turn2_input"]), user_id=user_id)
    path = case_dir / f"turn2_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    _save_json(path, artifact)
    print(path)
    return 0


def main() -> int:
    enforce_file_backed_audit_input(audit_name="turn2_hybrid_replay")
    args = _parser().parse_args()
    case = _load_case(args.case_id)
    if args.mode == "full":
        return asyncio.run(_run_full(case))
    return asyncio.run(_run_single_stage(case, args.mode))


if __name__ == "__main__":
    raise SystemExit(main())
