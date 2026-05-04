from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.composition.accurate_intake_context_quality_pack import (  # noqa: E402
    build_context_quality_pack_artifact,
)
from app.composition.accurate_intake_context_replay_pack import (  # noqa: E402
    build_context_replay_pack_artifact,
)
from app.composition.accurate_intake_context_review import (  # noqa: E402
    build_context_review_artifact,
)
from app.composition.accurate_intake_context_target_candidate_eval import (  # noqa: E402
    build_context_target_candidate_eval_artifact,
)
from app.composition.accurate_intake_context_window_diagnostic import (  # noqa: E402
    build_context_window_diagnostic_artifact,
)
from app.composition.accurate_intake_fake_provider_context_smoke import (  # noqa: E402
    build_fake_provider_context_smoke_artifact,
)

DEFAULT_OUTPUT_PATH = ROOT / "artifacts" / "accurate_intake_context_quality_pack.json"


def _fixture_context_review() -> dict[str, object]:
    return build_context_review_artifact(
        traces=[
            {
                "request_id": "context-quality-fixture-trace",
                "context_policy_version": "manager_context_policy_v1",
                "loaded_context_summary": {
                    "pending_followup_present": True,
                    "pending_draft_present": True,
                    "target_candidate_count": 2,
                },
                "omitted_context_summary": {
                    "policy_excluded_context_ids": [
                        "raw_trace_dump",
                        "long_term_memory",
                        "proactive_context",
                        "rescue_context",
                    ]
                },
                "manager_context_packet_v1": {
                    "hard_pins": {
                        "pending_followup": {"is_open": True},
                        "pending_draft": {"draft_id": "fixture-draft"},
                    },
                    "target_candidates": {
                        "for_correction_or_removal": [
                            {"meal_item_id": 1, "display_name": "tofu"},
                            {"meal_item_id": 2, "display_name": "rice"},
                        ]
                    },
                },
            }
        ]
    )


def build_context_quality_pack_report() -> dict[str, object]:
    return build_context_quality_pack_artifact(
        context_review=_fixture_context_review(),
        target_candidate_eval=build_context_target_candidate_eval_artifact(),
        context_window_diagnostic=build_context_window_diagnostic_artifact(),
        context_replay=build_context_replay_pack_artifact(),
        fake_provider_context_smoke=build_fake_provider_context_smoke_artifact(),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build the PL+CE context quality diagnostic pack."
    )
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH))
    args = parser.parse_args(argv)

    artifact = build_context_quality_pack_report()
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(artifact, ensure_ascii=False, indent=2))
    return 0 if artifact["status"] == "context_quality_diagnostic_pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
