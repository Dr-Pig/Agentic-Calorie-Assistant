from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.nutrition.application.exact_card_candidate_promotion_readiness import (  # noqa: E402
    build_exact_card_candidate_promotion_readiness,
)
from app.nutrition.application.exact_evidence_lane_policy import (  # noqa: E402
    build_exact_evidence_lane_policy_artifact,
)
from app.nutrition.application.websearch_exact_candidate_chain_status import (  # noqa: E402
    build_websearch_exact_candidate_chain_status,
)
from app.nutrition.application.websearch_exact_candidate_review_packet import (  # noqa: E402
    build_websearch_exact_candidate_review_packet,
)
from app.nutrition.application.websearch_extract_result_candidate_smoke import (  # noqa: E402
    build_websearch_extract_result_candidate_smoke,
)
from app.nutrition.application.websearch_grokfast_live_diagnostic_case_matrix import (  # noqa: E402
    build_websearch_grokfast_live_diagnostic_case_matrix_artifact,
)
from app.nutrition.application.websearch_live_diagnostic_report import (  # noqa: E402
    build_websearch_live_diagnostic_report,
)
from app.nutrition.application.websearch_live_extract_preflight import (  # noqa: E402
    build_websearch_live_extract_preflight,
)
from app.nutrition.application.websearch_live_runner_readiness_packet import (  # noqa: E402
    build_websearch_live_runner_readiness_packet,
)
from app.nutrition.application.websearch_selected_extract_packet_smoke import (  # noqa: E402
    build_websearch_selected_extract_packet_smoke,
)
from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact  # noqa: E402
from scripts.run_accurate_intake_grokfast_websearch_packet_smoke import (  # noqa: E402
    main as run_grokfast_websearch_packet_smoke,
)


DEFAULT_OUTPUT_DIR = ROOT / "artifacts" / "accurate_intake_websearch_live_diagnostic_bundle"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build and run the bounded WebSearch/GrokFast packet live diagnostic bundle."
        )
    )
    parser.add_argument("--mode", choices=("fixture", "live"), default="fixture")
    parser.add_argument("--allow-live", action="store_true")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args(argv)

    output_dir = Path(args.output_dir)
    paths = _artifact_paths(output_dir)
    artifacts = _build_pre_provider_artifacts(paths)
    diagnostic_exit = _run_packet_smoke(
        mode=args.mode,
        allow_live=args.allow_live,
        paths=paths,
    )
    diagnostic = read_json_artifact(paths["diagnostic"])
    report = build_websearch_live_diagnostic_report(
        diagnostic_artifact=diagnostic,
        preflight_artifact=artifacts["preflight"],
    )
    write_json_artifact(paths["report"], report)
    manifest = _build_manifest(
        mode=args.mode,
        allow_live=args.allow_live,
        paths=paths,
        diagnostic_exit=diagnostic_exit,
        diagnostic=diagnostic,
        report=report,
    )
    write_json_artifact(paths["manifest"], manifest)
    print(
        json.dumps(
            {
                "artifact": str(paths["manifest"]),
                "bundle_status": manifest["bundle_status"],
                "mode": args.mode,
                "live_provider_used": diagnostic.get("live_provider_used"),
                "seam_status": report["seam_status"],
                "next_recommended_slice": report["next_recommended_slice"],
            },
            ensure_ascii=False,
        )
    )
    return diagnostic_exit


def _artifact_paths(output_dir: Path) -> dict[str, Path]:
    return {
        "case_matrix": output_dir
        / "accurate_intake_websearch_grokfast_packet_live_diagnostic_case_matrix.json",
        "selected_extract": output_dir
        / "accurate_intake_websearch_selected_extract_packet_smoke.json",
        "extract_result": output_dir
        / "accurate_intake_websearch_extract_result_candidate_smoke.json",
        "review_packet": output_dir
        / "accurate_intake_websearch_exact_candidate_review_packet.json",
        "preflight": output_dir / "accurate_intake_websearch_live_extract_preflight.json",
        "chain_status": output_dir
        / "accurate_intake_websearch_exact_candidate_chain_status.json",
        "readiness": output_dir
        / "accurate_intake_websearch_live_runner_readiness_packet.json",
        "diagnostic": output_dir / "accurate_intake_grokfast_websearch_packet_smoke.json",
        "report": output_dir / "accurate_intake_websearch_live_diagnostic_report.json",
        "manifest": output_dir / "accurate_intake_websearch_live_diagnostic_bundle_manifest.json",
    }


