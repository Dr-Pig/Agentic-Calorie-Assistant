from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.composition.accurate_intake_debug_routes import build_accurate_intake_debug_payload
from app.composition.intake_turn_orchestrator import execute_intake_turn
from app.composition.non_fooddb_read_only_turn import NON_FOODDB_READ_ONLY_MANAGER_TOOLS
from app.composition.onboarding_service import OnboardingBootstrapInput, bootstrap_body_plan_for_date
from app.database import get_or_create_user
from app.models import Base


ROOT = Path(__file__).resolve().parents[1]
CASE_REGISTER_PATH = ROOT / "docs" / "quality" / "accurate_intake_mvp_ux_semantic_cases.json"
GATE_MANIFEST_PATH = ROOT / "docs" / "quality" / "accurate_intake_mvp_gate_manifest.json"
HUMAN_REVIEW_DOC_PATH = ROOT / "docs" / "quality" / "ACCURATE_INTAKE_MVP_UX_SEMANTIC_CASES.md"

EXPECTED_CASE_IDS = {f"UX-{index:03d}" for index in range(1, 19)}
FORBIDDEN_ORACLE_FIELDS = {
    "input_contains",
    "keyword",
    "raw_text_route",
    "raw_text_intent",
    "deterministic_route",
    "deterministic_intent",
}
FORBIDDEN_DETERMINISTIC_ROLES = {
    "infer_user_intent_from_raw_text",
    "choose_workflow_route_from_keywords",
    "create_missing_workflow_effect",
    "fabricate_target_attachment",
    "decide_logged_draft_no_mutation_from_food_seed",
    "silently_rewrite_manager_semantic_decision",
}
ALLOWED_DETERMINISTIC_ROLES = {
    "validate_schema",
    "validate_target_exists_unique_writable",
    "validate_evidence_accepted",
    "reject_or_downgrade_unsafe_mutation",
    "compute_ledger_and_read_model_truth",
}


def _load_case_register() -> dict[str, Any]:
    return json.loads(CASE_REGISTER_PATH.read_text(encoding="utf-8-sig"))


def _session() -> Session:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    testing_session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)
    return testing_session()


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


class ScriptedManagerDecisionProvider:
    """Fixture provider that returns scripted Manager decisions, not raw-text routes."""

    def __init__(self, *, entry: dict[str, Any], execution: list[dict[str, Any]] | None = None) -> None:
        self.entry = entry
        self.execution = list(execution or [])
        self.execution_index = 0
        self.calls: list[dict[str, Any]] = []

    def readiness(self) -> dict[str, Any]:
        return {
            "configured": True,
            "provider": "scripted_manager_decision_fixture",
            "live_llm_invoked": False,
        }

    async def complete_with_trace(self, **kwargs: Any) -> tuple[dict[str, Any], dict[str, Any]]:
        user_payload = dict(kwargs.get("user_payload") or {})
        available_tools = {str(item) for item in user_payload.get("available_tools") or []}
        self.calls.append(
            {
                "available_tools": sorted(available_tools),
                "round_index": int(user_payload.get("round_index") or 0),
                "raw_user_input_seen_by_manager": str(user_payload.get("raw_user_input") or ""),
            }
        )
        if set(NON_FOODDB_READ_ONLY_MANAGER_TOOLS).intersection(available_tools):
            return self.entry, self._trace("entry_decision")
        if self.execution_index >= len(self.execution):
            return _final_payload(
                intent_type="log_meal",
                current_turn_intent="unknown",
                final_action="no_commit",
                workflow_effect="safe_failure",
                mutation_intent_candidate="none",
                evidence_posture="missing_scripted_execution_decision",
            ), self._trace("missing_execution_decision")
        payload = self.execution[self.execution_index]
        self.execution_index += 1
        return payload, self._trace("execution_decision")

    def _trace(self, stage: str) -> dict[str, Any]:
        return {
            "source": "scripted_manager_decision_fixture",
            "stage": stage,
            "runner_inferred_semantics": False,
            "live_llm_invoked": False,
        }


def _call_tools(*names: str) -> dict[str, Any]:
    return {
        "manager_action": "call_tools",
        "response_mode": "tool_call",
        "tool_calls": [{"name": name} for name in names],
    }


