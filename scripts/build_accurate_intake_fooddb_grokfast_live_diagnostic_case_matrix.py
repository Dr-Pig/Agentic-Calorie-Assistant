from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.nutrition.application.fooddb_grokfast_live_diagnostic_case_matrix import (  # noqa: E402
    build_fooddb_grokfast_live_diagnostic_case_matrix,
)
from app.shared.infra.json_artifacts import write_json_artifact  # noqa: E402


DEFAULT_OUTPUT = (
    ROOT
    / "artifacts"
    / "accurate_intake_fooddb_grokfast_packet_live_diagnostic_case_matrix.json"
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build plan-only FoodDB/GrokFast packet live diagnostic case matrix."
    )
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args(argv)

    artifact = build_fooddb_grokfast_live_diagnostic_case_matrix()
    output_path = Path(args.output)
    write_json_artifact(output_path, artifact)
    print(
        json.dumps(
            {
                "artifact": str(output_path),
                "classification": artifact["classification"],
                "case_count": artifact["summary"]["case_count"],
                "live_provider_invoked": artifact["live_provider_invoked"],
                "live_websearch_invoked": artifact["live_websearch_invoked"],
                "next_required_slice": artifact["next_required_slice"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
