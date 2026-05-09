from __future__ import annotations

import asyncio
from pathlib import Path

import yaml
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.composition.accurate_intake_today_macro_mirror_gate import (
    build_today_macro_runtime_mirror_gate_artifact,
)
from app.composition.canonical_persistence import commit_meal_payload_to_canonical
from app.composition.current_budget_read_model import build_current_budget_view
from app.composition.intake_estimation_tools import estimate_nutrition_tool
from app.database import get_or_create_user
from app.models import Base
from app.nutrition.agent.exact_item_packets import build_exact_item_lane_packet
from app.nutrition.infrastructure.exact_item_search import resolve_exact_item_fts


def _session() -> Session:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    testing_session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)
    return testing_session()


def _manager_gate_ledger() -> dict[str, object]:
    return yaml.safe_load(Path("docs/quality/MANAGER_RUNTIME_GATE_LEDGER.yaml").read_text(encoding="utf-8"))


def test_macro_present_exact_item_flows_from_fooddb_seed_to_today_render() -> None:
    db = _session()
    user = get_or_create_user(db, "macro-present-exact-item-e2e")
    raw_input = "\u7d71\u4e00\u5de7\u514b\u529b\u725b\u4e73(400ml)"

    exact_candidates = resolve_exact_item_fts(raw_input, limit=1)
    assert exact_candidates
    assert exact_candidates[0]["title"] == raw_input
    assert exact_candidates[0]["label_kcal"] == 300
    assert exact_candidates[0]["label_macros"] == {"protein_g": 12.0, "carb_g": 48.0, "fat_g": 6.0}

    exact_packet = build_exact_item_lane_packet(raw_input, limit=1)
    top_candidate = exact_packet["top_exact_candidate"]
    assert top_candidate["macro_completeness"] == "complete"
    assert top_candidate["protein_g"] == 12.0
    assert top_candidate["carb_g"] == 48.0
    assert top_candidate["fat_g"] == 6.0

    artifact = asyncio.run(
        estimate_nutrition_tool(
            db,
            user_external_id=user.user_id,
            raw_user_input=raw_input,
            request_id="req-macro-present-exact-item",
            local_date="2026-05-09",
            allow_search=False,
        )
    )
    payload = artifact.payload

    assert payload.best_estimate_mode == "exact_item"
    assert payload.trace_contract["db_hit_type"] == "exact_truth"
    assert payload.trace_contract["macro_display_authorized"] is True
    assert payload.display_macro_breakdown == {
        "protein_g": 12,
        "carb_g": 48,
        "fat_g": 6,
        "macro_source": "exact_item_db",
        "macro_confidence": "high",
        "macro_status": "available",
    }

    commit_meal_payload_to_canonical(
        db,
        user=user,
        payload=payload,
        raw_input=raw_input,
        manager_intent="food_estimation",
        request_id=payload.request_id,
        budget_kcal=1200,
    )

    current_budget = build_current_budget_view(db, user_id=user.id, local_date="2026-05-09")
    assert current_budget.consumed_kcal == 300
    assert current_budget.consumed_protein == 12
    assert current_budget.consumed_carbs == 48
    assert current_budget.consumed_fat == 6
    assert current_budget.show_macro is True
    assert current_budget.macro_guard_reason == "committed_and_aligned"

    today_gate = build_today_macro_runtime_mirror_gate_artifact(
        manager_gate_ledger_artifact=_manager_gate_ledger(),
        current_budget_payload=current_budget.model_dump(mode="json"),
    )
    assert today_gate["status"] == "today_macro_runtime_mirror_gate_ready_for_browser"
    assert today_gate["truth_owner"] == "CurrentBudgetView.macro_visibility"
    assert today_gate["frontend_calculates_macro_values"] is False
    assert today_gate["runtime_case"]["macro_state"] == "visible"
    assert today_gate["runtime_case"]["protein_text"] == "12"
    assert today_gate["runtime_case"]["carbs_text"] == "48"
    assert today_gate["runtime_case"]["fat_text"] == "6"
