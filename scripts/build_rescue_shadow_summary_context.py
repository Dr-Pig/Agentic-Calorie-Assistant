from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.rescue.application.shadow_summary_context import (  # noqa: E402
    build_rescue_shadow_summary_context_projection,
)
from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build the rescue shadow summary-context projection artifact."
    )
    parser.add_argument("--memory-summary-projection", required=True, type=Path)
    parser.add_argument("--derived-memory-views-json", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)

    projection = build_rescue_shadow_summary_context_projection(
        memory_summary_projection=read_json_artifact(args.memory_summary_projection),
        derived_memory_views=read_json_artifact(args.derived_memory_views_json),
    )
    write_json_artifact(args.output, projection)
    print(json.dumps(projection, ensure_ascii=False))
    return 0 if projection["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
