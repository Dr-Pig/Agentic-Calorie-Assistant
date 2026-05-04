from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.nutrition.application.food_evidence_candidate_validation import (  # noqa: E402
    build_food_evidence_candidate_validation_artifact,
)
from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact  # noqa: E402


DEFAULT_CANDIDATES = ROOT / "artifacts" / "accurate_intake_food_evidence_candidates.json"
DEFAULT_GAP_REGISTER = ROOT / "artifacts" / "accurate_intake_food_kb_gap_register.json"
DEFAULT_OUTPUT = ROOT / "artifacts" / "accurate_intake_food_evidence_validation.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate FoodEvidenceCandidate artifacts and build PR110 coverage diagnostics."
    )
    parser.add_argument(
        "--candidate-json",
        default=str(DEFAULT_CANDIDATES),
        help="FoodEvidenceCandidate artifact JSON path.",
    )
    parser.add_argument(
        "--food-gap-register",
        default=str(DEFAULT_GAP_REGISTER),
        help="Optional PR110 food gap register JSON path.",
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT),
        help="Output artifact path. Defaults to ignored local artifacts directory.",
    )
    args = parser.parse_args(argv)

    candidate_artifact = read_json_artifact(Path(args.candidate_json))
    gap_path = Path(args.food_gap_register)
    gap_register = read_json_artifact(gap_path) if gap_path.exists() else None
    artifact = build_food_evidence_candidate_validation_artifact(
        candidate_artifact=candidate_artifact,
        gap_register=gap_register,
    )
    write_json_artifact(Path(args.output), artifact)
    print(
        json.dumps(
            {
                "artifact": str(args.output),
                "claim_scope": artifact["claim_scope"],
                "validator_passed_count": artifact["summary"]["validator_passed_count"],
                "rejected_count": artifact["summary"]["rejected_count"],
                "needs_source_repair_count": artifact["summary"]["needs_source_repair_count"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
