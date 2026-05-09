from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.rescue.application.no_commit_viability import (  # noqa: E402
    build_rescue_no_commit_viability_shadow_packet,
)
from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build the rescue no-commit viability shadow packet artifact."
    )
    parser.add_argument("--rescue-summary-context-projection", required=True, type=Path)
    parser.add_argument("--current-budget-view-json", required=True, type=Path)
    parser.add_argument("--active-body-plan-view-json", required=True, type=Path)
    parser.add_argument("--open-proposals-view-json", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)

    packet = build_rescue_no_commit_viability_shadow_packet(
        rescue_context_projection=read_json_artifact(args.rescue_summary_context_projection),
        current_budget_view=read_json_artifact(args.current_budget_view_json),
        active_body_plan_view=read_json_artifact(args.active_body_plan_view_json),
        open_proposals_view=read_json_artifact(args.open_proposals_view_json),
    )
    write_json_artifact(args.output, packet)
    print(json.dumps(packet, ensure_ascii=False))
    return 0 if packet["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
