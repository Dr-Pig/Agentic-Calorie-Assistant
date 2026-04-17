from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.application.rescue_chat_surface import apply_rescue_chat_action, build_rescue_chat_surface
from app.models import Base, LedgerEntryRecord, ProposalContainerRecord, ProposalOptionRecord, User
from scripts.audit_io_guard import enforce_file_backed_audit_input, load_json_audit_fixture


PACK_PATH = ROOT / "docs" / "quality" / "benchmarks" / "rescue" / "rescue_executable_action_pack_v1.json"
SOURCE_PACK_PATH = ROOT / "docs" / "quality" / "benchmarks" / "rescue" / "rescue_official_canonical_pack_v1.json"
LOG_ROOT = ROOT / ".logs" / "rescue_executable_action"
DEFAULT_BASE_LOCAL_DATE = "2026-04-15"

ACTION_TO_DISPOSITION = {
    "accept_rescue_plan": "accept",
    "reject_rescue_plan": "reject",
    "defer_rescue_plan": "defer",
    "extend_rescue_plan": "adjust",
    "shorten_rescue_plan": "adjust",
    "explain_rescue_plan": "answer_only",
}
ACTION_TO_ADJUST_DIRECTION = {
    "extend_rescue_plan": "longer",
    "shorten_rescue_plan": "shorter",
}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run rescue executable action pack against the local rescue runtime.")
    parser.add_argument("--case-id", default=None, help="Optional executable_case_id filter.")
    return parser


def load_executable_pack() -> dict[str, Any]:
    return load_json_audit_fixture(path=PACK_PATH, audit_name="rescue_executable_action")


def load_source_pack() -> dict[str, Any]:
    return load_json_audit_fixture(path=SOURCE_PACK_PATH, audit_name="rescue_official_canonical")


def _selected_cases(payload: dict[str, Any], *, case_id: str | None) -> list[dict[str, Any]]:
    cases = [dict(case) for case in payload.get("cases", [])]
    if case_id is None:
        return cases
    for case in cases:
        if str(case.get("executable_case_id")) == case_id:
            return [case]
    raise SystemExit(f"Unknown executable_case_id: {case_id}")


def _source_case_map(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(case["case_id"]): dict(case)
        for case in payload.get("cases", [])
        if case.get("case_id") is not None
    }


def _session() -> Session:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    testing_session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)
    return testing_session()


def _user(db: Session, *, case_id: str) -> User:
    user = User(user_id=f"rescue-executable-{case_id}")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _build_overlay_days(*, recommended_days: int, daily_kcal_adjustment: int, base_budget_kcal: int) -> list[dict[str, Any]]:
    start = datetime.fromisoformat(f"{DEFAULT_BASE_LOCAL_DATE}T00:00:00")
    days: list[dict[str, Any]] = []
    for index in range(recommended_days):
        local_date = (start + timedelta(days=index)).date().isoformat()
        days.append(
            {
                "local_date": local_date,
                "proposed_rescue_overlay_kcal": -daily_kcal_adjustment,
                "base_budget_kcal": base_budget_kcal,
                "calibration_adjustment_kcal": 0,
                "max_daily_rescue_compression_kcal": daily_kcal_adjustment,
                "candidate_effective_budget_kcal": base_budget_kcal - daily_kcal_adjustment,
                "safety_floor_kcal": 1500,
                "compression_ratio": round(daily_kcal_adjustment / max(base_budget_kcal, 1), 4),
                "viability": "viable",
                "within_compression_cap": True,
                "meets_safety_floor": True,
            }
        )
    return days


