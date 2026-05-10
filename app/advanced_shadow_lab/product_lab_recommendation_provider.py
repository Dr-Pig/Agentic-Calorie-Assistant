from __future__ import annotations

from typing import Any, Mapping

from app.advanced_shadow_lab.product_lab_recommendation_ux import (
    build_recommendation_ux_packet,
)


class FixtureProductLabRecommendationProvider:
    provider_name = "fixture_product_lab_llm"
    planning_model_profile = "fast_router_model"
    offer_model_profile = "strict_reasoner_or_response_writer_model"

    def profile(self) -> dict[str, Any]:
        return {
            "provider_name": self.provider_name,
            "planning_model_profile": self.planning_model_profile,
            "offer_model_profile": self.offer_model_profile,
            "model_dependency_inverted": True,
        }

    def plan(
        self,
        *,
        turn: Mapping[str, Any],
        fixture_inputs: Mapping[str, Any],
        memory_context_pack: Mapping[str, Any],
    ) -> dict[str, Any]:
        payload = _mapping(fixture_inputs.get("recommendation_payload"))
        remaining = _remaining_kcal(payload)
        selected_refs = [
            str(record_id)
            for record_id in memory_context_pack.get("selected_record_ids") or []
        ]
        return {
            "node": "recommendation_planning",
            "owner": "llm_fixture_provider",
            "model_profile": self.planning_model_profile,
            "recommendation_context_result": {
                "user_goal": str(turn.get("semantic_intent_fixture") or ""),
                "soft_preferences": selected_refs,
                "budget_posture": {
                    "remaining_kcal": remaining,
                    "already_logged_kcal": _already_logged_kcal(fixture_inputs),
                },
                "raw_user_text_semantic_inference_performed": False,
            },
            "candidate_spec": {
                "desired_source_types": [
                    "memory_golden_order",
                    "golden_order",
                    "nearby_fixture",
                    "safe_fallback",
                ],
                "memory_record_refs": selected_refs,
                "budget_posture": {
                    "remaining_kcal": remaining,
                    "max_candidate_kcal": remaining,
                },
                "hard_blockers_must_be_deterministic": True,
            },
            "blockers": [],
        }

    def synthesize_offer(
        self,
        *,
        retrieval_guard_scoring: Mapping[str, Any],
    ) -> dict[str, Any]:
        allowed = [
            item
            for item in retrieval_guard_scoring.get("qualified_candidates") or []
            if isinstance(item, Mapping)
        ]
        if not allowed:
            return {
                "node": "offer_synthesis",
                "owner": "llm_fixture_provider",
                "model_profile": self.offer_model_profile,
                "status": "omitted",
                "offer_model_invoked": False,
                "no_qualified_candidate": True,
                "ranking_result": {
                    "pool_decision": "silent_no_qualified_candidate",
                    "ranked_candidate_ids": [],
                    "selected_primary": "",
                    "backup_candidate_ids": [],
                },
                "recommendation_response_result": {
                    "surface": "chat",
                    "response_packet_owner": "offer_synthesis",
                    "omission_reason": "no_qualified_candidate",
                },
                "blockers": [],
            }
        selected_id = str(retrieval_guard_scoring.get("primary_candidate_id") or "")
        primary = _candidate_by_id(allowed, selected_id) or dict(allowed[0])
        backups = [
            dict(candidate)
            for candidate_id in retrieval_guard_scoring.get("backup_candidate_ids") or []
            if (candidate := _candidate_by_id(allowed, str(candidate_id)))
        ]
        public_primary = _public_candidate(primary)
        public_backups = [_public_candidate(item) for item in backups]
        explanation = _explanation(primary)
        backup_ids = [str(item.get("candidate_id") or "") for item in backups]
        return {
            "node": "offer_synthesis",
            "owner": "llm_fixture_provider",
            "model_profile": self.offer_model_profile,
            "status": "pass",
            "offer_model_invoked": True,
            "no_qualified_candidate": False,
            "selected_primary": public_primary,
            "backup_candidates": public_backups,
            "ranking_result": {
                "pool_decision": str(retrieval_guard_scoring.get("pool_decision") or ""),
                "ranked_candidate_ids": [
                    str(item.get("candidate_id") or "") for item in allowed
                ],
                "selected_primary": str(primary.get("candidate_id") or ""),
                "backup_candidate_ids": backup_ids,
            },
            "recommendation_response_result": {
                "surface": "chat",
                "explanation": explanation,
                "response_packet_owner": "offer_synthesis",
            },
            "ux_packet": build_recommendation_ux_packet(
                primary_candidate=public_primary,
                backup_candidates=public_backups,
                explanation=explanation,
            ),
            "blockers": [],
        }


def _public_candidate(candidate: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "candidate_id": str(candidate.get("candidate_id") or ""),
        "title": str(candidate.get("title") or ""),
        "source_type": str(candidate.get("source_type") or ""),
        "estimated_kcal_range": dict(_mapping(candidate.get("estimated_kcal_range"))),
        "quality_score": int(candidate.get("quality_score") or 0),
        "quality_tier": str(candidate.get("quality_tier") or ""),
        "proactive_intensity": str(candidate.get("proactive_intensity") or ""),
        "source_refs": [str(ref) for ref in candidate.get("source_refs") or []],
    }


def _explanation(candidate: Mapping[str, Any]) -> str:
    title = str(candidate.get("title") or "this option")
    return f"{title} fits the current budget and remembered preference context."


def _remaining_kcal(payload: Mapping[str, Any]) -> int | None:
    value = _mapping(payload.get("current_budget_view")).get("remaining_kcal")
    return value if isinstance(value, int) else None


def _already_logged_kcal(fixture_inputs: Mapping[str, Any]) -> int | None:
    value = _mapping(fixture_inputs.get("current_budget_view")).get(
        "meal_consumption_total_kcal"
    )
    return value if isinstance(value, int) else None


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _candidate_by_id(
    candidates: list[Mapping[str, Any]],
    candidate_id: str,
) -> dict[str, Any] | None:
    for candidate in candidates:
        if str(candidate.get("candidate_id") or "") == candidate_id:
            return dict(candidate)
    return None


__all__ = ["FixtureProductLabRecommendationProvider"]
