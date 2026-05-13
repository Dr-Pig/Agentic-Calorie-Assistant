from __future__ import annotations

from typing import Any, Mapping

from app.recommendation.application.offer_synthesis_fixture_parts import (
    candidate_by_id,
    candidate_explanation,
    contract_blockers,
    empty_ranking,
    public_candidate,
    ranking,
    ux_packet,
)


INPUT_CONTRACT = {
    "allowed_pool_trace_required": True,
    "may_retrieve_candidates": False,
    "may_apply_hard_blockers": False,
    "may_mutate_canonical_truth": False,
    "raw_transcript_allowed": False,
}


class FixtureRecommendationOfferSynthesisProvider:
    def __init__(self, *, model_profile: str) -> None:
        self.model_profile = model_profile

    def synthesize(self, *, retrieval_guard_scoring: Mapping[str, Any]) -> dict[str, Any]:
        allowed = [
            item
            for item in retrieval_guard_scoring.get("qualified_candidates") or []
            if isinstance(item, Mapping)
        ]
        if not allowed:
            return {
                **_base(self.model_profile),
                "status": "omitted",
                "offer_model_invoked": False,
                "no_qualified_candidate": True,
                "ranking_result": empty_ranking(),
                "recommendation_response_result": {
                    "surface": "chat",
                    "response_packet_owner": "offer_synthesis",
                    "omission_reason": "no_qualified_candidate",
                },
                "blockers": contract_blockers(retrieval_guard_scoring),
            }
        selected_id = str(retrieval_guard_scoring.get("primary_candidate_id") or "")
        primary = candidate_by_id(allowed, selected_id) or dict(allowed[0])
        backups = [
            dict(candidate)
            for candidate_id in retrieval_guard_scoring.get("backup_candidate_ids") or []
            if (candidate := candidate_by_id(allowed, str(candidate_id)))
        ]
        public_primary = public_candidate(primary)
        public_backups = [public_candidate(item) for item in backups]
        explanation = candidate_explanation(primary)
        return {
            **_base(self.model_profile),
            "status": "pass",
            "offer_model_invoked": True,
            "no_qualified_candidate": False,
            "selected_primary": public_primary,
            "backup_candidates": public_backups,
            "ranking_result": ranking(retrieval_guard_scoring, allowed, primary, backups),
            "recommendation_response_result": {
                "surface": "chat",
                "explanation": explanation,
                "response_packet_owner": "offer_synthesis",
            },
            "ux_packet": ux_packet(
                retrieval_guard_scoring=retrieval_guard_scoring,
                primary_candidate=primary,
                public_primary=public_primary,
                public_backups=public_backups,
                explanation=explanation,
            ),
            "blockers": contract_blockers(retrieval_guard_scoring),
        }


def _base(model_profile: str) -> dict[str, Any]:
    return {
        "node": "offer_synthesis",
        "owner": "llm_fixture_provider",
        "provider_module": "app.recommendation.application.offer_synthesis_fixture_provider",
        "model_profile": model_profile,
        "input_contract": dict(INPUT_CONTRACT),
    }

__all__ = ["FixtureRecommendationOfferSynthesisProvider"]
