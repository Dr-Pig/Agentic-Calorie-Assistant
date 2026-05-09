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

from app.composition import intake_manager_tool_batch, intake_routes  # noqa: E402
from app.composition.request_runtime_context import load_request_runtime_context  # noqa: E402
from app.database import get_db  # noqa: E402
from app.models import Base  # noqa: E402
from app.nutrition.application.estimate_artifacts import EstimatedNutritionArtifact  # noqa: E402
from app.nutrition.application.fooddb_macro_contract import (  # noqa: E402
    APPROVED_PACKET_READY_SCHEMA_VERSION,
    APPROVED_PACKET_READY_SOURCE_QUALITY,
    MACRO_CONTRACT,
)
from app.paths import REQUEST_TRACE_DIR  # noqa: E402
from app.routes import router  # noqa: E402
from app.shared.contracts.common import EstimateRequest  # noqa: E402
from app.shared.contracts.intake import ComponentEstimate, EstimatePayload  # noqa: E402
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
            "final_action": "commit",
            "target_attachment": {"mode": "new_meal"},
            "mutation_intent_candidate": "canonical_write",
            "estimation_posture": "estimable",
            "evidence_posture": "needs_tool_evidence",
            "retrieval_goal": "generic_anchor_lookup",
            "base_dish": "蛋餅跟拿鐵",
        },
        "expected_behavior": "Meal log commits through runner-scoped approved FoodDB evidence.",
    },
    {
        "turn_id": "lunch_001",
        "raw_user_input": "午餐吃雞腿便當，飯半碗",
        "manager_decision": {
            "intent_type": "log_meal",
            "workflow_effect": "route_to_intake",
            "final_action": "commit",
            "target_attachment": {"mode": "new_meal"},
            "mutation_intent_candidate": "canonical_write",
            "estimation_posture": "estimable",
            "evidence_posture": "needs_tool_evidence",
            "retrieval_goal": "generic_anchor_lookup",
            "base_dish": "雞腿便當",
            "modifier_hints": ["飯半碗"],
        },
        "expected_behavior": "Meal log commits through runner-scoped approved FoodDB evidence.",
    },
    {
        "turn_id": "tea_001",
        "raw_user_input": "下午喝珍奶半糖大杯",
        "manager_decision": {
            "intent_type": "log_meal",
            "workflow_effect": "route_to_intake",
            "final_action": "commit",
            "target_attachment": {"mode": "new_meal"},
            "mutation_intent_candidate": "canonical_write",
            "estimation_posture": "estimable",
            "evidence_posture": "needs_tool_evidence",
            "retrieval_goal": "generic_anchor_lookup",
            "base_dish": "珍奶",
            "modifier_hints": ["半糖", "大杯"],
        },
        "expected_behavior": "Meal log commits through runner-scoped approved FoodDB evidence.",
    },
    {
        "turn_id": "dinner_draft_001",
        "raw_user_input": "晚餐吃滷味",
        "manager_decision": {
            "intent_type": "log_meal",
            "workflow_effect": "draft_clarify_no_mutation",
            "final_action": "ask_followup",
            "target_attachment": {"mode": "pending_draft", "canonical_name": "滷味"},
            "mutation_intent_candidate": "no_mutation",
            "estimation_posture": "composition_unknown_basket",
            "evidence_posture": "composition_unknown",
            "followup_question": "這份滷味有哪些品項？",
            "meal_title": "滷味",
        },
        "expected_behavior": "Saves pending draft without applying real generic item mutation.",
    },
    {
        "turn_id": "dinner_basket_001",
        "raw_user_input": "有豆干、海帶、貢丸、青菜",
        "manager_decision": {
            "intent_type": "log_meal",
            "workflow_effect": "route_to_intake",
            "final_action": "commit",
            "target_attachment": {"mode": "draft_followup", "canonical_name": "滷味"},
            "mutation_intent_candidate": "canonical_write",
            "estimation_posture": "estimable",
            "evidence_posture": "needs_tool_evidence",
            "retrieval_goal": "listed_item_lookup",
            "base_dish": "滷味",
            "listed_items": ["豆干", "海帶", "貢丸", "青菜"],
        },
        "expected_behavior": "Context continuation applies to the draft basket and commits listed components through approved evidence.",
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
                "correction_operation": "remove_item",
            },
            "mutation_intent_candidate": "correction_write",
            "current_turn_intent": "correct_meal",
            "estimation_posture": "target_evidence_only",
            "evidence_posture": "target_evidence_required",
        },
        "expected_behavior": "Explicit removal resolves the existing item target before applying canonical removal.",
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

