from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.composition.accurate_intake_product_pages_context_target_browser_closure import (  # noqa: E402
    READY_STATUS,
    build_context_target_browser_closure_artifact,
)
from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact  # noqa: E402


def _read_yaml_artifact(path: Path) -> dict[str, object]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--manager-gate-ledger-yaml",
        default="docs/quality/MANAGER_RUNTIME_GATE_LEDGER.yaml",
    )
    parser.add_argument(
        "--short-term-context-json",
        default="artifacts/accurate_intake_product_pages_short_term_context_smoke_ci.json",
    )
    parser.add_argument(
        "--target-candidate-json",
        default="artifacts/accurate_intake_product_pages_target_candidate_ui_smoke_ci.json",
    )
    parser.add_argument(
        "--output",
        default="artifacts/accurate_intake_product_pages_context_target_browser_closure.json",
    )
    args = parser.parse_args(argv)

    artifact = build_context_target_browser_closure_artifact(
        manager_gate_ledger_artifact=_read_yaml_artifact(Path(args.manager_gate_ledger_yaml)),
        short_term_context_report=read_json_artifact(Path(args.short_term_context_json)),
        target_candidate_report=read_json_artifact(Path(args.target_candidate_json)),
    )
    output_path = Path(args.output)
    write_json_artifact(output_path, artifact)
    print(json.dumps(artifact, ensure_ascii=False))
    return 0 if artifact["status"] == READY_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
