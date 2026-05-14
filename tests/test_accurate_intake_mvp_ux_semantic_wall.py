from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.composition.accurate_intake_debug_routes import build_accurate_intake_debug_payload
from app.composition.canonical_persistence import commit_meal_payload_to_canonical
from app.composition.intake_turn_orchestrator import execute_intake_turn
from app.composition.non_fooddb_read_only_turn import NON_FOODDB_READ_ONLY_MANAGER_TOOLS
from app.composition.onboarding_service import OnboardingBootstrapInput, bootstrap_body_plan_for_date
from app.database import get_or_create_user
from app.models import Base, MealItemRecord, MealThreadRecord, MealVersionRecord
from app.schemas import CommitRequestCandidate, MealItemPayload


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
                "manager_context_packet_v1": user_payload.get("manager_context_packet_v1"),
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
    semantic_overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    target = dict(target_attachment or {"mode": "none"})
    semantic_decision = {
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
        **dict(semantic_overrides or {}),
    }
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
        "semantic_decision": semantic_decision,
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


def test_runtime_keeps_estimate_explanation_query_read_only_even_with_active_meal_context() -> None:
    db = _session()
    user_external_id = "ux-semantic-estimate-explanation"
    local_date = "2026-05-02"
    _seed_body_plan(db, user_external_id=user_external_id, local_date=local_date)
    user = get_or_create_user(db, user_external_id)
    db.add(
        MealThreadRecord(
            user_id=user.id,
            title="早餐店鐵板麵套餐",
            active_version_id=None,
        )
    )
    db.commit()
    thread = db.query(MealThreadRecord).filter_by(user_id=user.id).one()
    version = MealVersionRecord(
        meal_thread_id=thread.id,
        version_status="active",
        version_reason="new_intake",
        meal_title="早餐店鐵板麵套餐",
        raw_input="我早餐吃個早點店的鐵板麵套餐",
        resolution_status="completed_meal",
        total_kcal=620,
        protein_g=24,
        carb_g=70,
        fat_g=22,
        local_date=local_date,
    )
    db.add(version)
    db.commit()
    thread.active_version_id = version.id
    db.add(thread)
    db.commit()
    provider = ScriptedManagerDecisionProvider(
        entry=_final_payload(
            intent_type="answer_query",
            current_turn_intent="answer_query",
            final_action="answer_only",
            workflow_effect="answer_only",
            mutation_intent_candidate="no_mutation",
            target_attachment={
                "mode": "target_committed_thread",
                "target_object_type": "meal_thread",
                "target_object_id": str(thread.id),
            },
            evidence_posture="active_meal_basis_read_only",
        )
    )

    result = asyncio.run(
        execute_intake_turn(
            db,
            user_external_id=user_external_id,
            raw_user_input="你是怎麼估的？你估的組成是什麼？",
            onboarding_payload=None,
            local_date=local_date,
            allow_search=False,
            manager_provider=provider,
            provider=provider,
        )
    )
    debug_payload = build_accurate_intake_debug_payload(db, user_external_id=user_external_id, local_date=local_date)

    assert result["manager_decision"]["intent_type"] == "answer_query"
    assert result["state_delta"]["canonical_commit"] is False
    assert result["state_delta"]["draft_saved"] is False
    assert result["intake_execution_manager"]["decision_1"] is None
    assert result["assistant_message"] == "answer_only"
    assert debug_payload["model"]["today_summary"]["consumed_kcal"] == 620
    assert db.query(MealThreadRecord).count() == 1
    assert db.query(MealVersionRecord).count() == 1
    assert provider.calls[0]["raw_user_input_seen_by_manager"] == "你是怎麼估的？你估的組成是什麼？"
    manager_packet = provider.calls[0]["manager_context_packet_v1"]
    assert isinstance(manager_packet, dict)
    meal_basis = manager_packet["active_day_state"]["active_meal_estimate_basis"]
    assert meal_basis["meal_thread_id"] == thread.id
    assert meal_basis["total_kcal"] == 620
    assert meal_basis["mutation_authority"] is False


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


