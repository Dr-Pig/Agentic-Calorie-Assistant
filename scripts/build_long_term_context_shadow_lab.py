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
    build_local_framework_review,
)
from app.memory.application.long_term_context_shadow_lab import (  # noqa: E402
    build_shadow_lab_artifacts,
)
from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact  # noqa: E402


ARTIFACT_FILENAMES = {
    "long_term_memory_candidate_review": "long_term_memory_candidate_review.json",
    "context_value_review_queue": "context_value_review_queue.json",
    "proactive_no_send_simulation": "proactive_no_send_simulation.json",
    "recommendation_shadow_eval": "recommendation_shadow_eval.json",
    "rescue_shadow_candidates": "rescue_shadow_candidates.json",
    "memory_review_action_shadow_result": "memory_review_action_shadow_result.json",
    "conversation_recall_shadow_eval": "conversation_recall_shadow_eval.json",
    "conversation_recall_tool_shadow_plan": "conversation_recall_tool_shadow_plan.json",
    "long_term_context_pack_shadow_eval": "long_term_context_pack_shadow_eval.json",
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

    for artifact_key, filename in ARTIFACT_FILENAMES.items():
        write_json_artifact(output_dir / filename, artifacts[artifact_key])

    if args.local_framework_root:
        framework_review = build_local_framework_review(Path(args.local_framework_root))
        write_json_artifact(
            output_dir / "local_memory_framework_review.json", framework_review
        )

    print(
        json.dumps(
            {
                "status": "generated",
                "output_dir": str(output_dir),
                "artifact_count": len(ARTIFACT_FILENAMES)
                + (1 if args.local_framework_root else 0),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