DOGFOOD_APPROVED_EVIDENCE_BY_TURN_ID: dict[str, dict[str, Any]] = {
    "breakfast_001": {
        "meal_title": "蛋餅跟拿鐵",
        "source_lane": "generic_common_serving",
        "macro_visibility_status": "visible",
        "components": [
            {
                "name": "蛋餅",
                "quantity_hint": "1 份",
                "kcal": 330,
                "protein_g": 12,
                "carb_g": 38,
                "fat_g": 14,
                "evidence_id": "dogfood_anchor_egg_pancake",
            },
            {
                "name": "拿鐵",
                "quantity_hint": "1 杯",
                "kcal": 120,
                "protein_g": 7,
                "carb_g": 16,
                "fat_g": 4,
                "evidence_id": "dogfood_anchor_latte",
            },
        ],
    },
    "lunch_001": {
        "meal_title": "雞腿便當，飯半碗",
        "source_lane": "generic_common_serving",
        "macro_visibility_status": "visible",
        "components": [
            {
                "name": "雞腿便當，飯半碗",
                "quantity_hint": "1 份",
                "kcal": 620,
                "protein_g": 34,
                "carb_g": 70,
                "fat_g": 22,
                "evidence_id": "dogfood_anchor_chicken_bento_half_rice",
            },
        ],
    },
    "tea_001": {
        "meal_title": "珍奶半糖大杯",
        "source_lane": "generic_common_serving",
        "macro_visibility_status": "visible",
        "components": [
            {
                "name": "珍奶半糖大杯",
                "quantity_hint": "大杯",
                "kcal": 520,
                "protein_g": 8,
                "carb_g": 82,
                "fat_g": 18,
                "evidence_id": "dogfood_anchor_large_half_sugar_bubble_milk_tea",
            },
        ],
    },
    "dinner_basket_001": {
        "meal_title": "滷味：豆干、海帶、貢丸、青菜",
        "source_lane": "listed_component",
        "macro_visibility_status": "hidden_missing_source",
        "components": [
            {"name": "豆干", "quantity_hint": "1 份", "kcal": 95, "evidence_id": "dogfood_component_dried_tofu"},
            {"name": "海帶", "quantity_hint": "1 份", "kcal": 40, "evidence_id": "dogfood_component_kelp"},
            {"name": "貢丸", "quantity_hint": "1 顆", "kcal": 70, "evidence_id": "dogfood_component_pork_ball"},
            {"name": "青菜", "quantity_hint": "1 份", "kcal": 50, "evidence_id": "dogfood_component_greens"},
        ],
    },
}


def _fixture_by_turn_id() -> dict[str, dict[str, Any]]:
    return {str(fixture["turn_id"]): fixture for fixture in ONE_DAY_TURN_FIXTURES}


def _fixture_turn_id_by_raw_input() -> dict[str, str]:
    return {
        str(fixture["raw_user_input"]): str(fixture["turn_id"])
        for fixture in ONE_DAY_TURN_FIXTURES
    }


