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
from app.composition.accurate_intake_review_eval_candidate_pipeline import (  # noqa: E402
    build_review_eval_candidate_pipeline_artifact,
)
from app.composition.accurate_intake_ui_same_truth_render_contract import (  # noqa: E402
    build_ui_same_truth_render_contract,
)
from scripts.build_accurate_intake_context_quality_pack import (  # noqa: E402
    build_context_quality_pack_report,
)

DEFAULT_OUTPUT_PATH = ROOT / "artifacts" / "accurate_intake_review_eval_candidate_pipeline.json"
DEFAULT_SHELL_PATH = ROOT / "static" / "accurate-intake-local-shell.html"


def _fixture_product_loop_e2e() -> dict[str, object]:
    return {
        "artifact_type": "accurate_intake_fixture_full_product_loop_e2e",
        "status": "fixture_product_loop_e2e_diagnostic_pass",
        "fixture_evidence_used": True,
        "fooddb_evidence_used": False,
        "websearch_evidence_used": False,
        "real_fooddb_pass_claimed": False,
        "dogfood_pass": False,
        "product_readiness_claimed": False,
        "private_self_use_approved": False,
        "ready_for_fdb_integration": False,
    }


def build_review_eval_candidate_pipeline_report(*, shell_path: Path = DEFAULT_SHELL_PATH) -> dict[str, object]:
    fixture_packets = build_fixture_evidence_packet_emulator_artifact()
    return build_review_eval_candidate_pipeline_artifact(
        product_loop_e2e=_fixture_product_loop_e2e(),
        ui_same_truth_contract=build_ui_same_truth_render_contract(
            shell_path.read_text(encoding="utf-8")
        ),
        context_quality_pack=build_context_quality_pack_report(),
        fixture_packet_emulator=fixture_packets,
        fake_provider_tool_loop_smoke=build_fake_provider_tool_loop_smoke_artifact(
            context_smoke=build_fake_provider_context_smoke_artifact(),
            fixture_packet_emulator=fixture_packets,
        ),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build local review candidates from PL+CE diagnostic artifacts."
    )
    parser.add_argument("--shell-path", default=str(DEFAULT_SHELL_PATH))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH))
    args = parser.parse_args(argv)

    artifact = build_review_eval_candidate_pipeline_report(shell_path=Path(args.shell_path))
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(artifact, ensure_ascii=False, indent=2))
    return 0 if artifact["status"] == "review_eval_candidate_pipeline_ready" else 1


if __name__ == "__main__":
    raise SystemExit(main())
