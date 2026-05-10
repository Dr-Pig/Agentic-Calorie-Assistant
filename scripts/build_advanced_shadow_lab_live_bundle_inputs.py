from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.advanced_shadow_lab.live_bundle_inputs import (  # noqa: E402
    write_live_bundle_inputs,
)
from app.advanced_shadow_lab.live_bundle_profile_gate import (  # noqa: E402
    ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build reproducible inputs for the advanced shadow-lab live bundle."
    )
    parser.add_argument("--output-dir", default="artifacts/advanced_shadow_lab_live_bundle_inputs")
    parser.add_argument("--provider-mode", choices=("fake", "live"), default="fake")
    parser.add_argument("--allow-live-provider", action="store_true")
    parser.add_argument("--provider-profile-id", default=ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID)
    args = parser.parse_args(argv)

    result = write_live_bundle_inputs(
        Path(args.output_dir),
        provider_mode=str(args.provider_mode),
        provider_profile_id=str(args.provider_profile_id),
        allow_live_provider=bool(args.allow_live_provider),
    )
    preflight = result["preflight"]
    print(
        json.dumps(
            {
                "status": preflight["status"],
                "blockers": preflight["blockers"],
                "memory_review": str(result["memory_review_path"]),
                "chain_payload": str(result["chain_payload_path"]),
                "preflight": str(result["preflight_path"]),
                "environment_presence": preflight["environment_presence"],
                "live_provider_invoked": False,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