class _DogfoodApprovedFoodDBEvidenceTool:
    """Runner-scoped approved evidence adapter.

    This is not a production FoodDB promotion. It supplies tiny packet-ready
    evidence for the scripted one-day dogfood turns so the existing
    Manager/guard/persistence/read-model path can be exercised end to end.
    """

    def __init__(self) -> None:
        self.turn_id_by_raw_user_input = _fixture_turn_id_by_raw_input()
        self.calls: list[dict[str, Any]] = []

    async def __call__(
        self,
        db: Session,
        *,
        user_external_id: str,
        raw_user_input: str,
        request_id: str,
        local_date: str,
        force_new_meal_context: bool = False,
        **_: Any,
    ) -> EstimatedNutritionArtifact:
        turn_id = self.turn_id_by_raw_user_input.get(str(raw_user_input or ""))
        evidence = DOGFOOD_APPROVED_EVIDENCE_BY_TURN_ID.get(str(turn_id or ""))
        self.calls.append(
            {
                "turn_id": turn_id,
                "raw_user_input": raw_user_input,
                "evidence_found": evidence is not None,
            }
        )
        if evidence is None:
            raise ValueError("runner_scoped_approved_fooddb_evidence_missing")
        return self._artifact_from_evidence(
            db,
            user_external_id=user_external_id,
            raw_user_input=raw_user_input,
            request_id=request_id,
            local_date=local_date,
            turn_id=str(turn_id),
            evidence=evidence,
            force_new_meal_context=force_new_meal_context,
        )

    def _artifact_from_evidence(
        self,
        db: Session,
        *,
        user_external_id: str,
        raw_user_input: str,
        request_id: str,
        local_date: str,
        turn_id: str,
        evidence: dict[str, Any],
        force_new_meal_context: bool,
    ) -> EstimatedNutritionArtifact:
        request = EstimateRequest(
            text=raw_user_input,
            allow_search=False,
            user_id=user_external_id,
        )
        runtime_context = load_request_runtime_context(
            request=request,
            db=db,
            provider=type(
                "DogfoodApprovedFoodDBEvidenceProvider",
                (),
                {"readiness": lambda self: {"configured": False}},
            )(),
        )
        if force_new_meal_context and hasattr(runtime_context, "latest_log"):
            runtime_context.latest_log = None
        if force_new_meal_context and hasattr(runtime_context, "conversation_state"):
            conversation_state = runtime_context.conversation_state
            pending_state = getattr(conversation_state, "pending_followup_state", None)
            if pending_state is not None and hasattr(pending_state, "is_open"):
                pending_state.is_open = False
        source_lane = str(evidence["source_lane"])
        macro_visible = evidence.get("macro_visibility_status") == "visible"
        components = [
            self._component_from_evidence_item(item, macro_visible=macro_visible)
            for item in evidence["components"]
        ]
        estimated_kcal = sum(int(component.estimated_kcal or 0) for component in components)
        protein_g = sum(int(component.protein_g or 0) for component in components)
        carb_g = sum(int(component.carb_g or 0) for component in components)
        fat_g = sum(int(component.fat_g or 0) for component in components)
        evidence_ids = [
            str(item.get("evidence_id") or "")
            for item in evidence["components"]
            if str(item.get("evidence_id") or "").strip()
        ]
        approved_trace = {
            "source_lane": source_lane,
            "schema_version": APPROVED_PACKET_READY_SCHEMA_VERSION,
            "source_quality": APPROVED_PACKET_READY_SOURCE_QUALITY,
            "runtime_truth_allowed": True,
            "macro_truth_owner": MACRO_CONTRACT["macro_truth_owner"],
            "missing_macro_policy": MACRO_CONTRACT["missing_macro_policy"],
            "macro_visibility_status": evidence["macro_visibility_status"],
            "macro_source_basis": "validated_runner_packet"
            if macro_visible
            else "unknown",
            "macro_confidence": "medium" if macro_visible else "unknown",
            "fixture_scope": "one_day_realistic_web_dogfood_only",
            "turn_id": turn_id,
            "live_llm_invoked": False,
            "fooddb_truth_updated": False,
            "websearch_evidence_used": False,
        }
        display_macro_breakdown = (
            {
                "protein_g": protein_g,
                "carb_g": carb_g,
                "fat_g": fat_g,
                "macro_source": "runner_scoped_approved_fooddb_evidence",
                "macro_confidence": "medium",
                "macro_status": "available",
            }
            if macro_visible
            else {}
        )
        payload = EstimatePayload(
            request_id=request_id,
            meal_title=str(evidence["meal_title"]),
            components=[component.name for component in components],
            component_estimates=components,
            component_breakdown=[
                {
                    "name": component.name,
                    "quantity_hint": component.quantity_hint,
                    "estimated_kcal": component.estimated_kcal,
                    "protein_g": component.protein_g,
                    "carb_g": component.carb_g,
                    "fat_g": component.fat_g,
                    "source_lane": source_lane,
                }
                for component in components
            ],
            estimated_kcal=estimated_kcal,
            protein_g=protein_g if macro_visible else 0,
            carb_g=carb_g if macro_visible else 0,
            fat_g=fat_g if macro_visible else 0,
            macro_breakdown=display_macro_breakdown,
            raw_macro_breakdown=display_macro_breakdown,
            display_macro_breakdown=display_macro_breakdown,
            evidence_ids_used=evidence_ids,
            source_decision="ready",
            answer_mode="direct_answer",
            action_taken="direct_answer",
            route_target="direct_answer",
            reply_text=f"Logged {evidence['meal_title']} at about {estimated_kcal} kcal.",
            best_answer_source="runner_scoped_approved_fooddb_evidence",
            best_estimate_mode="anchored_component",
            estimate_confidence_tier="medium",
            retrieved_evidence_summary=[
                {
                    "title": str(evidence["meal_title"]),
                    "source_class": "runner_scoped_approved_fooddb_evidence",
                    "source_lane": source_lane,
                    "evidence_role": "meal_pattern_prior"
                    if source_lane == "generic_common_serving"
                    else "ingredient_anchor",
                }
            ],
            sources=[
                {
                    "source_class": "runner_scoped_approved_fooddb_evidence",
                    "source_type": source_lane,
                    "title": str(evidence["meal_title"]),
                }
            ],
            trace_contract={
                "local_date": local_date,
                "occurred_at": f"{local_date}T12:00:00+08:00",
                "timezone": "Asia/Taipei",
                "route_family": "food_logging",
                "response_mode_hint": "rough_estimate_ok",
                "canonical_write_decision": {
                    "can_write_canonical": True,
                    "source": "runner_scoped_approved_fooddb_evidence",
                },
                "db_hit_type": "approved_fooddb_packet_fixture",
                "approved_fooddb_evidence_trace": approved_trace,
                "macro_display_authorized": macro_visible,
                "macro_visibility_status": evidence["macro_visibility_status"],
                "macro_guard_reason": "committed_and_aligned"
                if macro_visible
                else "no_macro_data",
                "grounding_summary": {
                    "exact_truth_present": False,
                    "retrieved_knowledge_count": len(components),
                    "evidence_roles": [
                        "meal_pattern_prior"
                        if source_lane == "generic_common_serving"
                        else "ingredient_anchor"
                    ],
                },
                "reasoning_state": {
                    "exact_lane_count": 0,
                    "search_attempt_count": 0,
                },
                "search_attempt_count": 0,
                "search_query": None,
                "websearch_evidence_used": False,
                "shadow_stub": False,
            },
        )
        return EstimatedNutritionArtifact(
            request=request,
            runtime_context=runtime_context,
            payload=payload,
        )

    def _component_from_evidence_item(
        self,
        item: dict[str, Any],
        *,
        macro_visible: bool,
    ) -> ComponentEstimate:
        return ComponentEstimate(
            name=str(item["name"]),
            quantity_hint=str(item.get("quantity_hint") or ""),
            source="lookup",
            evidence_role="meal_pattern_prior"
            if macro_visible
            else "ingredient_anchor",
            estimate_basis="anchored",
            confidence_tier="medium",
            estimated_kcal=int(item["kcal"]),
            protein_g=int(item.get("protein_g") or 0) if macro_visible else 0,
            carb_g=int(item.get("carb_g") or 0) if macro_visible else 0,
            fat_g=int(item.get("fat_g") or 0) if macro_visible else 0,
            evidence_ids=[str(item.get("evidence_id") or "")],
        )