def _seed_open_rescue_proposal(db: Session, *, user: User, proposal_seed: dict[str, Any]) -> ProposalContainerRecord:
    proposal_container_id = int(proposal_seed["proposal_container_id"])
    proposal_status = str(proposal_seed.get("proposal_status") or "open")
    recommended_days = max(1, int(proposal_seed.get("recommended_days") or 1))
    daily_kcal_adjustment = max(0, int(proposal_seed.get("daily_kcal_adjustment") or 0))
    target_recovery_kcal = recommended_days * daily_kcal_adjustment
    base_budget_kcal = max(1, math.ceil(daily_kcal_adjustment / 0.15)) if daily_kcal_adjustment > 0 else 1800
    overlay_days = _build_overlay_days(
        recommended_days=recommended_days,
        daily_kcal_adjustment=daily_kcal_adjustment,
        base_budget_kcal=base_budget_kcal,
    )

    proposal = ProposalContainerRecord(
        id=proposal_container_id,
        user_id=user.id,
        proposal_type="rescue",
        proposal_status=proposal_status,
        metadata_json={
            "proposal_posture": "proposal",
            "recommended_rescue_family": "short_horizon_spread",
            "target_recovery_kcal": target_recovery_kcal,
            "trigger_summary": {
                "triggered": True,
                "trigger_reason": "seeded from executable action pack",
                "overshoot_kcal": target_recovery_kcal,
                "current_local_date": DEFAULT_BASE_LOCAL_DATE,
                "relevant_ledger_summary": {
                    "effective_budget_kcal": base_budget_kcal,
                    "consumed_kcal": base_budget_kcal + target_recovery_kcal,
                },
            },
        },
    )
    db.add(proposal)
    db.commit()
    db.refresh(proposal)

    option = ProposalOptionRecord(
        proposal_container_id=proposal.id,
        option_type="short_horizon_spread",
        option_label="Seeded rescue option",
        option_summary="Seeded from rescue executable action pack",
        rank_order=1,
        is_primary=True,
        effect_payload_json={
            "activation_mode": "today_lunch",
            "horizon_days": recommended_days,
            "daily_kcal_adjustments": [-daily_kcal_adjustment for _ in range(recommended_days)],
            "confidence": "high",
            "guardrail_summary": {"seeded": True},
            "safety_floor_kcal": 1500,
            "recovery_viability": "viable",
            "overlay_days": overlay_days,
        },
    )
    db.add(option)
    db.commit()
    db.refresh(option)

    proposal.top_option_id = option.id
    db.commit()
    db.refresh(proposal)
    return proposal


def _proposal_snapshot(record: ProposalContainerRecord) -> dict[str, Any]:
    return {
        "proposal_status": record.proposal_status,
        "top_option_id": record.top_option_id,
        "metadata": dict(record.metadata_json or {}),
        "accepted_at": record.accepted_at.isoformat() if record.accepted_at is not None else None,
    }


def _resolve_reason(case: dict[str, Any], source_case: dict[str, Any]) -> str | None:
    runtime_action = dict(case.get("runtime_action") or {})
    strategy = str(runtime_action.get("reason_strategy") or "").strip()
    if strategy not in {"reuse_source_utterance", "optional_reuse_source_utterance"}:
        return None
    utterance = str(source_case.get("utterance") or "").strip()
    return utterance or None


