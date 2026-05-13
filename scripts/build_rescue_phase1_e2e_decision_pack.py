from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import yaml


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.advanced_shadow_lab.product_lab_rescue_phase1_decision_pack import (  # noqa: E402
    build_rescue_phase1_e2e_decision_pack,
)
from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build the rescue Phase 1 integrated E2E decision pack."
    )
    parser.add_argument("--pr-train-yaml", required=True, type=Path)
    parser.add_argument("--golden-set-yaml", required=True, type=Path)
    parser.add_argument("--replay-artifacts-json", required=True, type=Path)
    parser.add_argument("--live-diagnostics-json", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)

    replay = read_json_artifact(args.replay_artifacts_json)
    diagnostics = read_json_artifact(args.live_diagnostics_json)
    pack = build_rescue_phase1_e2e_decision_pack(
        pr_train=yaml.safe_load(args.pr_train_yaml.read_text(encoding="utf-8-sig")),
        golden_set=yaml.safe_load(args.golden_set_yaml.read_text(encoding="utf-8-sig")),
        replay_artifacts=list(replay.get("replay_artifacts") or []),
        live_diagnostic_artifacts=list(diagnostics.get("diagnostic_artifacts") or []),
    )
    write_json_artifact(args.output, pack)
    print(json.dumps(pack, ensure_ascii=False))
    return 0 if pack["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