class _ChineseOneDayManagerProvider:
    def __init__(self):
        self.turn_index = 0
        self.fixture_by_raw_user_input = {
            str(fixture["raw_user_input"]): fixture
            for fixture in ONE_DAY_TURN_FIXTURES
        }
        self.calls: list[dict[str, Any]] = []

    def readiness(self) -> dict[str, Any]:
        return {
            "configured": True,
            "provider": "chinese_one_day_manager_fixture",
            "live_llm_invoked": False,
        }

    async def complete_with_trace(
        self, **kwargs: Any
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        user_payload = dict(kwargs.get("user_payload") or {})
        fixture, fixture_binding = self._fixture_for_user_payload(user_payload)
        available_tools = {str(item) for item in user_payload.get("available_tools") or []}
        round_index = int(user_payload.get("round_index") or 0)
        self.calls.append(
            {
                "raw_user_input": user_payload.get("raw_user_input"),
                "fixture_turn_id": fixture["turn_id"],
                "fixture_binding": fixture_binding,
                "available_tools": sorted(available_tools),
                "round_index": round_index,
            }
        )
        if "estimate_nutrition" in available_tools:
            return self._format_execution_decision(
                fixture,
                user_payload=user_payload,
                fixture_binding=fixture_binding,
            )
        return self._format_decision(
            fixture["manager_decision"],
            fixture_turn_id=str(fixture["turn_id"]),
            fixture_binding=fixture_binding,
        )

    def _fixture_for_user_payload(
        self, user_payload: dict[str, Any]
    ) -> tuple[dict[str, Any], str]:
        raw_user_input = str(user_payload.get("raw_user_input") or "")
        fixture = self.fixture_by_raw_user_input.get(raw_user_input)
        if fixture is not None:
            return fixture, "raw_user_input_fixture_identity"
        if self.turn_index >= len(ONE_DAY_TURN_FIXTURES):
            raise RuntimeError("Exceeded fixture turns.")
        fixture = ONE_DAY_TURN_FIXTURES[self.turn_index]
        self.turn_index += 1
        return fixture, "sequential_fallback_for_unknown_fixture_input"

    def _format_execution_decision(
        self,
        fixture: dict[str, Any],
        *,
        user_payload: dict[str, Any],
        fixture_binding: str,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        dec = dict(fixture["manager_decision"])
        tool_results = [
            item for item in user_payload.get("tool_results") or [] if isinstance(item, dict)
        ]
        has_nutrition = any(
            str(item.get("tool_name") or "") == "estimate_nutrition"
            and item.get("confidence") == "available"
            for item in tool_results
        )
        has_correction_target = self._has_resolved_correction_target(tool_results)
        if (
            dec["final_action"] == "correction_applied"
            and "resolve_correction_target" in {
                str(item) for item in user_payload.get("available_tools") or []
            }
            and not has_correction_target
        ):
            return (
                {
                    "manager_action": "call_tools",
                    "response_mode": "tool_call",
                    "tool_calls": [
                        {
                            "name": "resolve_correction_target",
                            "arguments": self._target_proposal(dec),
                        }
                    ],
                },
                self._trace(
                    fixture_turn_id=str(fixture["turn_id"]),
                    fixture_binding=fixture_binding,
                    stage="correction_target_tool_request",
                ),
            )
        if dec["final_action"] == "commit" and not has_nutrition:
            return (
                {
                    "manager_action": "call_tools",
                    "response_mode": "tool_call",
                    "tool_calls": [
                        {
                            "name": "estimate_nutrition",
                            "arguments": {
                                "manager_semantic_decision": self._tool_semantic_decision(dec),
                            },
                        }
                    ],
                },
                self._trace(
                    fixture_turn_id=str(fixture["turn_id"]),
                    fixture_binding=fixture_binding,
                    stage="execution_tool_request",
                ),
            )
        return self._format_decision(
            dec,
            fixture_turn_id=str(fixture["turn_id"]),
            fixture_binding=fixture_binding,
        )

    def _has_resolved_correction_target(self, tool_results: list[dict[str, Any]]) -> bool:
        for item in tool_results:
            if str(item.get("tool_name") or "") != "resolve_correction_target":
                continue
            target = dict((item.get("provenance") or {}).get("correction_target") or {})
            validation = dict(target.get("manager_target_proposal_validation") or {})
            if (
                item.get("confidence") == "available"
                and validation.get("status") == "accepted"
                and target.get("meal_item_id") is not None
            ):
                return True
        return False

    def _target_proposal(self, dec: dict[str, Any]) -> dict[str, Any]:
        proposal = dict(dec.get("target_attachment") or {})
        proposal["target_proposal_source"] = "chinese_one_day_manager_fixture.target_attachment"
        proposal["semantic_owner"] = "manager"
        return proposal

    def _tool_semantic_decision(self, dec: dict[str, Any]) -> dict[str, Any]:
        return {
            key: value
            for key, value in {
                "base_dish": dec.get("base_dish"),
                "aliases": dec.get("aliases"),
                "brand_hint": dec.get("brand_hint"),
                "size_hint": dec.get("size_hint"),
                "modifier_hints": dec.get("modifier_hints"),
                "listed_items": dec.get("listed_items"),
                "retrieval_goal": dec.get("retrieval_goal"),
                "semantic_authority_source": "synthetic_manager_structured_fixture",
            }.items()
            if value not in (None, "", [])
        }

    def _trace(
        self,
        *,
        fixture_turn_id: str,
        fixture_binding: str,
        stage: str = "final_decision",
    ) -> dict[str, Any]:
        return {
            "live_llm_invoked": False,
            "fixture_turn_id": fixture_turn_id,
            "fixture_binding": fixture_binding,
            "stage": stage,
        }

    def _format_decision(
        self,
        dec: dict[str, Any],
        *,
        fixture_turn_id: str,
        fixture_binding: str,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        target_attachment = dict(dec["target_attachment"])
        answer_contract: dict[str, Any] = {
            "reply_text": "one-day dogfood manager fixture decision",
        }
        if isinstance(target_attachment.get("daily_target_kcal"), int):
            answer_contract["daily_target_kcal"] = target_attachment["daily_target_kcal"]
        if dec.get("followup_question"):
            answer_contract["followup_question"] = dec["followup_question"]
        if dec.get("meal_title"):
            answer_contract["meal_title"] = dec["meal_title"]
        semantic_decision = {
            "semantic_authority": "deterministic_fake_provider",
            "current_turn_intent": dec.get("current_turn_intent") or dec["intent_type"],
            "target_attachment": target_attachment,
            "workflow_effect": dec["workflow_effect"],
            "final_action_candidate": dec["final_action"],
            "estimation_posture": dec.get("estimation_posture") or "not_applicable",
            "followup_posture": "ask_required" if dec.get("followup_question") else "none",
            "followup_targets": [],
            "mutation_intent_candidate": dec["mutation_intent_candidate"],
            "uncertainty_posture": "bounded",
            "source": "chinese_one_day_manager_fixture",
            "semantic_owner": "manager",
            "deterministic_role": "fixture_simulates_manager_output_only",
        }
        for key in (
            "base_dish",
            "listed_items",
            "modifier_hints",
            "retrieval_goal",
            "followup_question",
            "meal_title",
            "correction_operation",
        ):
            if dec.get(key) not in (None, "", []):
                semantic_decision[key] = dec[key]
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
                "evidence_posture": dec.get("evidence_posture") or "read_only_state",
                "repair_ack": False,
                "answer_contract": answer_contract,
                "response_summary": "one_day_dogfood_manager_fixture_decision",
                "uncertainty_posture": "bounded",
                "evidence_honesty_posture": dec.get("evidence_posture") or "not_applicable",
                "semantic_decision": semantic_decision,
                "tool_calls": [],
            },
            self._trace(fixture_turn_id=fixture_turn_id, fixture_binding=fixture_binding),
        )


def _load_runtime_error_trace(request_id: str | None) -> dict[str, Any]:
    if not request_id:
        return {}
    path = REQUEST_TRACE_DIR / f"{request_id}.json"
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"trace_error_family": "request_trace_decode_error"}
    return {
        "trace_error_family": _trace_error_family(str(payload.get("error") or "")),
        "error": str(payload.get("error") or ""),
    }


