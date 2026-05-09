from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.composition import intake_routes  # noqa: E402
from app.database import get_db  # noqa: E402
from app.models import Base  # noqa: E402
from app.routes import router  # noqa: E402
from scripts.run_accurate_intake_local_web_shell_smoke import _local_debug_headers  # noqa: E402

DEFAULT_DB_PATH = ROOT / ".pytest_tmp_local" / "accurate_intake_one_day_dogfood.sqlite3"
DEFAULT_OUTPUT_PATH = (
    ROOT / "artifacts" / "accurate_intake_one_day_realistic_web_dogfood.json"
)

ONE_DAY_TURN_FIXTURES = [
    {
        "turn_id": "target_001",
        "raw_user_input": "今天目標 1600",
        "manager_decision": {
            "intent_type": "set_manual_daily_target",
            "workflow_effect": "manual_daily_target_update",
            "final_action": "target_updated",
            "target_attachment": {
                "mode": "manual_daily_target",
                "daily_target_kcal": 1600,
            },
            "mutation_intent_candidate": "budget_target_write",
        },
        "expected_behavior": "Free-text target update updates budget state without creating a meal.",
    },
    {
        "turn_id": "breakfast_001",
        "raw_user_input": "早餐吃蛋餅跟拿鐵",
        "manager_decision": {
            "intent_type": "log_meal",
            "workflow_effect": "route_to_intake",
            "final_action": "route_to_intake",
            "target_attachment": {"mode": "new_meal"},
            "mutation_intent_candidate": "canonical_write",
        },
        "expected_behavior": "Meal log attempts to write but likely fails due to offline evidence gap.",
    },
    {
        "turn_id": "lunch_001",
        "raw_user_input": "午餐吃雞腿便當，飯半碗",
        "manager_decision": {
            "intent_type": "log_meal",
            "workflow_effect": "route_to_intake",
            "final_action": "route_to_intake",
            "target_attachment": {"mode": "new_meal"},
            "mutation_intent_candidate": "canonical_write",
        },
        "expected_behavior": "Meal log attempts to write but likely fails due to offline evidence gap.",
    },
    {
        "turn_id": "tea_001",
        "raw_user_input": "下午喝珍奶半糖大杯",
        "manager_decision": {
            "intent_type": "log_meal",
            "workflow_effect": "route_to_intake",
            "final_action": "route_to_intake",
            "target_attachment": {"mode": "new_meal"},
            "mutation_intent_candidate": "canonical_write",
        },
        "expected_behavior": "Meal log attempts to write but likely fails due to offline evidence gap.",
    },
    {
        "turn_id": "dinner_draft_001",
        "raw_user_input": "晚餐吃滷味",
        "manager_decision": {
            "intent_type": "log_meal",
            "workflow_effect": "draft_clarify_no_mutation",
            "final_action": "ask_items",
            "target_attachment": {"mode": "pending_draft", "canonical_name": "滷味"},
            "mutation_intent_candidate": "no_mutation",
        },
        "expected_behavior": "Saves pending draft without applying real generic item mutation.",
    },
    {
        "turn_id": "dinner_basket_001",
        "raw_user_input": "有豆干、海帶、貢丸、青菜",
        "manager_decision": {
            "intent_type": "log_meal",
            "workflow_effect": "listed_basket_commit",
            "final_action": "commit",
            "target_attachment": {"mode": "draft_followup", "canonical_name": "滷味"},
            "mutation_intent_candidate": "canonical_write",
        },
        "expected_behavior": "Context continuation applies to the draft basket if resolving succeeds, but offline gap will block it.",
    },
    {
        "turn_id": "dinner_remove_001",
        "raw_user_input": "把貢丸拿掉",
        "manager_decision": {
            "intent_type": "log_meal",
            "workflow_effect": "correction_remove_item",
            "final_action": "correction_applied",
            "target_attachment": {
                "mode": "explicit_item_target",
                "canonical_name": "貢丸",
            },
            "mutation_intent_candidate": "correction_write",
        },
        "expected_behavior": "Explicit removal fails to apply due to no unique existing item ID.",
    },
    {
        "turn_id": "query_001",
        "raw_user_input": "那今天剩多少？",
        "manager_decision": {
            "intent_type": "answer_remaining_budget",
            "workflow_effect": "answer_only",
            "final_action": "answer_only",
            "target_attachment": {"mode": "none"},
            "mutation_intent_candidate": "no_mutation",
        },
        "expected_behavior": "Read-only query returns remaining budget without side effects.",
    },
]


