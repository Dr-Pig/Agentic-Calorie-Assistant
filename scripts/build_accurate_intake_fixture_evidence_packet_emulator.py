from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.composition.accurate_intake_fixture_evidence_packet_emulator import (  # noqa: E402
    build_fixture_evidence_packet_emulator_artifact,
)

DEFAULT_OUTPUT_PATH = ROOT / "artifacts" / "accurate_intake_fixture_evidence_packet_emulator.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build fixture-only evidence packet emulator scenarios for PL+CE diagnostics."
    )
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH))
    args = parser.parse_args(argv)

    artifact = build_fixture_evidence_packet_emulator_artifact()
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(artifact, ensure_ascii=False, indent=2))
    return 0 if artifact["status"] == "fixture_packet_emulator_ready" else 1


if __name__ == "__main__":
    raise SystemExit(main())