def _derive_observed_runtime_outcome(
    *,
    case: dict[str, Any],
    before_snapshot: dict[str, Any],
    after_snapshot: dict[str, Any],
    result: Any,
) -> dict[str, Any]:
    runtime_action = dict(case.get("runtime_action") or {})
    execution_mode = str(case.get("execution_mode") or "")
    action = str(runtime_action.get("action") or "")
    proposal_status_before = str(before_snapshot.get("proposal_status") or "")
    proposal_status_after = str(after_snapshot.get("proposal_status") or "")
    metadata_before = dict(before_snapshot.get("metadata") or {})
    metadata_after = dict(after_snapshot.get("metadata") or {})
    metadata_changed = metadata_before != metadata_after
    status_changed = proposal_status_before != proposal_status_after
    writeback = dict(getattr(result, "writeback", None) or {})
    writeback_status = writeback.get("status")

    disposition = "answer_only"
    workflow_effect = "answer_current_object"
    persistence_mode = "surface_only"

    if execution_mode == "surface_only":
        disposition = "answer_only"
        workflow_effect = "answer_current_object"
    else:
        disposition = ACTION_TO_DISPOSITION.get(action, "answer_only")
        if action == "accept_rescue_plan" and proposal_status_after == "accepted" and writeback_status == "applied":
            workflow_effect = "accept_and_apply_current_proposal"
            persistence_mode = "persisted"
        elif action == "reject_rescue_plan" and proposal_status_after == "rejected":
            workflow_effect = "close_current_proposal"
            persistence_mode = "persisted"
        elif action == "defer_rescue_plan" and proposal_status_after == "deferred_pending_reminder":
            workflow_effect = "defer_current_proposal"
            persistence_mode = "persisted"
        elif action in ACTION_TO_ADJUST_DIRECTION:
            workflow_effect = "mutate_current_proposal" if status_changed or metadata_changed else "answer_current_object"
            persistence_mode = "persisted" if workflow_effect == "mutate_current_proposal" else "surface_only"
        elif action == "explain_rescue_plan":
            workflow_effect = "answer_current_object"

    return {
        "target_object_type": "proposal",
        "target_workflow_family": "rescue",
        "disposition": disposition,
        "workflow_effect": workflow_effect,
        "adjust_direction": ACTION_TO_ADJUST_DIRECTION.get(action),
        "persistence_mode": persistence_mode,
        "proposal_status_before": proposal_status_before,
        "proposal_status_after": proposal_status_after,
        "proposal_metadata_changed": metadata_changed,
        "proposal_status_changed": status_changed,
        "writeback_status": writeback_status,
    }


def _response_snapshot(result: Any) -> dict[str, Any]:
    response = result.response
    top_option = response.top_option
    return {
        "surfaced": response.surfaced,
        "recommended_days": response.recommended_days,
        "daily_kcal_adjustment": response.daily_kcal_adjustment,
        "overshoot_kcal": response.overshoot_kcal,
        "ui_hints": dict(response.ui_hints or {}),
        "top_option_id": getattr(top_option, "proposal_option_id", None),
        "reply_text": response.reply_text,
    }


def _db_snapshot(db: Session, *, proposal_container_id: int) -> dict[str, Any]:
    proposal = db.get(ProposalContainerRecord, proposal_container_id)
    if proposal is None:
        raise ValueError(f"proposal_container_id={proposal_container_id} not found after run")
    ledger_entries = db.execute(
        select(LedgerEntryRecord)
        .where(LedgerEntryRecord.source_id == proposal_container_id)
        .order_by(LedgerEntryRecord.id.asc())
    ).scalars().all()
    return {
        "proposal_status": proposal.proposal_status,
        "accepted_at": proposal.accepted_at.isoformat() if proposal.accepted_at is not None else None,
        "metadata": dict(proposal.metadata_json or {}),
        "ledger_entry_count": len(ledger_entries),
        "ledger_entry_deltas": [entry.delta_kcal for entry in ledger_entries],
        "ledger_entry_source_types": [entry.source_type for entry in ledger_entries],
    }


def _oracle(case: dict[str, Any], observed: dict[str, Any]) -> dict[str, Any]:
    expected = dict(case.get("expected_runtime_outcome") or {})
    checks = {
        "matched_target_object_type": observed.get("target_object_type") == expected.get("expected_target_object_type"),
        "matched_target_workflow_family": observed.get("target_workflow_family") == expected.get("expected_target_workflow_family"),
        "matched_disposition": observed.get("disposition") == expected.get("expected_disposition"),
        "matched_workflow_effect": observed.get("workflow_effect") == expected.get("expected_workflow_effect"),
        "matched_adjust_direction": (
            True
            if expected.get("expected_adjust_direction") in (None, "")
            else observed.get("adjust_direction") == expected.get("expected_adjust_direction")
        ),
    }
    checks["passed"] = all(bool(value) for value in checks.values())
    return checks


