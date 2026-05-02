from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.composition.accurate_intake_debug_routes import build_accurate_intake_debug_payload
from app.composition.canonical_persistence import commit_meal_payload_to_canonical
from app.database import get_or_create_user
from app.intake.infrastructure.models import MealItemRecord
from app.models import Base
from app.schemas import CommitRequestCandidate, MealItemPayload

DEFAULT_ARTIFACT_PATH = ROOT / "artifacts" / "accurate_intake_mvp_self_use_smoke.json"
DEFAULT_DB_PATH = ROOT / "artifacts" / "accurate_intake_mvp_self_use_smoke.sqlite3"

_NOT_CLAIMING = [
    "product_ready",
    "rollout_ready",
    "live_llm_ready",
    "web_ready",
    "production_db_ready",
]


def _session_factory(db_path: Path) -> sessionmaker[Session]:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{db_path.as_posix()}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, autocommit=False, autoflush=False)


def _initial_candidate(*, local_date: str) -> CommitRequestCandidate:
    return CommitRequestCandidate(
        request_id="self-use-smoke-initial",
        manager_intent="food_estimation",
        version_reason="new_intake",
        meal_title="chicken rice and soup",
        raw_input="chicken rice and soup",
        estimated_kcal=650,
        protein_g=35,
        carb_g=70,
        fat_g=18,
        resolution_status="completed_meal",
        local_date=local_date,
        items=[
            MealItemPayload(name="chicken rice", estimated_kcal=500, protein_g=32, carb_g=65, fat_g=15),
            MealItemPayload(name="soup", estimated_kcal=150, protein_g=3, carb_g=5, fat_g=3),
        ],
    )


def _correction_candidate(*, local_date: str, meal_thread_id: int, meal_item_id: int) -> CommitRequestCandidate:
    return CommitRequestCandidate(
        request_id="self-use-smoke-correction",
        manager_intent="food_estimation",
        meal_thread_id=meal_thread_id,
        version_reason="correction",
        meal_title="chicken rice and soup",
        raw_input="the chicken rice was smaller",
        estimated_kcal=470,
        protein_g=30,
        carb_g=55,
        fat_g=12,
        resolution_status="completed_meal",
        local_date=local_date,
        items=[MealItemPayload(name="chicken rice", estimated_kcal=320, protein_g=27, carb_g=50, fat_g=9)],
        trace_ref={
            "correction_target_ref": {
                "meal_thread_id": meal_thread_id,
                "meal_item_id": meal_item_id,
                "canonical_name": "chicken rice",
            }
        },
    )


def build_self_use_smoke_report(
    *,
    db_path: Path,
    user_external_id: str = "self-use-smoke-user",
    local_date: str = "2026-05-02",
    reset_db: bool = True,
) -> dict[str, Any]:
    if reset_db and db_path.exists():
        db_path.unlink()
    SessionLocal = _session_factory(db_path)
    with SessionLocal() as db:
        user = get_or_create_user(db, user_external_id)
        initial = commit_meal_payload_to_canonical(
            db,
            user=user,
            candidate=_initial_candidate(local_date=local_date),
            budget_kcal=1800,
        )
        if initial is None:
            raise RuntimeError("self_use_initial_commit_failed")
        target_item = db.execute(
            select(MealItemRecord).where(MealItemRecord.meal_version_id == initial.meal_version_id)
        ).scalars().first()
        if target_item is None:
            raise RuntimeError("self_use_target_item_missing")
        correction = commit_meal_payload_to_canonical(
            db,
            user=user,
            candidate=_correction_candidate(
                local_date=local_date,
                meal_thread_id=initial.meal_thread_id,
                meal_item_id=target_item.id,
            ),
            budget_kcal=1800,
        )
        if correction is None:
            raise RuntimeError("self_use_correction_commit_failed")

    with SessionLocal() as db:
        debug_payload = build_accurate_intake_debug_payload(
            db,
            user_external_id=user_external_id,
            local_date=local_date,
        )

    model = dict(debug_payload.get("model") or {})
    today = dict(model.get("today_summary") or {})
    same_truth = dict(model.get("same_truth") or {})
    correction_history = list(model.get("correction_history") or [])
    status = "pass"
    blockers: list[str] = []
    if today.get("consumed_kcal") != 470:
        status = "fail"
        blockers.append("consumed_kcal_not_from_corrected_active_version")
    if today.get("remaining_kcal") != 1330:
        status = "fail"
        blockers.append("remaining_kcal_not_from_current_budget_truth")
    if same_truth.get("status") != "pass":
        status = "fail"
        blockers.append("debug_surface_same_truth_failed")
    if not correction_history or correction_history[0].get("non_target_item_names_preserved") != ["soup"]:
        status = "fail"
        blockers.append("correction_non_target_item_not_preserved")
    return {
        "artifact_schema_version": "1.0",
        "smoke_id": "accurate_intake_mvp_self_use_smoke_v1",
        "claim_scope": "local_deterministic_self_use_smoke",
        "status": status,
        "blockers": blockers,
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "not_claiming": list(_NOT_CLAIMING),
        "live_llm_invoked": False,
        "web_tavily_invoked": False,
        "production_db_used": False,
        "user_facing_rollout": False,
        "local_date": local_date,
        "input_sequence": [
            {"turn": 1, "kind": "new_meal", "text": "chicken rice and soup"},
            {"turn": 2, "kind": "explicit_item_correction", "text": "the chicken rice was smaller"},
            {"turn": 3, "kind": "debug_read", "text": "show current local product-loop truth"},
        ],
        "debug_surface": debug_payload,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the Accurate Intake MVP local self-use smoke.")
    parser.add_argument("--output", default=str(DEFAULT_ARTIFACT_PATH))
    parser.add_argument("--db-path", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--user-id", default="self-use-smoke-user")
    parser.add_argument("--local-date", default="2026-05-02")
    parser.add_argument("--keep-db", action="store_true")
    args = parser.parse_args(argv)

    report = build_self_use_smoke_report(
        db_path=Path(args.db_path),
        user_external_id=args.user_id,
        local_date=args.local_date,
        reset_db=not args.keep_db,
    )
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
