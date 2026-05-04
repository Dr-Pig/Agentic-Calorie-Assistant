from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.composition.accurate_intake_fake_provider_context_smoke import (  # noqa: E402
    build_fake_provider_context_smoke_artifact,
)
from app.composition.accurate_intake_fake_provider_tool_loop_smoke import (  # noqa: E402
    build_fake_provider_tool_loop_smoke_artifact,
)
from app.composition.accurate_intake_fixture_evidence_packet_emulator import (  # noqa: E402
    build_fixture_evidence_packet_emulator_artifact,
)

DEFAULT_OUTPUT_PATH = ROOT / "artifacts" / "accurate_intake_fake_provider_tool_loop_smoke.json"


def build_fake_provider_tool_loop_smoke_report() -> dict[str, object]:
    return build_fake_provider_tool_loop_smoke_artifact(
        context_smoke=build_fake_provider_context_smoke_artifact(),
        fixture_packet_emulator=build_fixture_evidence_packet_emulator_artifact(),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run fake-provider context + fixture evidence packet tool-loop smoke."
    )
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH))
    args = parser.parse_args(argv)

    artifact = build_fake_provider_tool_loop_smoke_report()
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(artifact, ensure_ascii=False, indent=2))
    return 0 if artifact["status"] == "fake_provider_tool_loop_smoke_pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
