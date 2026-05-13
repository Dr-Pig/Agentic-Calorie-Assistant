from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.advanced_shadow_lab.context_engineering_decision_pack import (  # noqa: E402
    build_context_engineering_decision_pack,
)
from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build the advanced product-lab context engineering decision pack."
    )
    parser.add_argument("--pr-train-json", required=True, type=Path)
    parser.add_argument("--baseline-runtime-json", required=True, type=Path)
    parser.add_argument("--manager-runtime-json", required=True, type=Path)
    parser.add_argument("--live-grokfast-json", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)

    pack = build_context_engineering_decision_pack(
        pr_train=read_json_artifact(args.pr_train_json),
        baseline_runtime_artifact=read_json_artifact(args.baseline_runtime_json),
        manager_runtime_artifact=read_json_artifact(args.manager_runtime_json),
        live_grokfast_artifact=read_json_artifact(args.live_grokfast_json),
    )
    write_json_artifact(args.output, pack)
    print(json.dumps(pack, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
