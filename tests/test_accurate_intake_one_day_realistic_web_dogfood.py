import sys
from pathlib import Path
from tempfile import TemporaryDirectory


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_accurate_intake_one_day_realistic_web_dogfood import (  # noqa: E402
    build_report,
)


def _turn_by_id(turns: list[dict], turn_id: str) -> dict:
    return next(turn for turn in turns if turn["turn_id"] == turn_id)


def _react_trace(turn: dict) -> dict:
    payload = (turn.get("raw_response") or {}).get("payload") or {}
    manager = payload.get("intake_execution_manager") or {}
    return manager.get("react_trace") or {}


def test_accurate_intake_one_day_realistic_web_dogfood_uses_minimal_fooddb_evidence():
    with TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        report = build_report(db_path)

        scenario = report["one_day_realistic_web_dogfood"]

        assert scenario["status"] == "diagnostic_pass_with_correction_gap"

        # Non-goals are preserved
        assert scenario["live_provider_called"] is False
        assert scenario["kimi_activated"] is False
        assert scenario["production_db_touched"] is False
        assert scenario["product_readiness_claimed"] is False
        assert scenario["private_self_use_approved"] is False

        turns = scenario["turns"]
        assert len(turns) == 8, "Expected exactly 8 turns"

        # Turn 1: target update
        t_target = turns[0]
        assert t_target["turn_id"] == "target_001"
        assert t_target["expected_manager_decision"]["intent_type"] == "set_manual_daily_target"
        assert t_target["manager_decision_source"] == "runtime_response"
        assert t_target["manager_decision"]["intent_type"] == "set_manual_daily_target"
        assert t_target["manager_decision"]["semantic_decision"]["semantic_authority"] == (
            "deterministic_fake_provider"
        )
        manager_round_decision = t_target["manager_decision"]["trace"]["manager_rounds"][0][
            "decision"
        ]
        assert manager_round_decision["answer_contract"]["daily_target_kcal"] == 1600
        assert t_target["state_delta"]["manual_daily_target_updated"] is True
        assert t_target["state_delta"]["manual_daily_target_kcal"] == 1600
        assert t_target["raw_response"]["payload"]["remaining_budget"]["daily_target_kcal"] == 1600
        assert t_target["state_after"]["budget_kcal"] == 1600
        assert t_target["state_after"]["local_date"] == "2026-05-04"
        assert t_target["mutation_or_query"] == "mutation"

        # The food logging turns now consume runner-scoped approved FoodDB evidence
        # through the Manager loop instead of shadow-stub kcal.
        evi = scenario["evidence"]
        assert evi["food_logs_created"] is True
        assert evi["active_meal_count"] >= 4
        assert evi["food_evidence_gap_observed"] is False
        assert evi["evidence_gap_observed"] is False
        assert evi["approved_fooddb_evidence_fixture_used"] is True
        assert evi["fooddb_evidence_used"] is True
        assert evi["macro_present_evidence_seen"] is True
        assert evi["macro_missing_evidence_seen"] is True
        assert evi["manager_context_gap_observed"] is False
        assert evi["manager_fixture_call_topology_gap_observed"] is False
        assert evi["manager_gap_breakdown"]["runtime_response_turn_ids"] == [
            "target_001",
            "breakfast_001",
            "lunch_001",
            "tea_001",
            "dinner_draft_001",
            "dinner_basket_001",
            "dinner_remove_001",
            "query_001",
        ]
        assert evi["manager_gap_breakdown"]["missing_manager_response_turn_ids"] == []
        assert evi["manager_gap_breakdown"]["fixture_provider_exhausted_turn_ids"] == []
        assert evi["evidence_gap_handled_without_fake_kcal"] is True
        assert "food evidence gap prevented realistic food logging" not in scenario["blockers"]
        assert "correction target gap prevented remove-item application" in scenario["blockers"]
        assert (
            "manager context/runtime gap prevented complete turn evaluation"
            not in scenario["blockers"]
        )
        assert (
            "dogfood manager fixture exhausted before all turns completed"
            not in scenario["blockers"]
        )

        for turn_id in ("breakfast_001", "lunch_001", "tea_001", "dinner_basket_001"):
            turn = _turn_by_id(turns, turn_id)
            assert turn["mutation_or_query"] == "mutation"
            assert turn["state_delta"]["canonical_commit"] is True
            assert "estimate_nutrition" in _react_trace(turn)["executed_tools"]

        lunch = _turn_by_id(turns, "lunch_001")
        lunch_macro = lunch["raw_response"]["payload"]["sidecar"]["macro"]
        assert lunch_macro["display_status"] == "show"
        assert lunch_macro["guard_reason"] == "committed_and_aligned"
        assert lunch_macro["approved_fooddb_evidence_trace"]["source_lane"] == "generic_common_serving"

        dinner = _turn_by_id(turns, "dinner_basket_001")
        dinner_macro = dinner["raw_response"]["payload"]["sidecar"]["macro"]
        assert dinner_macro["display_status"] == "hide"
        assert dinner_macro["guard_reason"] == "macro_alignment_fail"
        assert dinner_macro["protein_g"] == 61
        assert dinner_macro["carbs_g"] == 206
        assert dinner_macro["fat_g"] == 58
        assert dinner_macro["approved_fooddb_evidence_trace"]["source_lane"] == "listed_component"
        assert dinner_macro["approved_fooddb_evidence_trace"]["macro_visibility_status"] == "hidden_missing_source"

        # Rule: Remove-item attempts the correction but correctly flags the negative guard
        # rather than faking an applied correction when the target ID is omitted!
        remove_guard = evi["remove_item_negative_guard"]
        assert remove_guard["attempted"] is True
        assert remove_guard["target_attachment_present"] is True
        assert remove_guard["existing_item_id_present"] is False
        assert remove_guard["correction_or_removal_applied"] is False
        assert remove_guard["runtime_blocked_missing_target"] is True

        # Same truth properties updated to not_checked
        assert evi["same_truth_verified"] == "not_checked"
        assert evi["dogfood_review_queue_compatible"] == "not_checked"

        t_query = turns[7]
        assert t_query["turn_id"] == "query_001"
        assert "expected_manager_decision" in t_query
        assert "manager_decision_source" in t_query
        assert t_query["mutation_or_query"] == "query"
        assert t_query["state_after"]["consumed_kcal"] > 0
        assert t_query["state_after"]["remaining_kcal"] < t_query["state_after"]["budget_kcal"]
        # Since it is a query, ensure state_before and state_after consumed_kcal match
        assert (
            t_query["state_before"]["consumed_kcal"]
            == t_query["state_after"]["consumed_kcal"]
        )