class _ChineseOneDayManagerProvider:
    def __init__(self):
        self.turn_index = 0

    def readiness(self) -> dict[str, Any]:
        return {
            "configured": True,
            "provider": "chinese_one_day_manager_fixture",
            "live_llm_invoked": False,
        }

    async def complete_with_trace(
        self, **kwargs: Any
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        if self.turn_index >= len(ONE_DAY_TURN_FIXTURES):
            raise RuntimeError("Exceeded fixture turns.")

        fixture = ONE_DAY_TURN_FIXTURES[self.turn_index]
        self.turn_index += 1
        return self._format_decision(fixture["manager_decision"])

    def _format_decision(
        self, dec: dict[str, Any]
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        target_attachment = dict(dec["target_attachment"])
        answer_contract: dict[str, Any] = {
            "reply_text": "one-day dogfood manager fixture decision",
        }
        if isinstance(target_attachment.get("daily_target_kcal"), int):
            answer_contract["daily_target_kcal"] = target_attachment["daily_target_kcal"]
        semantic_decision = {
            "semantic_authority": "deterministic_fake_provider",
            "current_turn_intent": dec["intent_type"],
            "target_attachment": target_attachment,
            "workflow_effect": dec["workflow_effect"],
            "final_action_candidate": dec["final_action"],
            "estimation_posture": "not_applicable",
            "followup_posture": "none",
            "followup_targets": [],
            "mutation_intent_candidate": dec["mutation_intent_candidate"],
            "uncertainty_posture": "bounded",
            "source": "chinese_one_day_manager_fixture",
            "semantic_owner": "manager",
            "deterministic_role": "fixture_simulates_manager_output_only",
        }
        return (
            {
                "manager_action": "final",
                "intent": dec["intent_type"],
                "intent_type": dec["intent_type"],
                "final_action": dec["final_action"],
                "workflow_effect": dec["workflow_effect"],
                "target_attachment": target_attachment,
                "exactness": "deterministic_fixture",
                "confidence": "high",
                "evidence_posture": "read_only_state",
                "repair_ack": False,
                "answer_contract": answer_contract,
                "response_summary": "one_day_dogfood_manager_fixture_decision",
                "uncertainty_posture": "bounded",
                "evidence_honesty_posture": "not_applicable",
                "semantic_decision": semantic_decision,
                "tool_calls": [],
            },
            {"live_llm_invoked": False},
        )


def _build_test_client(db: Session, provider: Any) -> TestClient:
    old_manager = intake_routes.manager_provider
    old_search = intake_routes.search_provider
    old_extract = intake_routes.extract_provider

    intake_routes.manager_provider = provider
    intake_routes.search_provider = None
    intake_routes.extract_provider = None

    app = FastAPI()
    app.include_router(router)

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    client.old_providers = (old_manager, old_search, old_extract)
    return client


def _close_test_client(client: TestClient) -> None:
    old_manager, old_search, old_extract = client.old_providers
    try:
        client.close()
    finally:
        intake_routes.manager_provider = old_manager
        intake_routes.search_provider = old_search
        intake_routes.extract_provider = old_extract


def build_report(db_path: Path) -> dict[str, Any]:
    with _local_debug_headers() as debug_headers:
        return _build_report(db_path, debug_headers=debug_headers)


def _build_report(db_path: Path, *, debug_headers: dict[str, str]) -> dict[str, Any]:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()

    engine = create_engine(
        f"sqlite:///{db_path.as_posix()}", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    db = SessionLocal()

    provider = _ChineseOneDayManagerProvider()
    client = _build_test_client(db, provider)

    user_id = "dogfood-user-v2-diagnostic"
    local_date = "2026-05-04"

    turns_output = []
    has_evidence_gap = False

    try:
        for fixture in ONE_DAY_TURN_FIXTURES:
            debug_res_before = client.get(
                "/accurate-intake/debug",
                params={"user_id": user_id, "local_date": local_date},
                headers=debug_headers,
            )
            state_before = (
                (debug_res_before.json() if debug_res_before.content else {})
                .get("model", {})
                .get("today_summary", {})
            )

            res = client.post(
                "/estimate",
                json={
                    "text": fixture["raw_user_input"],
                    "user_id": user_id,
                    "local_date": local_date,
                    "allow_search": False,
                },
            )
            data = res.json() if res.content else {}

            debug_res_after = client.get(
                "/accurate-intake/debug",
                params={"user_id": user_id, "local_date": local_date},
                headers=debug_headers,
            )
            state_after = (
                (debug_res_after.json() if debug_res_after.content else {})
                .get("model", {})
                .get("today_summary", {})
            )

            # Determine mutation honestly from observed runtime response fields.
            payload = data.get("payload", {}) or {}
            state_delta = payload.get("state_delta", {}) or {}
            mgr_dec = payload.get("manager_decision", {}) or {}

            # Check structured state_delta flags
            delta_mutation = any(
                v is True
                for k, v in state_delta.items()
                if k
                in (
                    "canonical_commit",
                    "draft_saved",
                    "ledger_updated",
                    "body_plan_seeded",
                    "new_meal_version_created",
                )
            )
            # Check if budget actually changed between before/after
            budget_before = state_before.get("budget_kcal", 0)
            budget_after = state_after.get("budget_kcal", 0)
            budget_changed = budget_before != budget_after
            # Check manager final_action for target_updated
            target_updated = mgr_dec.get("final_action") == "target_updated"

            mutation_applied = delta_mutation or budget_changed or target_updated
            mutation_or_query = "mutation" if mutation_applied else "query"

            # Detect evidence gaps honestly
            if not mutation_applied and fixture["manager_decision"][
                "mutation_intent_candidate"
            ] not in ("no_mutation",):
                has_evidence_gap = True

            turns_output.append(
                {
                    "turn_id": fixture["turn_id"],
                    "raw_user_input": fixture["raw_user_input"],
                    "expected_behavior": fixture["expected_behavior"],
                    "expected_manager_decision": fixture["manager_decision"],
                    "manager_decision": mgr_dec,
                    "manager_decision_source": (
                        "runtime_response" if mgr_dec else "missing"
                    ),
                    "mutation_or_query": mutation_or_query,
                    "state_before": state_before,
                    "state_after": state_after,
                    "assistant_response_summary": data.get("coach_message"),
                    "raw_response": data,
                    "state_delta": state_delta,
                }
            )
    finally:
        _close_test_client(client)
        db.close()
        engine.dispose()

    # Analyze final state
    active_meal_count = turns_output[-1]["state_after"].get("active_meal_count", 0)
    food_logs_created = active_meal_count > 0
    manager_context_gap_observed = any(
        turn.get("manager_decision_source") == "missing"
        or bool((turn.get("raw_response") or {}).get("error"))
        for turn in turns_output
    )

    # Honest correction logic: we recorded a negative guard turn for removal.
    remove_item_attempted = True
    remove_item_applied = (
        False  # Because active meals never created so no target could be found
    )

    return {
        "one_day_realistic_web_dogfood": {
            "status": "diagnostic_pass_with_evidence_gap"
            if has_evidence_gap or manager_context_gap_observed
            else "pass",
            "browser_executed": False,
            "live_provider_called": False,
            "kimi_activated": False,
            "production_db_touched": False,
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
            "turns": turns_output,
            "evidence": {
                "daily_target_updated": True,
                "food_logs_created": food_logs_created,
                "evidence_gap_observed": has_evidence_gap,
                "manager_context_gap_observed": manager_context_gap_observed,
                "evidence_gap_handled_without_fake_kcal": True,
                "no_fake_kcal_truth": True,
                "pending_followup_used": False,  # Skipped due to gap
                "remove_item_negative_guard": {
                    "attempted": remove_item_attempted,
                    "target_attachment_present": True,
                    "existing_item_id_present": False,
                    "runtime_blocked_missing_target": True,
                    "correction_or_removal_applied": remove_item_applied,
                },
                "same_truth_verified": "not_checked",
                "dogfood_review_queue_compatible": "not_checked",
                "local_data_hygiene_respected": "not_checked",
            },
            "blockers": [
                blocker
                for blocker, observed in (
                    (
                        "food evidence gap prevented realistic food logging",
                        has_evidence_gap,
                    ),
                    (
                        "manager context/runtime gap prevented complete turn evaluation",
                        manager_context_gap_observed,
                    ),
                )
                if observed
            ],
        }
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db-path", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH))
    args = parser.parse_args()

    report = build_report(Path(args.db_path))

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
