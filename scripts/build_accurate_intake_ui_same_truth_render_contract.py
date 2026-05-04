from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.composition.accurate_intake_ui_same_truth_render_contract import (  # noqa: E402
    build_ui_same_truth_render_contract,
)

DEFAULT_SHELL_PATH = ROOT / "static" / "accurate-intake-local-shell.html"
DEFAULT_OUTPUT_PATH = ROOT / "artifacts" / "accurate_intake_ui_same_truth_render_contract.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build the Accurate Intake local shell render-only same-truth contract artifact."
    )
    parser.add_argument("--shell-path", default=str(DEFAULT_SHELL_PATH))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH))
    args = parser.parse_args(argv)

    shell_html = Path(args.shell_path).read_text(encoding="utf-8")
    artifact = build_ui_same_truth_render_contract(shell_html)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(artifact, ensure_ascii=False, indent=2))
    return 0 if artifact["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
