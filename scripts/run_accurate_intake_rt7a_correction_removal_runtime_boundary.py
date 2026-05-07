from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
from pathlib import Path
import sys
from typing import Any

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.budget.infrastructure.models import DayBudgetLedgerRecord  # noqa: E402
from app.composition.canonical_persistence import commit_meal_payload_to_canonical  # noqa: E402
from app.composition.intake_execution_orchestrator import _build_remove_item_target_evidence_artifact  # noqa: E402
from app.composition.intake_manager_tool_batch import nutrition_tool_output  # noqa: E402
from app.composition.state_resolver import resolve_intake_state  # noqa: E402
from app.database import get_or_create_user  # noqa: E402
from app.intake.infrastructure.models import MealItemRecord, MealThreadRecord, MealVersionRecord  # noqa: E402
from app.models import Base  # noqa: E402
from app.schemas import CommitRequestCandidate, MealItemPayload  # noqa: E402
from app.shared.infra.json_artifacts import write_json_artifact  # noqa: E402


DEFAULT_OUTPUT_PATH = ROOT / "artifacts" / "accurate_intake_rt7a_correction_removal_runtime_boundary.json"


def _session() -> Session:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    testing_session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)
    return testing_session()


def _two_item_candidate(*, request_id: str) -> CommitRequestCandidate:
    return CommitRequestCandidate(
        request_id=request_id,
        manager_intent="food_estimation",
        version_reason="new_intake",
        meal_title="lunch plate",
        raw_input="chicken rice and soup",
        estimated_kcal=650,
        protein_g=35,
        carb_g=70,
        fat_g=18,
        resolution_status="completed_meal",
        local_date="2026-05-02",
        items=[
            MealItemPayload(name="chicken rice", estimated_kcal=500, protein_g=32, carb_g=65, fat_g=15),
            MealItemPayload(name="soup", estimated_kcal=150, protein_g=3, carb_g=5, fat_g=3),
        ],
    )


def _single_item_candidate(*, request_id: str) -> CommitRequestCandidate:
    return CommitRequestCandidate(
        request_id=request_id,
        manager_intent="food_estimation",
        version_reason="new_intake",
        meal_title="pearl milk tea",
        raw_input="pearl milk tea",
        estimated_kcal=480,
        protein_g=4,
        carb_g=78,
        fat_g=16,
        resolution_status="completed_meal",
        local_date="2026-05-02",
        items=[MealItemPayload(name="pearl milk tea", estimated_kcal=480, protein_g=4, carb_g=78, fat_g=16)],
    )


def _correction_candidate(*, meal_thread_id: int, meal_item_id: int) -> CommitRequestCandidate:
    return CommitRequestCandidate(
        request_id="rt7a-correction-update",
        manager_intent="food_estimation",
        meal_thread_id=meal_thread_id,
        version_reason="correction",
        meal_title="lunch plate",
        raw_input="the chicken rice was smaller",
        estimated_kcal=470,
        protein_g=30,
        carb_g=55,
        fat_g=12,
        resolution_status="completed_meal",
        local_date="2026-05-02",
        items=[MealItemPayload(name="chicken rice", estimated_kcal=320, protein_g=27, carb_g=50, fat_g=9)],
        trace_ref={"correction_target_ref": {"meal_thread_id": meal_thread_id, "meal_item_id": meal_item_id, "canonical_name": "chicken rice"}},
    )


def _removal_candidate(*, meal_thread_id: int, meal_item_id: int, canonical_name: str = "chicken rice") -> CommitRequestCandidate:
    return CommitRequestCandidate(
        request_id="rt7a-remove-item",
        manager_intent="food_estimation",
        meal_thread_id=meal_thread_id,
        version_reason="correction",
        meal_title="lunch plate",
        raw_input="remove the chicken rice",
        estimated_kcal=150,
        protein_g=3,
        carb_g=5,
        fat_g=3,
        resolution_status="completed_meal",
        local_date="2026-05-02",
        items=[],
        trace_ref={
            "correction_operation": "remove_item",
            "correction_target_ref": {"meal_thread_id": meal_thread_id, "meal_item_id": meal_item_id, "canonical_name": canonical_name},
        },
    )


def _items_for_version(db: Session, version_id: int) -> list[MealItemRecord]:
    return db.execute(select(MealItemRecord).where(MealItemRecord.meal_version_id == version_id).order_by(MealItemRecord.item_index.asc())).scalars().all()


def _resolved_target(*, meal_thread_id: int, item: MealItemRecord) -> dict[str, object]:
    return {
        "meal_thread_id": meal_thread_id,
        "meal_item_id": item.id,
        "canonical_name": item.name,
        "observed_canonical_name": item.name,
        "target_resolution_source": "manager_target_proposal_validated",
    }


