from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.nutrition.application.food_evidence_candidate_triage_report import (  # noqa: E402
    build_food_evidence_candidate_triage_report,
)
from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact  # noqa: E402


DEFAULT_VALIDATION = ROOT / "artifacts" / "accurate_intake_food_evidence_validation.json"
DEFAULT_AUTO_ELIGIBLE = ROOT / "artifacts" / "accurate_intake_food_auto_eligible_batch.json"
DEFAULT_OUTPUT = ROOT / "artifacts" / "accurate_intake_food_candidate_triage_report.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build a report-only FoodDB candidate triage artifact."
    )
    parser.add_argument("--validation-json", default=str(DEFAULT_VALIDATION))
    parser.add_argument("--auto-eligible-json", default=str(DEFAULT_AUTO_ELIGIBLE))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args(argv)

    report = build_food_evidence_candidate_triage_report(
        validation_artifact=read_json_artifact(Path(args.validation_json)),
        auto_eligible_artifact=read_json_artifact(Path(args.auto_eligible_json)),
    )
    write_json_artifact(Path(args.output), report)
    print(
        json.dumps(
            {
                "artifact": str(args.output),
                "claim_scope": report["claim_scope"],
                "tfda_generic_auto_eligible_count": report["summary"][
                    "tfda_generic_auto_eligible_count"
                ],
                "official_exact_candidate_only_count": report["summary"][
                    "official_exact_candidate_only_count"
                ],
                "source_repair_required_count": report["summary"][
                    "source_repair_required_count"
                ],
                "rejected_count": report["summary"]["rejected_count"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
