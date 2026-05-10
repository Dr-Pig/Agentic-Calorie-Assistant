from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.recommendation.application.three_node_live_diagnostic import (  # noqa: E402
    FakeRecommendationThreeNodeDiagnosticProvider,
    run_recommendation_three_node_live_diagnostic,
)
from app.recommendation.application.three_node_live_preflight import (  # noqa: E402
    build_recommendation_three_node_live_preflight,
)


def write_recommendation_three_node_live_diagnostic(output_path: Path) -> Path:
    artifact = run_recommendation_three_node_live_diagnostic(
        preflight=build_recommendation_three_node_live_preflight(),
        provider=FakeRecommendationThreeNodeDiagnosticProvider(),
        provider_mode="fake_provider_contract_test",
        live_invoked=False,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    return output_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run dormant recommendation three-node fake diagnostic."
    )
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    write_recommendation_three_node_live_diagnostic(Path(args.output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["main", "write_recommendation_three_node_live_diagnostic"]