def _single_item_reference_case() -> dict[str, Any]:
    db = _session()
    try:
        user = get_or_create_user(db, "rt7a-single-item-ref")
        commit = commit_meal_payload_to_canonical(db, user=user, candidate=_single_item_candidate(request_id="rt7a-single-item"))
        assert commit is not None
        item = db.execute(select(MealItemRecord)).scalar_one()
        state = resolve_intake_state(db, user_external_id="rt7a-single-item-ref", local_date="2026-05-02", incoming_user_text="actually make that half sugar")
        target = state.injected_context["TARGET_MEAL_REFERENCE"]
        blockers = []
        if target.get("meal_thread_id") != commit.meal_thread_id or target.get("meal_version_id") != commit.meal_version_id:
            blockers.append("single_item_target_thread_reference_mismatch")
        if target.get("meal_item_id") != item.id:
            blockers.append("single_item_target_item_reference_missing")
        if target.get("item_resolution_source") != "single_active_item":
            blockers.append("single_item_resolution_source_mismatch")
        return {"case_id": "single_item_reference", "status": "pass" if not blockers else "fail", "blockers": blockers}
    finally:
        db.close()


def _ambiguous_multi_item_reference_case() -> dict[str, Any]:
    db = _session()
    try:
        user = get_or_create_user(db, "rt7a-ambiguous-ref")
        commit = commit_meal_payload_to_canonical(db, user=user, candidate=_two_item_candidate(request_id="rt7a-ambiguous-initial"))
        assert commit is not None
        state = resolve_intake_state(db, user_external_id="rt7a-ambiguous-ref", local_date="2026-05-02", incoming_user_text="actually make the rice smaller")
        target = state.injected_context["TARGET_MEAL_REFERENCE"]
        recent = state.injected_context["RECENT_COMMITTED_MEALS_SUMMARY"][0]
        blockers = []
        if "meal_item_id" in target:
            blockers.append("ambiguous_target_guessed_item_authority")
        if target.get("item_resolution_source") != "ambiguous_active_items":
            blockers.append("ambiguous_target_resolution_source_mismatch")
        if len(recent.get("item_candidates") or []) != 2:
            blockers.append("ambiguous_recent_item_candidates_missing")
        if any(candidate.get("mutation_authority") is not False for candidate in recent.get("item_candidates") or []):
            blockers.append("ambiguous_recent_item_candidates_gained_authority")
        return {"case_id": "ambiguous_multi_item_reference", "status": "pass" if not blockers else "fail", "blockers": blockers}
    finally:
        db.close()


def _item_level_correction_case() -> dict[str, Any]:
    db = _session()
    try:
        user = get_or_create_user(db, "rt7a-correction-user")
        initial = commit_meal_payload_to_canonical(db, user=user, candidate=_two_item_candidate(request_id="rt7a-correction-initial"), budget_kcal=1800)
        assert initial is not None
        old_items = _items_for_version(db, initial.meal_version_id)
        correction = commit_meal_payload_to_canonical(db, user=user, candidate=_correction_candidate(meal_thread_id=initial.meal_thread_id, meal_item_id=old_items[0].id), budget_kcal=1800)
        assert correction is not None
        thread = db.get(MealThreadRecord, initial.meal_thread_id)
        old_version = db.get(MealVersionRecord, initial.meal_version_id)
        new_items = _items_for_version(db, correction.meal_version_id)
        ledger = db.execute(select(DayBudgetLedgerRecord)).scalar_one()
        blockers = []
        if correction.superseded_version_id != initial.meal_version_id:
            blockers.append("correction_superseded_version_missing")
        if thread is None or thread.active_version_id != correction.meal_version_id:
            blockers.append("correction_active_version_not_advanced")
        if old_version is None or old_version.version_status != "superseded":
            blockers.append("correction_old_version_not_superseded")
        if [(item.name, item.estimated_kcal) for item in new_items] != [("chicken rice", 320), ("soup", 150)]:
            blockers.append("correction_non_target_items_not_preserved")
        if ledger.consumed_kcal != 470 or ledger.remaining_kcal != 1330:
            blockers.append("correction_ledger_recompute_mismatch")
        return {"case_id": "item_level_correction", "status": "pass" if not blockers else "fail", "blockers": blockers}
    finally:
        db.close()


def _explicit_item_removal_case() -> dict[str, Any]:
    db = _session()
    try:
        user = get_or_create_user(db, "rt7a-removal-user")
        initial = commit_meal_payload_to_canonical(db, user=user, candidate=_two_item_candidate(request_id="rt7a-removal-initial"), budget_kcal=1800)
        assert initial is not None
        old_items = _items_for_version(db, initial.meal_version_id)
        removal = commit_meal_payload_to_canonical(db, user=user, candidate=_removal_candidate(meal_thread_id=initial.meal_thread_id, meal_item_id=old_items[0].id), budget_kcal=1800)
        assert removal is not None
        thread = db.get(MealThreadRecord, initial.meal_thread_id)
        old_version = db.get(MealVersionRecord, initial.meal_version_id)
        new_items = _items_for_version(db, removal.meal_version_id)
        ledger = db.execute(select(DayBudgetLedgerRecord)).scalar_one()
        blockers = []
        if thread is None or thread.active_version_id != removal.meal_version_id:
            blockers.append("removal_active_version_not_advanced")
        if old_version is None or old_version.version_status != "superseded":
            blockers.append("removal_old_version_not_superseded")
        if [(item.name, item.estimated_kcal) for item in new_items] != [("soup", 150)]:
            blockers.append("removal_non_target_items_not_preserved")
        if ledger.consumed_kcal != 150 or ledger.remaining_kcal != 1650:
            blockers.append("removal_ledger_recompute_mismatch")
        return {"case_id": "explicit_item_removal", "status": "pass" if not blockers else "fail", "blockers": blockers}
    finally:
        db.close()


