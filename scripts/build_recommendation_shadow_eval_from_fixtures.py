from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.recommendation.application.shadow_artifact_gate import (  # noqa: E402
    evaluate_recommendation_shadow_artifact_quality,
)
from app.recommendation.application.shadow_evaluator import (  # noqa: E402
    build_recommendation_shadow_eval_artifact,
)
from app.recommendation.application.shadow_fixture_import import (  # noqa: E402
    RecommendationShadowFixtureImportError,
    load_recommendation_shadow_context_fixtures,
)


DEFAULT_OUTPUT = ROOT / "artifacts" / "recommendation_shadow_eval.json"


def build_recommendation_shadow_eval_from_fixture_file(
    fixture_path: Path,
    output_path: Path = DEFAULT_OUTPUT,
    gate_report_path: Path | None = None,
) -> Path:
    try:
        fixture_payload = json.loads(fixture_path.read_text(encoding="utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RecommendationShadowFixtureImportError(["payload:invalid_json"]) from exc
    fixture_result = load_recommendation_shadow_context_fixtures(fixture_payload)
    artifact = build_recommendation_shadow_eval_artifact(fixture_result.scenarios)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(artifact.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    if gate_report_path is not None:
        gate_result = evaluate_recommendation_shadow_artifact_quality(artifact)
        gate_report_path.parent.mkdir(parents=True, exist_ok=True)
        gate_report_path.write_text(
            json.dumps(gate_result.model_dump(mode="json"), indent=2, sort_keys=True)
            + "\n",
            encoding="utf-8",
        )

    return output_path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build an offline recommendation shadow eval artifact from context fixtures."
    )
    parser.add_argument(
        "--fixtures",
        type=Path,
        required=True,
        help="Path to a recommendation shadow context fixture JSON file.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Path to write the recommendation shadow eval artifact.",
    )
    parser.add_argument(
        "--gate-report",
        type=Path,
        default=None,
        help="Optional path to write the artifact gate report.",
    )
    args = parser.parse_args()

    try:
        output = build_recommendation_shadow_eval_from_fixture_file(
            args.fixtures,
            args.output,
            args.gate_report,
        )
    except RecommendationShadowFixtureImportError as exc:
        print(json.dumps({"failure_codes": exc.failure_codes}, sort_keys=True), file=sys.stderr)
        return 1

    print(f"wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