def _final_payload(
    *,
    intent_type: str,
    current_turn_intent: str,
    final_action: str,
    workflow_effect: str,
    mutation_intent_candidate: str,
    target_attachment: dict[str, Any] | None = None,
    evidence_posture: str = "unknown",
    followup_question: str | None = None,
) -> dict[str, Any]:
    target = dict(target_attachment or {"mode": "none"})
    return {
        "manager_action": "final",
        "intent": intent_type,
        "intent_type": intent_type,
        "final_action": final_action,
        "workflow_effect": workflow_effect,
        "target_attachment": target,
        "exactness": "fixture",
        "confidence": "medium",
        "evidence_posture": evidence_posture,
        "repair_ack": False,
        "answer_contract": {"reply_text": workflow_effect, "followup_question": followup_question},
        "response_summary": workflow_effect,
        "uncertainty_posture": "bounded",
        "evidence_honesty_posture": evidence_posture,
        "semantic_decision": {
            "semantic_authority": "deterministic_fake_provider",
            "current_turn_intent": current_turn_intent,
            "target_attachment": target,
            "workflow_effect": workflow_effect,
            "final_action_candidate": final_action,
            "estimation_posture": "estimable" if final_action in {"commit", "correction_applied"} else "not_applicable",
            "followup_posture": "required" if followup_question else "none",
            "followup_question": followup_question,
            "followup_targets": [],
            "mutation_intent_candidate": mutation_intent_candidate,
            "uncertainty_posture": "bounded",
            "source": "fixture_manager_structured_decision",
            "semantic_owner": "manager",
            "deterministic_role": "validate_gate_trace_only",
        },
    }


def test_ux_semantic_case_register_declares_manager_owned_decision_contract() -> None:
    register = _load_case_register()

    assert register["register_id"] == "accurate_intake_mvp_ux_semantic_cases_v1"
    assert register["gate_group_id"] == "ux_semantic_manager_decision_consumption"
    assert register["runner_inferred_semantics"] is False
    assert register["truth_owner"]["user_intent"] == "manager_structured_decision"
    assert register["truth_owner"]["routing_or_workflow_effect"] == "manager_structured_decision"
    assert register["truth_owner"]["mutation_legality"] == "deterministic_guard"
    assert register["food_seed_rule"]["can_decide_logged_draft_no_mutation"] is False
    assert set(register["deterministic_roles"]["allowed"]) == ALLOWED_DETERMINISTIC_ROLES
    assert set(register["deterministic_roles"]["forbidden"]) == FORBIDDEN_DETERMINISTIC_ROLES


def test_ux_semantic_cases_cover_locked_mvp_set_without_raw_text_oracles() -> None:
    register = _load_case_register()
    cases = {case["case_id"]: case for case in register["cases"]}

    assert set(cases) == EXPECTED_CASE_IDS
    for case in cases.values():
        assert case["runner_inferred_semantics"] is False
        manager_fixture = case["manager_decision_fixture"]
        assert manager_fixture["source"] == "fixture_manager_structured_decision"
        assert manager_fixture["semantic_owner"] == "manager"
        assert manager_fixture["deterministic_role"] == "none"
        assert manager_fixture["workflow_effect"]
        assert manager_fixture["final_action"]
        assert isinstance(manager_fixture["target_attachment"], dict)
        assert not (FORBIDDEN_ORACLE_FIELDS & set(case))
        assert not (FORBIDDEN_ORACLE_FIELDS & set(manager_fixture))

        runtime_validation = case["expected_runtime_validation"]
        assert set(runtime_validation["deterministic_roles"]) <= ALLOWED_DETERMINISTIC_ROLES
        assert runtime_validation["runner_may_infer_semantics_from_raw_text"] is False
        assert runtime_validation["food_seed_may_decide_logged_draft_no_mutation"] is False


def test_ux_semantic_human_review_doc_stays_aligned_with_machine_register() -> None:
    register = _load_case_register()
    doc = HUMAN_REVIEW_DOC_PATH.read_text(encoding="utf-8-sig")
    cases = {case["case_id"]: case for case in register["cases"]}

    assert register["human_review_doc"] == "docs/quality/ACCURATE_INTAKE_MVP_UX_SEMANTIC_CASES.md"
    assert "machine-readable gate truth is `docs/quality/accurate_intake_mvp_ux_semantic_cases.json`" in doc
    for case_id, case in cases.items():
        assert f"| {case_id} |" in doc
        assert str(case["title"]) in doc