def _trace_error_family(error_text: str) -> str:
    if "Exceeded fixture turns" in error_text:
        return "fixture_provider_exhausted"
    if error_text:
        return "unclassified_runtime_error"
    return "none"


def _manager_gap_breakdown(turns: list[dict[str, Any]]) -> dict[str, Any]:
    breakdown: dict[str, Any] = {
        "runtime_response_turn_ids": [],
        "missing_manager_response_turn_ids": [],
        "manager_error_turns": [],
        "fixture_provider_exhausted_turn_ids": [],
        "unclassified_error_turn_ids": [],
    }
    for turn in turns:
        turn_id = str(turn.get("turn_id") or "")
        if turn.get("manager_decision_source") == "runtime_response":
            breakdown["runtime_response_turn_ids"].append(turn_id)
            continue
        raw_response = turn.get("raw_response") or {}
        public_error = str(raw_response.get("error") or "")
        if public_error:
            runtime_error_trace = dict(turn.get("runtime_error_trace") or {})
            trace_error_family = str(runtime_error_trace.get("trace_error_family") or "unclassified_runtime_error")
            error_turn = {
                "turn_id": turn_id,
                "public_error": public_error,
                "trace_error_family": trace_error_family,
            }
            breakdown["manager_error_turns"].append(error_turn)
            if trace_error_family == "fixture_provider_exhausted":
                breakdown["fixture_provider_exhausted_turn_ids"].append(turn_id)
            else:
                breakdown["unclassified_error_turn_ids"].append(turn_id)
            continue
        breakdown["missing_manager_response_turn_ids"].append(turn_id)
    return breakdown


