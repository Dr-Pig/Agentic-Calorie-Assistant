from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.rescue.application.proposal_shaping_fake_runner import (  # noqa: E402
    run_rescue_proposal_shaping_fake,
)
from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build the rescue proposal-shaping fake runner artifact."
    )
    parser.add_argument("--proposal-shaping-input-shadow-packet", required=True, type=Path)
    parser.add_argument("--candidate-output", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)

    artifact = run_rescue_proposal_shaping_fake(
        proposal_shaping_input_shadow_packet=read_json_artifact(
            args.proposal_shaping_input_shadow_packet
        ),
        candidate_output=read_json_artifact(args.candidate_output),
    )
    write_json_artifact(args.output, artifact)
    print(json.dumps(artifact, ensure_ascii=False))
    return 0 if artifact["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
