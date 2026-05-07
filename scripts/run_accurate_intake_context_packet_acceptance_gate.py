from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.composition.accurate_intake_context_packet_acceptance_gate import (  # noqa: E402
    build_context_packet_acceptance_gate_artifact,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the accurate-intake runtime context packet acceptance gate.")
    parser.add_argument(
        "--output",
        default="artifacts/accurate_intake_context_packet_acceptance_gate.json",
    )
    args = parser.parse_args(argv)

    artifact = build_context_packet_acceptance_gate_artifact()
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": artifact["status"], "output": str(output_path)}, ensure_ascii=False))
    return 0 if artifact["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