def _remove_target_evidence_case() -> dict[str, Any]:
    db = _session()
    try:
        user = get_or_create_user(db, "rt7a-target-evidence-user")
        initial = commit_meal_payload_to_canonical(db, user=user, candidate=_two_item_candidate(request_id="rt7a-target-evidence-initial"), budget_kcal=1800)
        assert initial is not None
        soup = next(item for item in _items_for_version(db, initial.meal_version_id) if item.name == "soup")
        artifact = _build_remove_item_target_evidence_artifact(
            db,
            user_external_id="rt7a-target-evidence-user",
            raw_user_input="remove soup",
            local_date="2026-05-02",
            request_id="rt7a-target-evidence-turn",
            correction_target=_resolved_target(meal_thread_id=initial.meal_thread_id, item=soup),
            manager_semantic_decision={"current_turn_intent": "correct_meal", "final_action_candidate": "correction_applied", "target_attachment": {"operation": "remove_item", "canonical_name": "soup"}},
        )
        tool_output = nutrition_tool_output(raw_user_input="remove soup", nutrition_artifact=artifact, correction_target=_resolved_target(meal_thread_id=initial.meal_thread_id, item=soup), budget_summary=None)
        blockers = []
        contract = artifact.payload.trace_contract["target_evidence_contract"]
        if contract["nutrition_evidence_present"] is not False or contract["target_evidence_is_nutrition_evidence"] is not False:
            blockers.append("remove_target_evidence_promoted_to_nutrition_truth")
        if tool_output["evidence"]["nutrition_payload"] is not None:
            blockers.append("remove_target_evidence_tool_output_injected_nutrition_payload")
        if tool_output["evidence"]["target_evidence_payload"]["canonical_remaining_item_totals"]["estimated_kcal"] != 500:
            blockers.append("remove_target_evidence_remaining_totals_mismatch")
        return {"case_id": "remove_target_evidence_boundary", "status": "pass" if not blockers else "fail", "blockers": blockers}
    finally:
        db.close()


def build_rt7a_correction_removal_runtime_boundary_artifact(*, output_path: str | Path | None = None) -> dict[str, Any]:
    cases = [
        _single_item_reference_case(),
        _ambiguous_multi_item_reference_case(),
        _item_level_correction_case(),
        _explicit_item_removal_case(),
        _remove_target_evidence_case(),
    ]
    blockers = [f"{case['case_id']}.{blocker}" for case in cases for blocker in case["blockers"]]
    resolved_output = Path(output_path) if output_path is not None else DEFAULT_OUTPUT_PATH
    return json.loads(json.dumps({
        "artifact_schema_version": "1.0",
        "artifact_name": resolved_output.name,
        "artifact_path": str(resolved_output),
        "schema_version": "1.0",
        "fixture_or_real": "real_runtime_local",
        "producer_track": "CurrentShell/ManagerRuntime",
        "intended_consumers": ["CurrentShell/AppShell", "CurrentShell/SharedCurrentShell", "human_review"],
        "ready_for_other_tracks": True,
        "non_claims": {
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
            "real_fooddb_pass_claimed": False,
        },
        "gate_id": "accurate_intake_rt7a_correction_removal_runtime_boundary",
        "claim_scope": "manager_runtime_rt7a_correction_removal_runtime_boundary",
        "status": "pass" if not blockers else "fail",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "target_manager_runtime_gate": "rt7a_correction_removal_runtime_boundary",
        "supports_journeys": ["K"],
        "runtime_backed": True,
        "live_llm_invoked": False,
        "fooddb_used": False,
        "web_tavily_used": False,
        "runtime_truth_changed": False,
        "mutation_changed": False,
        "manager_context_packet_schema_changed": False,
        "summary": {"case_count": len(cases), "passed_case_count": sum(1 for case in cases if case["status"] == "pass")},
        "cases": cases,
        "blockers": blockers,
    }, ensure_ascii=False))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run RT7a correction/removal runtime boundary gate.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH))
    args = parser.parse_args(argv)
    artifact = build_rt7a_correction_removal_runtime_boundary_artifact(output_path=args.output)
    output_path = Path(args.output)
    write_json_artifact(output_path, artifact)
    print(json.dumps({"artifact": str(output_path), "status": artifact["status"], "passed_case_count": artifact["summary"]["passed_case_count"], "case_count": artifact["summary"]["case_count"]}, ensure_ascii=False))
    return 0 if artifact["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