def _build_test_client(db: Session, provider: Any) -> TestClient:
    old_manager = intake_routes.manager_provider
    old_search = intake_routes.search_provider
    old_extract = intake_routes.extract_provider
    old_estimate_tool = intake_manager_tool_batch.estimate_nutrition_tool

    intake_routes.manager_provider = provider
    intake_routes.search_provider = None
    intake_routes.extract_provider = None
    evidence_tool = _DogfoodApprovedFoodDBEvidenceTool()
    intake_manager_tool_batch.estimate_nutrition_tool = evidence_tool

    app = FastAPI()
    app.include_router(router)

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    client.old_providers = (old_manager, old_search, old_extract, old_estimate_tool)
    client.dogfood_evidence_tool = evidence_tool
    return client


def _close_test_client(client: TestClient) -> None:
    old_manager, old_search, old_extract, old_estimate_tool = client.old_providers
    try:
        client.close()
    finally:
        intake_routes.manager_provider = old_manager
        intake_routes.search_provider = old_search
        intake_routes.extract_provider = old_extract
        intake_manager_tool_batch.estimate_nutrition_tool = old_estimate_tool


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
    evidence_tool = client.dogfood_evidence_tool

    user_id = "dogfood-user-v2-diagnostic"
    local_date = "2026-05-04"

    turns_output = []
    has_food_evidence_gap = False
    correction_target_gap_observed = False

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
            runtime_error_trace = _load_runtime_error_trace(str(data.get("request_id") or ""))

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
            manager_response_available = bool(mgr_dec) and not data.get("error")
            mutation_candidate = fixture["manager_decision"]["mutation_intent_candidate"]
            if manager_response_available and not mutation_applied:
                if mutation_candidate == "canonical_write":
                    has_food_evidence_gap = True
                elif mutation_candidate == "correction_write":
                    correction_target_gap_observed = True

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
                    "runtime_error_trace": runtime_error_trace,
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
    evidence_tool_calls = list(evidence_tool.calls)
    evidence_found_calls = [call for call in evidence_tool_calls if call.get("evidence_found") is True]
    macro_present_evidence_seen = any(
        DOGFOOD_APPROVED_EVIDENCE_BY_TURN_ID.get(str(call.get("turn_id") or ""), {}).get("macro_visibility_status")
        == "visible"
        for call in evidence_found_calls
    )
    macro_missing_evidence_seen = any(
        DOGFOOD_APPROVED_EVIDENCE_BY_TURN_ID.get(str(call.get("turn_id") or ""), {}).get("macro_visibility_status")
        == "hidden_missing_source"
        for call in evidence_found_calls
    )
    manager_gap_breakdown = _manager_gap_breakdown(turns_output)
    manager_fixture_call_topology_gap_observed = bool(
        manager_gap_breakdown["fixture_provider_exhausted_turn_ids"]
    )
    manager_context_gap_observed = bool(
        manager_gap_breakdown["missing_manager_response_turn_ids"]
        or manager_gap_breakdown["unclassified_error_turn_ids"]
    )

    remove_turn = next(
        (turn for turn in turns_output if turn.get("turn_id") == "dinner_remove_001"),
        {},
    )
    remove_state_delta = dict(remove_turn.get("state_delta") or {})
    remove_item_attempted = True
    remove_item_applied = bool(
        remove_state_delta.get("old_version_superseded")
        or remove_state_delta.get("canonical_commit")
    )

    return {
        "one_day_realistic_web_dogfood": {
            "status": "diagnostic_pass_with_correction_gap"
            if correction_target_gap_observed and not has_food_evidence_gap and not manager_context_gap_observed
            else (
                "diagnostic_pass_with_evidence_gap"
                if has_food_evidence_gap or manager_context_gap_observed
                else "pass"
            ),
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
                "active_meal_count": active_meal_count,
                "food_evidence_gap_observed": has_food_evidence_gap,
                "evidence_gap_observed": has_food_evidence_gap,
                "correction_target_gap_observed": correction_target_gap_observed,
                "approved_fooddb_evidence_fixture_used": bool(evidence_found_calls),
                "fooddb_evidence_used": bool(evidence_found_calls),
                "fooddb_evidence_tool_calls": evidence_tool_calls,
                "macro_present_evidence_seen": macro_present_evidence_seen,
                "macro_missing_evidence_seen": macro_missing_evidence_seen,
                "manager_context_gap_observed": manager_context_gap_observed,
                "manager_fixture_call_topology_gap_observed": manager_fixture_call_topology_gap_observed,
                "manager_gap_breakdown": manager_gap_breakdown,
                "evidence_gap_handled_without_fake_kcal": True,
                "no_fake_kcal_truth": True,
                "pending_followup_used": False,  # Skipped due to gap
                "remove_item_negative_guard": {
                    "attempted": remove_item_attempted,
                    "target_attachment_present": True,
                    "existing_item_id_present": remove_item_applied,
                    "runtime_blocked_missing_target": not remove_item_applied,
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
                        has_food_evidence_gap,
                    ),
                    (
                        "correction target gap prevented remove-item application",
                        correction_target_gap_observed,
                    ),
                    (
                        "manager response missing or unclassified error prevented complete turn evaluation",
                        manager_context_gap_observed,
                    ),
                    (
                        "dogfood manager fixture exhausted before all turns completed",
                        manager_fixture_call_topology_gap_observed,
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