def test_gate_manifest_keeps_ux_semantic_wall_as_required_group() -> None:
    manifest = json.loads(GATE_MANIFEST_PATH.read_text(encoding="utf-8-sig"))
    groups = {group["group_id"]: group for group in manifest["required_groups"]}

    assert manifest["gate_version"] == "2.0"
    assert "ux_semantic_manager_decision_consumption" in groups
    assert groups["ux_semantic_manager_decision_consumption"]["pytest"] == [
        "tests/test_accurate_intake_mvp_ux_semantic_wall.py"
    ]
    assert manifest["live_llm_required"] is False
    assert manifest["web_tavily_required"] is False
    assert manifest["schema_migration_required"] is False


def test_runtime_does_not_mutate_when_manager_fixture_selects_read_only_even_for_food_text() -> None:
    db = _session()
    user_external_id = "ux-semantic-manager-read-only"
    local_date = "2026-05-02"
    _seed_body_plan(db, user_external_id=user_external_id, local_date=local_date)
    provider = ScriptedManagerDecisionProvider(
        entry=_final_payload(
            intent_type="answer_remaining_budget",
            current_turn_intent="answer_remaining_budget",
            final_action="answer_only",
            workflow_effect="answer_only",
            mutation_intent_candidate="ledger_read",
            evidence_posture="read_only_state",
        )
    )

    result = asyncio.run(
        execute_intake_turn(
            db,
            user_external_id=user_external_id,
            raw_user_input="I ate a tea egg",
            onboarding_payload=None,
            local_date=local_date,
            allow_search=False,
            manager_provider=provider,
            provider=provider,
        )
    )
    debug_payload = build_accurate_intake_debug_payload(db, user_external_id=user_external_id, local_date=local_date)

    assert result["manager_decision"]["intent_type"] == "answer_remaining_budget"
    assert result["state_delta"]["canonical_commit"] is False
    assert debug_payload["model"]["today_summary"]["consumed_kcal"] == 0
    assert provider.calls[0]["raw_user_input_seen_by_manager"] == "I ate a tea egg"


def test_runtime_can_commit_query_like_text_only_when_manager_fixture_authorizes_logging(monkeypatch) -> None:
    monkeypatch.setenv("V2_INTAKE_TURN_ALLOW_STUB_ESTIMATE", "1")
    db = _session()
    user_external_id = "ux-semantic-manager-log-authorized"
    local_date = "2026-05-02"
    _seed_body_plan(db, user_external_id=user_external_id, local_date=local_date)
    provider = ScriptedManagerDecisionProvider(
        entry=_final_payload(
            intent_type="log_meal",
            current_turn_intent="log_meal",
            final_action="commit",
            workflow_effect="route_to_intake",
            mutation_intent_candidate="canonical_write",
            evidence_posture="needs_tool_evidence",
        ),
        execution=[
            _call_tools("estimate_nutrition", "compare_against_budget"),
            _final_payload(
                intent_type="log_meal",
                current_turn_intent="log_meal",
                final_action="commit",
                workflow_effect="commit",
                mutation_intent_candidate="canonical_write",
                target_attachment={"mode": "new_meal"},
                evidence_posture="tool_evidence_present",
                followup_question="Please confirm size if you want a tighter estimate.",
            ),
        ],
    )

    result = asyncio.run(
        execute_intake_turn(
            db,
            user_external_id=user_external_id,
            raw_user_input="How many calories are in bubble milk tea?",
            onboarding_payload=None,
            local_date=local_date,
            allow_search=False,
            manager_provider=provider,
            provider=provider,
        )
    )
    debug_payload = build_accurate_intake_debug_payload(db, user_external_id=user_external_id, local_date=local_date)

    assert result["manager_decision"]["intent_type"] == "log_meal"
    assert result["intake_execution_manager"]["final"]["final_action"] == "commit"
    assert result["state_delta"]["canonical_commit"] is True
    final_round_decision = result["intake_execution_manager"]["manager_rounds"][-1]["decision"]
    assert final_round_decision["semantic_decision"]["source"] == "fixture_manager_structured_decision"
    assert debug_payload["model"]["today_summary"]["consumed_kcal"] > 0
    assert provider.calls[0]["raw_user_input_seen_by_manager"] == "How many calories are in bubble milk tea?"