def test_component_supplement_correction_replaces_default_active_meal_with_component_estimate(monkeypatch) -> None:
    monkeypatch.setenv("V2_INTAKE_TURN_ALLOW_STUB_ESTIMATE", "1")
    db = _session()
    user_external_id = "ux-semantic-component-refinement"
    local_date = "2026-05-02"
    _seed_body_plan(db, user_external_id=user_external_id, local_date=local_date)
    user = get_or_create_user(db, user_external_id)
    teppan_set = "\u65e9\u9910\u5e97\u9435\u677f\u9eb5\u5957\u9910"
    teppan_noodle = "\u9435\u677f\u9eb5"
    fried_egg = "\u8377\u5305\u86cb"
    pork_slices = "\u65e9\u9910\u5e97\u8c6c\u8089\u7247"
    initial = commit_meal_payload_to_canonical(
        db,
        user=user,
        candidate=CommitRequestCandidate(
            request_id="component-refinement-initial",
            manager_intent="food_estimation",
            version_reason="new_intake",
            meal_title=teppan_set,
            raw_input=teppan_set,
            estimated_kcal=400,
            protein_g=18,
            carb_g=42,
            fat_g=12,
            resolution_status="completed_meal",
            local_date=local_date,
            items=[
                MealItemPayload(
                    name=teppan_set,
                    quantity_hint="1 serving",
                    estimated_kcal=400,
                    protein_g=18,
                    carb_g=42,
                    fat_g=12,
                )
            ],
        ),
        budget_kcal=1800,
    )
    assert initial is not None
    old_item = db.execute(
        select(MealItemRecord).where(MealItemRecord.meal_version_id == initial.meal_version_id)
    ).scalar_one()
    target_attachment = {
        "mode": "target_committed_thread",
        "target_object_type": "meal_item",
        "target_object_id": str(old_item.id),
        "meal_thread_id": initial.meal_thread_id,
        "meal_item_id": old_item.id,
        "canonical_name": teppan_set,
        "correction_operation": "replace_item",
    }
    semantic_overrides = {
        "base_dish": teppan_set,
        "listed_items": [teppan_noodle, fried_egg, pork_slices],
        "retrieval_goal": "listed_item_lookup",
    }
    provider = ScriptedManagerDecisionProvider(
        entry=_final_payload(
            intent_type="correct_meal",
            current_turn_intent="correct_meal",
            final_action="correction_applied",
            workflow_effect="route_to_intake",
            mutation_intent_candidate="correction_write",
            target_attachment=target_attachment,
            evidence_posture="needs_tool_evidence",
            semantic_overrides=semantic_overrides,
        ),
        execution=[
            _final_payload(
                intent_type="correct_meal",
                current_turn_intent="correct_meal",
                final_action="correction_applied",
                workflow_effect="correction_applied",
                mutation_intent_candidate="correction_write",
                target_attachment=target_attachment,
                evidence_posture="tool_evidence_present",
                semantic_overrides=semantic_overrides,
            )
        ],
    )

    result = asyncio.run(
        execute_intake_turn(
            db,
            user_external_id=user_external_id,
            raw_user_input="\u6211\u525b\u525b\u7684\u65e9\u9910\u6709\u9435\u677f\u9eb5\u3001\u8377\u5305\u86cb\u548c\u8c6c\u8089\u7247",
            onboarding_payload=None,
            local_date=local_date,
            allow_search=False,
            manager_provider=provider,
            provider=provider,
        )
    )

    debug_payload = build_accurate_intake_debug_payload(db, user_external_id=user_external_id, local_date=local_date)
    active_version = debug_payload["model"]["meal_threads"][0]["active_version"]
    active_items = active_version["items"]

    assert result["manager_decision"]["intent_type"] == "correct_meal"
    assert result["state_delta"]["canonical_commit"] is True
    assert result["state_delta"]["old_version_superseded"] is True
    assert active_version["version_reason"] == "correction"
    assert active_version["total_kcal"] > 400
    assert debug_payload["model"]["today_summary"]["consumed_kcal"] == active_version["total_kcal"]
    assert [item["name"] for item in active_items] == [teppan_noodle, fried_egg, pork_slices]
    assert {round_info["tool_name"] for round_info in result["intake_execution_manager"]["manager_rounds"][0]["tool_results"]} == {
        "resolve_correction_target",
        "estimate_nutrition",
    }
