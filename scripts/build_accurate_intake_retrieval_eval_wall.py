from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.nutrition.application.retrieval_eval_wall import build_retrieval_eval_wall  # noqa: E402
from app.nutrition.infrastructure.local_food_evidence_index import (  # noqa: E402
    LocalSmallAnchorFoodEvidenceIndex,
)
from app.shared.infra.json_artifacts import write_json_artifact  # noqa: E402


DEFAULT_SMALL_ANCHOR_STORE = ROOT / "app" / "knowledge" / "small_anchor_store_tw.json"
DEFAULT_OUTPUT = ROOT / "artifacts" / "accurate_intake_retrieval_eval_wall.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build deterministic retrieval eval wall artifact."
    )
    parser.add_argument("--small-anchor-store", default=str(DEFAULT_SMALL_ANCHOR_STORE))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args(argv)

    index = LocalSmallAnchorFoodEvidenceIndex.from_path(Path(args.small_anchor_store))
    artifact = build_retrieval_eval_wall(retrieval_records=index.load_records())
    write_json_artifact(Path(args.output), artifact)
    print(
        json.dumps(
            {
                "artifact": str(args.output),
                "claim_scope": artifact["claim_scope"],
                "case_count": artifact["summary"]["case_count"],
                "pass_count": artifact["summary"]["pass_count"],
                "fail_count": artifact["summary"]["fail_count"],
                "next_required_slice": artifact["summary"]["next_required_slice"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
