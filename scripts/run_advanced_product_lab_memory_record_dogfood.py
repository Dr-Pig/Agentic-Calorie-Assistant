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
from app.advanced_shadow_lab.product_lab_memory_record_dogfood_summary import (  # noqa: E402
    build_memory_record_dogfood_summary,
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
        description="Run the MemoryRecord-backed advanced product-lab dogfood scenario."
    )
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--summary-output", required=True)
    parser.add_argument("--session-id", default="advanced-product-lab-memory-record")
    args = parser.parse_args(argv)

    session = run_advanced_product_lab_memory_record_session(
        artifact_root=Path(args.output_root),
        session_id=str(args.session_id),
        fixture_inputs=build_product_lab_calibration_fixture_inputs(),
        turns=build_product_lab_simulated_turns(),
    )
    summary = build_memory_record_dogfood_summary(session)
    write_json_artifact(Path(args.summary_output), summary)
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