def test_negative_guard_raw_text_inference_not_used():
    with TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test2.db"
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from app.models import Base
        from scripts.run_accurate_intake_one_day_realistic_web_dogfood import (
            _build_test_client,
            _ChineseOneDayManagerProvider,
        )
        import importlib

        intake_routes = importlib.import_module("app.composition.intake_routes")

        engine = create_engine(
            f"sqlite:///{db_path.as_posix()}", connect_args={"check_same_thread": False}
        )
        Base.metadata.create_all(bind=engine)
        SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
        db = SessionLocal()

        provider = _ChineseOneDayManagerProvider()
        client = _build_test_client(db, provider)

        # We mutate the raw user input structurally. Unknown fixture input falls back to the
        # first scripted structured decision; the provider must not infer target intent from text.
        res = client.post(
            "/estimate",
            json={
                "text": "這句完全無關而且沒有任何數字",
                "user_id": "test",
                "allow_search": False,
            },
        )
        data = res.json() if res.content else {}

        # The manager decision should still be matching "set_manual_daily_target" and daily_target_kcal 1600!
        # The runtime may nest this under payload.manager_decision or payload itself.
        payload = data.get("payload") or {}
        mgr_decision = payload.get("manager_decision") or {}

        assert mgr_decision.get("intent_type") == "set_manual_daily_target"

        # Verify daily_target_kcal is available somewhere in the semantic decision
        semantic = mgr_decision.get("semantic_decision") or {}
        target_att = (
            mgr_decision.get("target_attachment")
            or semantic.get("target_attachment")
            or {}
        )
        assert (
            target_att.get("daily_target_kcal") == 1600
            or semantic.get("daily_target_kcal") == 1600
        )

        client.close()
        old_manager, old_search, old_extract, old_estimate_tool = getattr(
            client, "old_providers", (None, None, None, None)
        )
        intake_routes.manager_provider = old_manager
        intake_routes.search_provider = old_search
        intake_routes.extract_provider = old_extract
        import app.composition.intake_manager_tool_batch as intake_manager_tool_batch

        intake_manager_tool_batch.estimate_nutrition_tool = old_estimate_tool
        db.close()
        engine.dispose()
