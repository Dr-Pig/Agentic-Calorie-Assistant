from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.composition.accurate_intake_clarify_commit_correction_same_truth_gate import (  # noqa: E402
    CLARIFY_COMMIT_CORRECTION_SAME_TRUTH_READY_STATUS,
    build_clarify_commit_correction_same_truth_gate_artifact,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--product-pages-browser-smoke-json", required=True)
    parser.add_argument("--product-pages-short-term-context-smoke-json", required=True)
    parser.add_argument("--product-pages-target-candidate-ui-smoke-json", required=True)
    parser.add_argument("--fixture-full-product-loop-e2e-json", required=True)
    parser.add_argument("--manager-runtime-gate-ledger-json")
    parser.add_argument(
        "--output",
        default="artifacts/accurate_intake_clarify_commit_correction_same_truth_gate.json",
    )
    args = parser.parse_args(argv)

    manager_runtime_gate_ledger = None
    if args.manager_runtime_gate_ledger_json:
        manager_runtime_gate_ledger = json.loads(
            Path(args.manager_runtime_gate_ledger_json).read_text(encoding="utf-8")
        )

    artifact = build_clarify_commit_correction_same_truth_gate_artifact(
        product_pages_browser_smoke=json.loads(
            Path(args.product_pages_browser_smoke_json).read_text(encoding="utf-8")
        ),
        short_term_context_smoke=json.loads(
            Path(args.product_pages_short_term_context_smoke_json).read_text(encoding="utf-8")
        ),
        target_candidate_ui_smoke=json.loads(
            Path(args.product_pages_target_candidate_ui_smoke_json).read_text(encoding="utf-8")
        ),
        fixture_full_product_loop_e2e=json.loads(
            Path(args.fixture_full_product_loop_e2e_json).read_text(encoding="utf-8")
        ),
        manager_runtime_gate_ledger=manager_runtime_gate_ledger,
    )

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(artifact, ensure_ascii=False, indent=2))
    return 0 if artifact["status"] == CLARIFY_COMMIT_CORRECTION_SAME_TRUTH_READY_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
