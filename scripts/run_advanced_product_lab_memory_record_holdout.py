from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.advanced_shadow_lab.product_lab_calibration_fixture_inputs import (  # noqa: E402
    build_product_lab_calibration_fixture_inputs,
)
from app.advanced_shadow_lab.product_lab_memory_record_holdout import (  # noqa: E402
    build_memory_record_holdout_report,
    build_memory_record_holdout_turns,
)
from app.advanced_shadow_lab.product_lab_memory_record_session import (  # noqa: E402
    run_advanced_product_lab_memory_record_session,
)
from app.advanced_shadow_lab.product_lab_simulated_scenario import (  # noqa: E402
    build_product_lab_simulated_turns,
)
from app.shared.infra.json_artifacts import write_json_artifact  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the MemoryRecord simulated holdout session."
    )
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--report-output", required=True, type=Path)
    parser.add_argument("--session-id", default="advanced-product-lab-memory-holdout")
    args = parser.parse_args(argv)

    session = run_advanced_product_lab_memory_record_session(
        artifact_root=args.output_root,
        session_id=str(args.session_id),
        fixture_inputs=build_product_lab_calibration_fixture_inputs(),
        turns=[*build_product_lab_simulated_turns(), *build_memory_record_holdout_turns()],
    )
    report = build_memory_record_holdout_report(session)
    write_json_artifact(args.report_output, report)
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
