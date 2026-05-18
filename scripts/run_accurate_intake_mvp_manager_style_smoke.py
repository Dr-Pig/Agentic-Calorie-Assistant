from __future__ import annotations

import argparse
import asyncio
import importlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.composition.accurate_intake_debug_routes import build_accurate_intake_debug_payload  # noqa: E402
from app.composition.non_fooddb_read_only_turn import NON_FOODDB_READ_ONLY_MANAGER_TOOLS  # noqa: E402
from app.composition.onboarding_service import OnboardingBootstrapInput, bootstrap_body_plan_for_date  # noqa: E402
from app.database import get_or_create_user  # noqa: E402
from app.models import Base  # noqa: E402

DEFAULT_ARTIFACT_PATH = ROOT / "artifacts" / "accurate_intake_mvp_manager_style_smoke.json"
DEFAULT_DB_PATH = ROOT / "artifacts" / "accurate_intake_mvp_manager_style_smoke.sqlite3"
ACTIVE_ENTRYPOINT = "app.composition.intake_turn_orchestrator.execute_intake_turn"

_NOT_CLAIMING = [
    "product_ready",
    "rollout_ready",
    "live_llm_ready",
    "web_ready",
    "production_db_ready",
]


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if hasattr(value, "model_dump"):
        return _json_safe(value.model_dump(mode="json"))
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def _session_factory(db_path: Path) -> sessionmaker[Session]:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{db_path.as_posix()}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, autocommit=False, autoflush=False)


def _active_entrypoint() -> Any:
    module = importlib.import_module("app.composition.intake_turn_orchestrator")
    return getattr(module, "execute_intake_turn")


def _active_entrypoint_verified() -> bool:
    entrypoint = _active_entrypoint()
    return f"{entrypoint.__module__}.{entrypoint.__name__}" == ACTIVE_ENTRYPOINT