def _build_pre_provider_artifacts(paths: dict[str, Path]) -> dict[str, dict[str, Any]]:
    case_matrix = build_websearch_grokfast_live_diagnostic_case_matrix_artifact()
    exact_readiness = build_exact_card_candidate_promotion_readiness(
        exact_lane_artifact=build_exact_evidence_lane_policy_artifact()
    )
    selected_extract = build_websearch_selected_extract_packet_smoke(
        exact_card_readiness_artifact=exact_readiness
    )
    extract_result = build_websearch_extract_result_candidate_smoke(
        selected_extract_artifact=selected_extract
    )
    review_packet = build_websearch_exact_candidate_review_packet(
        extract_result_artifact=extract_result
    )
    preflight = build_websearch_live_extract_preflight(
        exact_review_packet_artifact=review_packet,
        case_matrix_artifact=case_matrix,
    )
    chain_status = build_websearch_exact_candidate_chain_status(
        selected_extract_artifact=selected_extract,
        extract_result_artifact=extract_result,
        exact_review_packet_artifact=review_packet,
        preflight_artifact=preflight,
    )
    readiness = build_websearch_live_runner_readiness_packet(
        review_packet_artifact=review_packet,
        preflight_artifact=preflight,
        exact_candidate_chain_status_artifact=chain_status,
    )
    artifacts = {
        "case_matrix": case_matrix,
        "selected_extract": selected_extract,
        "extract_result": extract_result,
        "review_packet": review_packet,
        "preflight": preflight,
        "chain_status": chain_status,
        "readiness": readiness,
    }
    for key, artifact in artifacts.items():
        write_json_artifact(paths[key], artifact)
    return artifacts


def _run_packet_smoke(
    *,
    mode: str,
    allow_live: bool,
    paths: dict[str, Path],
) -> int:
    argv = [
        "--mode",
        mode,
        "--review-packet-artifact",
        str(paths["review_packet"]),
        "--preflight-artifact",
        str(paths["preflight"]),
        "--exact-candidate-chain-status-artifact",
        str(paths["chain_status"]),
        "--live-runner-readiness-artifact",
        str(paths["readiness"]),
        "--output",
        str(paths["diagnostic"]),
    ]
    if allow_live:
        argv.append("--allow-live")
    return run_grokfast_websearch_packet_smoke(argv)


def _build_manifest(
    *,
    mode: str,
    allow_live: bool,
    paths: dict[str, Path],
    diagnostic_exit: int,
    diagnostic: dict[str, Any],
    report: dict[str, Any],
) -> dict[str, Any]:
    return {
        "artifact_type": "accurate_intake_websearch_live_diagnostic_bundle_manifest",
        "artifact_schema_version": "1.0",
        "generated_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "track": "FDB",
        "classification": "live_diagnostic_orchestration_only",
        "claim_scope": "websearch_packet_live_diagnostic_bundle_execution",
        "bundle_status": "pass" if diagnostic_exit == 0 else "blocked_or_failed",
        "mode": mode,
        "allow_live": allow_live,
        "diagnostic_exit_code": diagnostic_exit,
        "live_provider_used": diagnostic.get("live_provider_used") is True,
        "live_websearch_used": diagnostic.get("live_websearch_used") is True,
        "runtime_truth_changed": False,
        "runtime_mutation_attempted": False,
        "readiness_claimed": False,
        "self_use_approved": False,
        "production_selected": False,
        "seam_status": report["seam_status"],
        "next_recommended_slice": report["next_recommended_slice"],
        "artifacts": {key: str(path) for key, path in paths.items() if key != "manifest"},
        "non_claims": [
            "not_self_use_gate",
            "not_websearch_tool_loop_gate",
            "not_exact_card_truth_gate",
            "not_runtime_mutation_gate",
            "not_product_readiness",
        ],
    }


if __name__ == "__main__":
    raise SystemExit(main())
