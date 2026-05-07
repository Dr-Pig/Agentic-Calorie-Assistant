from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.nutrition.application.evidence_track_live_handoff import (  # noqa: E402
    build_evidence_track_live_handoff,
)
from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact  # noqa: E402
from scripts.evidence_track_live_bundle_artifacts import (  # noqa: E402
    build_evidence_track_live_bundle_artifact_paths,
)
from scripts.fooddb_live_bundle_artifacts import (  # noqa: E402
    bundle_artifact_path_from_manifest as fooddb_path_from_manifest,
)
from scripts.websearch_live_bundle_artifacts import (  # noqa: E402
    bundle_artifact_path_from_manifest as websearch_path_from_manifest,
)


DEFAULT_OUTPUT_DIR = ROOT / "artifacts" / "accurate_intake_evidence_track_live_bundle"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the bounded FoodDB -> WebSearch evidence-track live diagnostic bundle."
    )
    parser.add_argument("--mode", choices=("fixture", "live"), default="fixture")
    parser.add_argument("--allow-live", action="store_true")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args(argv)

    paths = build_evidence_track_live_bundle_artifact_paths(Path(args.output_dir))
    paths["fooddb_dir"].mkdir(parents=True, exist_ok=True)
    paths["websearch_dir"].mkdir(parents=True, exist_ok=True)
    fooddb_manifest, fooddb_status_post_contract, fooddb_exit = _run_fooddb_child(
        mode=args.mode,
        allow_live=args.allow_live,
        output_dir=paths["fooddb_dir"],
    )
    websearch_manifest = None
    websearch_status_packet_inspection = None
    websearch_exit = 0
    if fooddb_manifest.get("bundle_status") == "pass":
        websearch_manifest, websearch_status_packet_inspection, websearch_exit = _run_websearch_child(
            mode=args.mode,
            allow_live=args.allow_live,
            output_dir=paths["websearch_dir"],
            fooddb_status_post_contract=fooddb_status_post_contract,
        )

    handoff = build_evidence_track_live_handoff(
        fooddb_manifest=fooddb_manifest,
        fooddb_status_post_contract=fooddb_status_post_contract,
        websearch_manifest=websearch_manifest,
        websearch_status_packet_inspection=websearch_status_packet_inspection,
    )
    write_json_artifact(paths["handoff"], handoff)

    bundle_status = "pass" if fooddb_exit == 0 and websearch_exit == 0 and handoff["status"] != "blocked" else "blocked_or_failed"
    manifest = {
        "artifact_type": "accurate_intake_evidence_track_live_manifest_v1",
        "artifact_schema_version": "1.0",
        "generated_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "track": "FDB",
        "classification": "live_diagnostic_orchestration_only",
        "claim_scope": "fooddb_websearch_live_diagnostic_track_execution",
        "bundle_status": bundle_status,
        "mode": args.mode,
        "allow_live": args.allow_live,
        "fooddb_exit_code": fooddb_exit,
        "websearch_exit_code": websearch_exit,
        "live_provider_used": fooddb_manifest.get("live_provider_used") is True
        or (isinstance(websearch_manifest, dict) and websearch_manifest.get("live_provider_used") is True),
        "live_websearch_used": False if not isinstance(websearch_manifest, dict) else websearch_manifest.get("live_websearch_used") is True,
        "runtime_truth_changed": False,
        "runtime_mutation_attempted": False,
        "readiness_claimed": False,
        "next_recommended_slice": handoff["selected_next_step"],
        "handoff_status": handoff["status"],
        "artifacts": {
            "fooddb_manifest": str(paths["fooddb_dir"] / "accurate_intake_fooddb_live_diagnostic_bundle_manifest.json"),
            "fooddb_status_post_contract": None if fooddb_status_post_contract is None else str(fooddb_path_from_manifest(fooddb_manifest, key="fooddb_status_packet_post_contract")),
            "websearch_manifest": None if websearch_manifest is None else str(paths["websearch_dir"] / "websearch_live_manifest.json"),
            "websearch_status_packet_inspection": None if websearch_status_packet_inspection is None else str(websearch_path_from_manifest(websearch_manifest, key="websearch_status_packet_inspection")),
            "handoff": str(paths["handoff"]),
        },
        "non_claims": [
            "no_runtime_truth_promotion",
            "no_runtime_mutation",
            "no_shared_contract_change",
            "no_manager_context_change",
            "no_readiness_claim",
            "no_self_use_approval",
        ],
    }
    write_json_artifact(paths["manifest"], manifest)
    print(
        json.dumps(
            {
                "artifact": str(paths["manifest"]),
                "bundle_status": manifest["bundle_status"],
                "mode": args.mode,
                "next_recommended_slice": manifest["next_recommended_slice"],
            },
            ensure_ascii=False,
        )
    )
    return 0 if bundle_status == "pass" else 2


def _run_fooddb_child(*, mode: str, allow_live: bool, output_dir: Path) -> tuple[dict, dict | None, int]:
    argv = ["scripts/run_accurate_intake_fooddb_live_diagnostic_bundle.py", "--mode", mode, "--output-dir", str(output_dir)]
    if allow_live:
        argv.append("--allow-live")
    exit_code = _run_child(argv)
    manifest = read_json_artifact(output_dir / "accurate_intake_fooddb_live_diagnostic_bundle_manifest.json")
    status_path = fooddb_path_from_manifest(manifest, key="fooddb_status_packet_post_contract")
    status_packet = None if status_path is None or not status_path.exists() else read_json_artifact(status_path)
    return manifest, status_packet, exit_code


def _run_websearch_child(
    *,
    mode: str,
    allow_live: bool,
    output_dir: Path,
    fooddb_status_post_contract: dict | None,
) -> tuple[dict, dict | None, int]:
    argv = ["scripts/run_accurate_intake_websearch_live_diagnostic_bundle.py", "--mode", mode, "--output-dir", str(output_dir)]
    if allow_live:
        argv.append("--allow-live")
    if isinstance(fooddb_status_post_contract, dict):
        temp_path = output_dir.parent / "fooddb_status_post_contract_ref.json"
        write_json_artifact(temp_path, fooddb_status_post_contract)
        argv.extend(["--fooddb-status-packet-artifact", str(temp_path)])
    exit_code = _run_child(argv)
    manifest = read_json_artifact(output_dir / "websearch_live_manifest.json")
    inspection_path = websearch_path_from_manifest(manifest, key="websearch_status_packet_inspection")
    inspection = None if inspection_path is None or not inspection_path.exists() else read_json_artifact(inspection_path)
    return manifest, inspection, exit_code


def _run_child(argv: list[str]) -> int:
    completed = subprocess.run(
        [sys.executable, *argv],
        cwd=ROOT,
        check=False,
    )
    return int(completed.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