class DeterministicSelfUseManagerProvider:
    """Deterministic fixture provider for the active Manager loop only."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def readiness(self) -> dict[str, Any]:
        return {
            "configured": True,
            "provider": "deterministic_self_use_manager_fixture",
            "live_llm_invoked": False,
        }

    async def complete_with_trace(self, **kwargs: Any) -> tuple[dict[str, Any], dict[str, Any]]:
        user_payload = _dict(kwargs.get("user_payload"))
        raw = str(user_payload.get("raw_user_input") or "")
        available_tools = {str(item) for item in _list(user_payload.get("available_tools"))}
        round_index = int(user_payload.get("round_index") or 0)
        self.calls.append(
            {
                "raw_user_input": raw,
                "available_tools": sorted(available_tools),
                "round_index": round_index,
            }
        )
        if set(NON_FOODDB_READ_ONLY_MANAGER_TOOLS).intersection(available_tools):
            return self._entry_decision(raw), self._trace("entry_decision")
        return self._execution_decision(raw=raw, available_tools=available_tools, round_index=round_index), self._trace(
            "execution_decision"
        )

    def _trace(self, stage: str) -> dict[str, Any]:
        return {
            "source": "deterministic_self_use_manager_fixture",
            "stage": stage,
            "live_llm_invoked": False,
        }

    def _entry_decision(self, raw: str) -> dict[str, Any]:
        normalized = raw.strip().lower()
        if "how much" in normalized or "remaining" in normalized or "today" in normalized:
            return self._final(
                intent_type="answer_remaining_budget",
                current_turn_intent="answer_remaining_budget",
                final_action="answer_only",
                workflow_effect="answer_only",
                mutation_intent_candidate="ledger_read",
                estimation_posture="not_applicable",
                evidence_posture="read_only_state",
            )
        if "smaller" in normalized or "correct" in normalized:
            return self._final(
                intent_type="log_meal",
                current_turn_intent="correct_meal",
                final_action="correction_applied",
                workflow_effect="route_to_intake",
                mutation_intent_candidate="correction_write",
                target_attachment={"mode": "target_committed_thread"},
                estimation_posture="estimable",
                evidence_posture="needs_tool_evidence",
            )
        return self._final(
            intent_type="log_meal",
            current_turn_intent="log_meal",
            final_action="commit",
            workflow_effect="route_to_intake",
            mutation_intent_candidate="canonical_write",
            estimation_posture="estimable",
            evidence_posture="needs_tool_evidence",
        )

    def _execution_decision(self, *, raw: str, available_tools: set[str], round_index: int) -> dict[str, Any]:
        normalized = raw.strip().lower()
        if round_index == 0 and "estimate_nutrition" in available_tools:
            calls = [
                {
                    "name": "estimate_nutrition",
                    "arguments": {
                        "retrieval_goal": "exact_brand_lookup",
                        "base_dish": _smoke_manager_owned_base_dish(raw),
                        "semantic_authority_source": "deterministic_self_use_manager_fixture",
                    },
                }
            ]
            if "compare_against_budget" in available_tools:
                calls.append({"name": "compare_against_budget"})
            return {"manager_action": "call_tools", "response_mode": "tool_call", "tool_calls": calls}
        if "smaller" in normalized or "correct" in normalized:
            return self._final(
                intent_type="log_meal",
                current_turn_intent="correct_meal",
                final_action="correction_applied",
                workflow_effect="correction",
                mutation_intent_candidate="correction_write",
                target_attachment={"mode": "target_committed_thread"},
                estimation_posture="estimable",
                evidence_posture="tool_evidence_present",
            )
        return self._final(
            intent_type="log_meal",
            current_turn_intent="log_meal",
            final_action="commit",
            workflow_effect="commit",
            mutation_intent_candidate="canonical_write",
            target_attachment={"mode": "new_meal"},
            estimation_posture="estimable",
            evidence_posture="tool_evidence_present",
        )

    def _final(
        self,
        *,
        intent_type: str,
        current_turn_intent: str,
        final_action: str,
        workflow_effect: str,
        mutation_intent_candidate: str,
        target_attachment: dict[str, Any] | None = None,
        estimation_posture: str = "unknown",
        evidence_posture: str = "unknown",
    ) -> dict[str, Any]:
        target = dict(target_attachment or {"mode": "none"})
        return {
            "manager_action": "final",
            "intent": intent_type,
            "intent_type": intent_type,
            "final_action": final_action,
            "workflow_effect": workflow_effect,
            "target_attachment": target,
            "exactness": "deterministic_fixture",
            "confidence": "medium",
            "evidence_posture": evidence_posture,
            "repair_ack": False,
            "answer_contract": {"reply_text": workflow_effect},
            "response_summary": workflow_effect,
            "uncertainty_posture": "bounded",
            "evidence_honesty_posture": evidence_posture,
            "semantic_decision": {
                "semantic_authority": "deterministic_fake_provider",
                "current_turn_intent": current_turn_intent,
                "target_attachment": target,
                "workflow_effect": workflow_effect,
                "final_action_candidate": final_action,
                "estimation_posture": estimation_posture,
                "followup_posture": "none",
                "followup_targets": [],
                "mutation_intent_candidate": mutation_intent_candidate,
                "uncertainty_posture": "bounded",
                "source": "deterministic_self_use_manager_fixture",
                "semantic_owner": "manager",
                "deterministic_role": "fixture_simulates_manager_output_only",
            },
        }


def _smoke_manager_owned_base_dish(raw: str) -> str:
    text = str(raw or "").strip()
    for suffix in (" keyboard enter", " shift enter"):
        if suffix in text:
            text = text.split(suffix, 1)[0].strip()
    if "\n" in text:
        text = text.splitlines()[0].strip()
    marker = " extra "
    if marker in text:
        text = text.split(marker, 1)[0].strip()
    return text or str(raw or "").strip() or "meal"


def _seed_body_plan(db: Session, *, user_external_id: str, local_date: str) -> None:
    user = get_or_create_user(db, user_external_id)
    bootstrap_body_plan_for_date(
        db,
        user=user,
        inputs=OnboardingBootstrapInput(
            sex="female",
            age_years=34,
            height_cm=170,
            current_weight_kg=70,
            goal_type="lose_weight",
            weekly_target_rate_kg=0.5,
            timezone="Asia/Taipei",
            daily_lifestyle="sedentary_with_some_walking",
            weekly_exercise_days_band="1_2",
            local_date=local_date,
        ),
    )


async def _execute(
    db: Session,
    provider: DeterministicSelfUseManagerProvider,
    *,
    user_external_id: str,
    text: str,
    local_date: str,
) -> dict[str, Any]:
    return await _active_entrypoint()(
        db,
        user_external_id=user_external_id,
        raw_user_input=text,
        onboarding_payload=None,
        local_date=local_date,
        allow_search=False,
        provider=provider,
        search_port=None,
        extract_port=None,
    )


def _turn_summary(turn: int, kind: str, text: str, result: dict[str, Any]) -> dict[str, Any]:
    execution = _dict(result.get("intake_execution_manager"))
    final = _dict(execution.get("final"))
    return {
        "turn": turn,
        "kind": kind,
        "text": text,
        "request_id": result.get("request_id"),
        "manager_intent": _dict(result.get("manager_decision")).get("intent_type"),
        "manager_final_action": final.get("final_action") or _dict(result.get("manager_decision")).get("final_action"),
        "workflow_effect": final.get("workflow_effect") or _dict(result.get("manager_decision")).get("workflow_effect"),
        "state_delta": _json_safe(_dict(result.get("state_delta"))),
        "remaining_budget": _json_safe(_dict(result.get("remaining_budget"))),
        "hard_fail_conditions": list(result.get("hard_fail_conditions") or []),
        "manager_round_count": len(_list(execution.get("manager_rounds"))),
    }


def _validate_report(report: dict[str, Any]) -> tuple[str, list[str]]:
    blockers: list[str] = []
    turns = list(report.get("turns") or [])
    initial_delta = _dict(turns[0].get("state_delta")) if len(turns) > 0 else {}
    correction_delta = _dict(turns[1].get("state_delta")) if len(turns) > 1 else {}
    query_delta = _dict(turns[2].get("state_delta")) if len(turns) > 2 else {}
    debug_model = _dict(_dict(report.get("debug_surface")).get("model"))
    today = _dict(debug_model.get("today_summary"))
    same_truth = _dict(debug_model.get("same_truth"))

    if report.get("active_entrypoint_verified") is not True:
        blockers.append("active_entrypoint_not_verified")
    if initial_delta.get("canonical_commit") is not True:
        blockers.append("initial_meal_not_committed_through_manager_loop")
    if correction_delta.get("canonical_commit") is not True:
        blockers.append("correction_not_committed_through_manager_loop")
    if correction_delta.get("old_version_superseded") is not True:
        blockers.append("correction_did_not_supersede_prior_version")
    if any(bool(query_delta.get(key)) for key in ("canonical_commit", "meal_logged", "ledger_updated")):
        blockers.append("budget_query_mutated_state")
    if int(today.get("consumed_kcal") or 0) <= 0:
        blockers.append("debug_surface_missing_consumed_kcal")
    if same_truth.get("status") != "pass":
        blockers.append("debug_surface_same_truth_failed")
    return ("pass" if not blockers else "fail"), blockers


async def build_manager_style_smoke_report(
    *,
    db_path: Path,
    user_external_id: str = "manager-style-smoke-user",
    local_date: str = "2026-05-02",
    reset_db: bool = True,
) -> dict[str, Any]:
    if reset_db and db_path.exists():
        db_path.unlink()
    SessionLocal = _session_factory(db_path)
    provider = DeterministicSelfUseManagerProvider()
    with SessionLocal() as db:
        _seed_body_plan(db, user_external_id=user_external_id, local_date=local_date)
        initial = await _execute(
            db,
            provider,
            user_external_id=user_external_id,
            text="chicken sandwich",
            local_date=local_date,
        )
        correction = await _execute(
            db,
            provider,
            user_external_id=user_external_id,
            text="the chicken sandwich was smaller",
            local_date=local_date,
        )
        query = await _execute(
            db,
            provider,
            user_external_id=user_external_id,
            text="how much have I eaten today",
            local_date=local_date,
        )
        debug_surface = build_accurate_intake_debug_payload(
            db,
            user_external_id=user_external_id,
            local_date=local_date,
        )

    report = {
        "artifact_schema_version": "1.0",
        "smoke_id": "accurate_intake_mvp_manager_style_smoke_v1",
        "claim_scope": "local_deterministic_manager_style_smoke",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "not_claiming": list(_NOT_CLAIMING),
        "active_entrypoint": ACTIVE_ENTRYPOINT,
        "active_entrypoint_verified": _active_entrypoint_verified(),
        "manager_provider": provider.readiness(),
        "live_llm_invoked": False,
        "web_tavily_invoked": False,
        "production_db_used": False,
        "user_facing_rollout": False,
        "local_date": local_date,
        "turns": [
            _turn_summary(1, "new_meal", "chicken sandwich", initial),
            _turn_summary(2, "explicit_item_correction", "the chicken sandwich was smaller", correction),
            _turn_summary(3, "budget_query", "how much have I eaten today", query),
        ],
        "manager_provider_calls": provider.calls,
        "debug_surface": debug_surface,
    }
    status, blockers = _validate_report(report)
    report["status"] = status
    report["blockers"] = blockers
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the Accurate Intake MVP active Manager-style smoke.")
    parser.add_argument("--output", default=str(DEFAULT_ARTIFACT_PATH))
    parser.add_argument("--db-path", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--user-id", default="manager-style-smoke-user")
    parser.add_argument("--local-date", default="2026-05-02")
    parser.add_argument("--keep-db", action="store_true")
    args = parser.parse_args(argv)

    report = asyncio.run(
        build_manager_style_smoke_report(
            db_path=Path(args.db_path),
            user_external_id=args.user_id,
            local_date=args.local_date,
            reset_db=not args.keep_db,
        )
    )
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
