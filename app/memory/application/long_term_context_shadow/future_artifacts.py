from __future__ import annotations

from app.memory.application.long_term_context_shadow.catalog_artifacts import (
    _product_capability_context_map_artifact,
)
from app.memory.application.long_term_context_shadow.context_pack_artifacts import (
    _context_pack_token_pressure_shadow_artifact,
    _long_term_context_pack_shadow_artifact,
)
from app.memory.application.long_term_context_shadow.context_ingress_artifact import (
    _context_ingress_decision_shadow_artifact,
)
from app.memory.application.long_term_context_shadow.conversation_artifacts import (
    _conversation_recall_retrieval_shadow_artifact,
    _conversation_recall_shadow_artifact,
    _conversation_recall_tool_shadow_plan_artifact,
)
from app.memory.application.long_term_context_shadow.dependency_graph_artifact import (
    _memory_dependency_graph_shadow_artifact,
)
from app.memory.application.long_term_context_shadow.do_not_save_policy_artifact import (
    _memory_do_not_save_policy_shadow_artifact,
)
from app.memory.application.long_term_context_shadow.memory_architecture_artifacts import (
    _memory_extraction_storage_rag_artifact,
)
from app.memory.application.long_term_context_shadow.manager_memory_contracts import (
    _manager_memory_contract_shadow_artifact,
)
from app.memory.application.long_term_context_shadow.pre_compaction_flush_artifact import (
    _pre_compaction_memory_flush_shadow_artifact,
)
from app.memory.application.long_term_context_shadow.quality_artifacts import (
    _capability_scenario_fixture_pack_artifact,
    _context_quality_contradiction_review_artifact,
    _entity_normalization_shadow_artifact,
    _pr_review_autopilot_closeout_artifact,
)
from app.memory.application.long_term_context_shadow.retrieval_ranking_policy_artifact import (
    _retrieval_ranking_policy_shadow_artifact,
)
from app.memory.application.long_term_context_shadow.simulation_artifacts import (
    _memory_promotion_demotion_shadow_artifact,
    _memory_review_action_shadow_artifact,
    _proactive_no_send_artifact,
    _recommendation_shadow_artifact,
    _rescue_shadow_artifact,
    _semantic_pattern_extraction_shadow_artifact,
)


def build_future_shadow_artifacts(
    fixture: dict,
    candidates: list,
) -> dict[str, dict]:
    return {
        **_simulation_future_artifacts(fixture, candidates),
        **_conversation_future_artifacts(fixture, candidates),
        **_quality_future_artifacts(fixture, candidates),
        "long_term_context_pack_shadow_eval": _long_term_context_pack_shadow_artifact(
            fixture,
            candidates,
        ),
        "context_ingress_decision_shadow_eval": (
            _context_ingress_decision_shadow_artifact(fixture)
        ),
        "memory_extraction_storage_rag_shadow_plan": (
            _memory_extraction_storage_rag_artifact(fixture)
        ),
        "retrieval_ranking_policy_shadow_eval": (
            _retrieval_ranking_policy_shadow_artifact(fixture)
        ),
        "manager_memory_contract_shadow_plan": (
            _manager_memory_contract_shadow_artifact(fixture)
        ),
        "pre_compaction_memory_flush_shadow_plan": (
            _pre_compaction_memory_flush_shadow_artifact(fixture)
        ),
        "memory_do_not_save_policy_shadow_eval": (
            _memory_do_not_save_policy_shadow_artifact(fixture)
        ),
        "product_capability_context_map": _product_capability_context_map_artifact(
            fixture,
            candidates,
        ),
        "memory_dependency_graph_shadow_eval": (
            _memory_dependency_graph_shadow_artifact(fixture)
        ),
    }


def _simulation_future_artifacts(fixture: dict, candidates: list) -> dict[str, dict]:
    return {
        "context_pack_token_pressure_shadow_eval": (
            _context_pack_token_pressure_shadow_artifact(fixture, candidates)
        ),
        "proactive_no_send_simulation": _proactive_no_send_artifact(
            fixture, candidates
        ),
        "recommendation_shadow_eval": _recommendation_shadow_artifact(
            fixture, candidates
        ),
        "rescue_shadow_candidates": _rescue_shadow_artifact(fixture, candidates),
        "memory_review_action_shadow_result": _memory_review_action_shadow_artifact(
            fixture, candidates
        ),
        "memory_promotion_demotion_shadow_eval": (
            _memory_promotion_demotion_shadow_artifact(fixture, candidates)
        ),
        "semantic_pattern_extraction_shadow_plan": (
            _semantic_pattern_extraction_shadow_artifact(fixture)
        ),
    }


def _conversation_future_artifacts(
    fixture: dict,
    candidates: list,
) -> dict[str, dict]:
    return {
        "conversation_recall_shadow_eval": _conversation_recall_shadow_artifact(
            fixture, candidates
        ),
        "conversation_recall_tool_shadow_plan": (
            _conversation_recall_tool_shadow_plan_artifact(fixture, candidates)
        ),
        "conversation_recall_retrieval_shadow_eval": (
            _conversation_recall_retrieval_shadow_artifact(fixture, candidates)
        ),
    }


def _quality_future_artifacts(fixture: dict, candidates: list) -> dict[str, dict]:
    return {
        "entity_normalization_shadow_plan": _entity_normalization_shadow_artifact(
            fixture, candidates
        ),
        "context_quality_contradiction_review_queue": (
            _context_quality_contradiction_review_artifact(fixture, candidates)
        ),
        "capability_scenario_fixture_pack": _capability_scenario_fixture_pack_artifact(
            fixture, candidates
        ),
        "pr_review_autopilot_closeout": _pr_review_autopilot_closeout_artifact(fixture),
    }


__all__ = [
    "build_future_shadow_artifacts",
    "_capability_scenario_fixture_pack_artifact",
    "_context_pack_token_pressure_shadow_artifact",
    "_context_ingress_decision_shadow_artifact",
    "_context_quality_contradiction_review_artifact",
    "_conversation_recall_retrieval_shadow_artifact",
    "_conversation_recall_shadow_artifact",
    "_conversation_recall_tool_shadow_plan_artifact",
    "_entity_normalization_shadow_artifact",
    "_long_term_context_pack_shadow_artifact",
    "_memory_do_not_save_policy_shadow_artifact",
    "_manager_memory_contract_shadow_artifact",
    "_memory_dependency_graph_shadow_artifact",
    "_memory_extraction_storage_rag_artifact",
    "_memory_promotion_demotion_shadow_artifact",
    "_memory_review_action_shadow_artifact",
    "_pr_review_autopilot_closeout_artifact",
    "_pre_compaction_memory_flush_shadow_artifact",
    "_proactive_no_send_artifact",
    "_product_capability_context_map_artifact",
    "_recommendation_shadow_artifact",
    "_retrieval_ranking_policy_shadow_artifact",
    "_rescue_shadow_artifact",
    "_semantic_pattern_extraction_shadow_artifact",
]
