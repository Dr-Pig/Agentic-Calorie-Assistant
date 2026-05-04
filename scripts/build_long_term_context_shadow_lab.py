from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.memory.application.external_memory_framework_research import (  # noqa: E402
    build_external_memory_framework_research,
)
from app.memory.application.local_memory_framework_review import (  # noqa: E402
    build_local_framework_deep_review,
    build_local_framework_review,
)
from app.memory.application.long_term_context_shadow_lab import (  # noqa: E402
    build_artifact_registry_manifest,
    build_shadow_lab_artifacts,
)
from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact  # noqa: E402


ARTIFACT_FILENAMES = {
    "artifact_registry_manifest": "artifact_registry_manifest.json",
    "long_term_memory_candidate_review": "long_term_memory_candidate_review.json",
    "context_value_review_queue": "context_value_review_queue.json",
    "context_signal_quality_scorecard": "context_signal_quality_scorecard.json",
    "candidate_extraction_engine_v2": "candidate_extraction_engine_v2.json",
    "derived_memory_views_shadow_eval": "derived_memory_views_shadow_eval.json",
    "context_signal_lifecycle_shadow_eval": (
        "context_signal_lifecycle_shadow_eval.json"
    ),
    "user_context_profile_shadow_eval": "user_context_profile_shadow_eval.json",
    "scope_isolation_shadow_eval": "scope_isolation_shadow_eval.json",
    "proactive_intelligence_shadow_eval": "proactive_intelligence_shadow_eval.json",
    "contextual_friction_budget_shadow_eval": (
        "contextual_friction_budget_shadow_eval.json"
    ),
    "menu_highlight_shadow_eval": "menu_highlight_shadow_eval.json",
    "consumer_memory_substrate_shadow_eval": (
        "consumer_memory_substrate_shadow_eval.json"
    ),
    "context_value_scoring_v2": "context_value_scoring_v2.json",
    "shadow_replay_evaluators": "shadow_replay_evaluators.json",
    "review_queue_reducer": "review_queue_reducer.json",
    "context_pack_token_pressure_shadow_eval": (
        "context_pack_token_pressure_shadow_eval.json"
    ),
    "proactive_no_send_simulation": "proactive_no_send_simulation.json",
    "recommendation_shadow_eval": "recommendation_shadow_eval.json",
    "rescue_shadow_candidates": "rescue_shadow_candidates.json",
    "memory_review_action_shadow_result": "memory_review_action_shadow_result.json",
    "memory_promotion_demotion_shadow_eval": (
        "memory_promotion_demotion_shadow_eval.json"
    ),
    "semantic_pattern_extraction_shadow_plan": (
        "semantic_pattern_extraction_shadow_plan.json"
    ),
    "conversation_recall_shadow_eval": "conversation_recall_shadow_eval.json",
    "conversation_recall_tool_shadow_plan": "conversation_recall_tool_shadow_plan.json",
    "conversation_recall_retrieval_shadow_eval": (
        "conversation_recall_retrieval_shadow_eval.json"
    ),
    "entity_normalization_shadow_plan": "entity_normalization_shadow_plan.json",
    "context_quality_contradiction_review_queue": (
        "context_quality_contradiction_review_queue.json"
    ),
    "capability_scenario_fixture_pack": "capability_scenario_fixture_pack.json",
    "pr_review_autopilot_closeout": "pr_review_autopilot_closeout.json",
    "long_term_context_pack_shadow_eval": "long_term_context_pack_shadow_eval.json",
    "context_ingress_decision_shadow_eval": (
        "context_ingress_decision_shadow_eval.json"
    ),
    "memory_extraction_storage_rag_shadow_plan": (
        "memory_extraction_storage_rag_shadow_plan.json"
    ),
    "retrieval_ranking_policy_shadow_eval": (
        "retrieval_ranking_policy_shadow_eval.json"
    ),
    "manager_memory_contract_shadow_plan": "manager_memory_contract_shadow_plan.json",
    "product_capability_context_map": "product_capability_context_map.json",
    "memory_dependency_graph_shadow_eval": "memory_dependency_graph_shadow_eval.json",
    "external_memory_framework_research_review": (
        "external_memory_framework_research_review.json"
    ),
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build fixture-only Long-Term Context Shadow Lab artifacts."
    )
    parser.add_argument(
        "--fixture-json", required=True, help="Fixture-only dogfood export JSON."
    )
    parser.add_argument("--output-dir", default="artifacts")
    parser.add_argument(
        "--local-framework-root",
        default=None,
        help="Optional local framework checkout root for read-only review.",
    )
    args = parser.parse_args(argv)

    fixture = read_json_artifact(Path(args.fixture_json))
    output_dir = Path(args.output_dir)
    artifacts = build_shadow_lab_artifacts(fixture)
    artifacts["external_memory_framework_research_review"] = (
        build_external_memory_framework_research(
            generated_at_utc=str(
                fixture.get("generated_at_utc") or "1970-01-01T00:00:00+00:00"
            )
        )
    )

    if args.local_framework_root:
        artifacts["local_memory_framework_review"] = build_local_framework_review(
            Path(args.local_framework_root)
        )
        artifacts["local_memory_framework_deep_review"] = (
            build_local_framework_deep_review(Path(args.local_framework_root))
        )

    artifacts["artifact_registry_manifest"] = build_artifact_registry_manifest(
        fixture,
        artifacts,
    )

    for artifact_key, filename in ARTIFACT_FILENAMES.items():
        write_json_artifact(output_dir / filename, artifacts[artifact_key])

    if args.local_framework_root:
        write_json_artifact(
            output_dir / "local_memory_framework_review.json",
            artifacts["local_memory_framework_review"],
        )
        write_json_artifact(
            output_dir / "local_memory_framework_deep_review.json",
            artifacts["local_memory_framework_deep_review"],
        )

    print(
        json.dumps(
            {
                "status": "generated",
                "output_dir": str(output_dir),
                "artifact_count": len(ARTIFACT_FILENAMES)
                + (2 if args.local_framework_root else 0),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
