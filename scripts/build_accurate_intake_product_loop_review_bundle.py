from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.composition.accurate_intake_product_loop_review_bundle import (  # noqa: E402
    build_product_loop_review_bundle_artifact,
)
from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build a local Product Loop + Context review bundle."
    )
    parser.add_argument("--browser-shell-smoke", required=True)
    parser.add_argument("--browser-fixture-dogfood", required=True)
    parser.add_argument("--browser-realistic-dogfood", required=True)
    parser.add_argument("--context-review", required=True)
    parser.add_argument("--context-target-candidate-eval", required=True)
    parser.add_argument("--context-window-diagnostic", required=True)
    parser.add_argument(
        "--output",
        default="artifacts/accurate_intake_product_loop_review_bundle.json",
    )
    args = parser.parse_args(argv)

    artifact = build_product_loop_review_bundle_artifact(
        browser_shell_smoke=read_json_artifact(Path(args.browser_shell_smoke)),
        browser_fixture_dogfood=read_json_artifact(Path(args.browser_fixture_dogfood)),
        browser_realistic_dogfood=read_json_artifact(Path(args.browser_realistic_dogfood)),
        context_review=read_json_artifact(Path(args.context_review)),
        context_target_candidate_eval=read_json_artifact(
            Path(args.context_target_candidate_eval)
        ),
        context_window_diagnostic=read_json_artifact(Path(args.context_window_diagnostic)),
    )
    write_json_artifact(Path(args.output), artifact)
    print(json.dumps({"artifact": args.output, "status": artifact["status"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