def run_case(case: dict[str, Any], *, source_case_map: dict[str, dict[str, Any]]) -> dict[str, Any]:
    source_case_id = str(case["source_official_case_id"])
    source_case = source_case_map[source_case_id]
    db = _session()
    try:
        user = _user(db, case_id=str(case["executable_case_id"]))
        proposal = _seed_open_rescue_proposal(db, user=user, proposal_seed=dict(case["proposal_seed"]))
        before_snapshot = _proposal_snapshot(proposal)

        execution_mode = str(case.get("execution_mode") or "")
        runtime_action = dict(case.get("runtime_action") or {})
        resolved_reason = _resolve_reason(case, source_case)

        if execution_mode == "surface_only":
            result = build_rescue_chat_surface(
                db,
                user_id=user.id,
                mode=str(runtime_action.get("mode") or "reactive_explicit_rescue_request"),
            )
        elif execution_mode == "chat_action":
            result = apply_rescue_chat_action(
                db,
                user_id=user.id,
                action=str(runtime_action["action"]),
                reason=resolved_reason,
            )
        else:
            raise ValueError(f"unsupported execution_mode: {execution_mode}")

        after_proposal = db.get(ProposalContainerRecord, proposal.id)
        if after_proposal is None:
            raise ValueError(f"proposal_container_id={proposal.id} missing after execution")
        after_snapshot = _proposal_snapshot(after_proposal)
        observed = _derive_observed_runtime_outcome(
            case=case,
            before_snapshot=before_snapshot,
            after_snapshot=after_snapshot,
            result=result,
        )
        oracle = _oracle(case, observed)
        return {
            "executable_case_id": case["executable_case_id"],
            "source_official_case_id": source_case_id,
            "suite_id": case["suite_id"],
            "execution_mode": execution_mode,
            "runtime_action": runtime_action,
            "proposal_seed": dict(case["proposal_seed"]),
            "resolved_reason": resolved_reason,
            "source_utterance": source_case.get("utterance"),
            "response": _response_snapshot(result),
            "observed_runtime_outcome": observed,
            "expected_runtime_outcome": dict(case.get("expected_runtime_outcome") or {}),
            "oracle": oracle,
            "db_snapshot": _db_snapshot(db, proposal_container_id=proposal.id),
        }
    finally:
        db.close()


def _build_summary(results: list[dict[str, Any]], *, pack: dict[str, Any]) -> dict[str, Any]:
    passed = sum(1 for item in results if item["oracle"]["passed"])
    failed_case_ids = [item["executable_case_id"] for item in results if not item["oracle"]["passed"]]
    by_disposition: dict[str, dict[str, int]] = {}
    for item in results:
        disposition = str(item["expected_runtime_outcome"].get("expected_disposition") or "unknown")
        bucket = by_disposition.setdefault(disposition, {"total": 0, "passed": 0, "failed": 0})
        bucket["total"] += 1
        if item["oracle"]["passed"]:
            bucket["passed"] += 1
        else:
            bucket["failed"] += 1
    return {
        "pack_id": pack["pack_id"],
        "pack_mode": pack.get("pack_mode"),
        "authority_level": pack.get("authority_level"),
        "total_cases": len(results),
        "passed_cases": passed,
        "failed_cases": len(results) - passed,
        "failed_case_ids": failed_case_ids,
        "by_expected_disposition": by_disposition,
    }


def run_pack(*, case_id: str | None = None) -> dict[str, Any]:
    pack = load_executable_pack()
    source_pack = load_source_pack()
    source_case_map = _source_case_map(source_pack)
    cases = _selected_cases(pack, case_id=case_id)
    results = [run_case(case, source_case_map=source_case_map) for case in cases]
    return {
        "run_id": f"rescue_executable_action_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "pack_id": pack["pack_id"],
        "summary": _build_summary(results, pack=pack),
        "cases": results,
    }


def _save_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def main() -> int:
    enforce_file_backed_audit_input(audit_name="rescue_executable_action")
    args = _parser().parse_args()
    report = run_pack(case_id=args.case_id)
    output_path = LOG_ROOT / f"{report['run_id']}.json"
    _save_json(output_path, report)
    print(output_path)
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0 if report["summary"]["failed_cases"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
