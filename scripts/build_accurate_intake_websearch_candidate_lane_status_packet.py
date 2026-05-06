from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.nutrition.application.websearch_candidate_lane_status_packet import (  # noqa: E402
    build_websearch_candidate_lane_status_packet,
)
from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact  # noqa: E402
from scripts.websearch_live_bundle_artifacts import (  # noqa: E402
    build_websearch_live_bundle_artifact_paths,
    bundle_artifact_path_from_manifest,
)


DEFAULT_OUTPUT = ROOT / "artifacts" / "accurate_intake_websearch_candidate_lane_status_packet.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build WebSearch candidate lane status packet."
    )
    parser.add_argument("--fooddb-status-packet")
    parser.add_argument("--manager-contract-handoff-artifact")
    parser.add_argument("--live-diagnostic-report")
    parser.add_argument("--contract-probe-artifact")
    parser.add_argument("--repair-pack-artifact")
    parser.add_argument("--preflight-artifact")
    parser.add_argument("--live-bundle-manifest")
    parser.add_argument("--live-bundle-dir")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args(argv)

    live_bundle_manifest = _read_bundle_manifest(
        args.live_bundle_manifest,
        args.live_bundle_dir,
    )

    artifact = build_websearch_candidate_lane_status_packet(
        fooddb_status_packet=(
            read_json_artifact(Path(args.fooddb_status_packet)) if args.fooddb_status_packet else None
        ),
        manager_contract_handoff_artifact=(
            _read_optional_or_bundle(
                explicit_path=args.manager_contract_handoff_artifact,
                bundle_manifest=live_bundle_manifest,
                bundle_dir=args.live_bundle_dir,
                bundle_key="manager_contract_handoff",
            )
        ),
        live_diagnostic_report=(
            _read_optional_or_bundle(
                explicit_path=args.live_diagnostic_report,
                bundle_manifest=live_bundle_manifest,
                bundle_dir=args.live_bundle_dir,
                bundle_key="report",
            )
        ),
        contract_probe_artifact=(
            _read_optional_or_bundle(
                explicit_path=args.contract_probe_artifact,
                bundle_manifest=live_bundle_manifest,
                bundle_dir=args.live_bundle_dir,
                bundle_key="manager_contract_probe",
            )
        ),
        repair_pack_artifact=(
            _read_optional_or_bundle(
                explicit_path=args.repair_pack_artifact,
                bundle_manifest=live_bundle_manifest,
                bundle_dir=args.live_bundle_dir,
                bundle_key="manager_contract_repair_pack",
            )
        ),
        preflight_artifact=(
            _read_optional_or_bundle(
                explicit_path=args.preflight_artifact,
                bundle_manifest=live_bundle_manifest,
                bundle_dir=args.live_bundle_dir,
                bundle_key="preflight",
            )
        ),
    )
    output_path = Path(args.output)
    write_json_artifact(output_path, artifact)
    print(
        json.dumps(
            {
                "artifact": str(output_path),
                "claim_scope": artifact["claim_scope"],
                "upstream_fooddb_gate_status": artifact["summary"]["upstream_fooddb_gate_status"],
                "manager_contract_gate_status": artifact["summary"]["manager_contract_gate_status"],
                "next_required_slices": artifact["next_required_slices"],
            },
            ensure_ascii=False,
        )
    )
    return 0


def _read_bundle_manifest(
    manifest_arg: str | None,
    bundle_dir_arg: str | None,
) -> dict[str, object] | None:
    if manifest_arg:
        return read_json_artifact(Path(manifest_arg))
    if bundle_dir_arg:
        manifest_path = build_websearch_live_bundle_artifact_paths(Path(bundle_dir_arg))["manifest"]
        if manifest_path.exists():
            return read_json_artifact(manifest_path)
    return None


def _read_optional_or_bundle(
    *,
    explicit_path: str | None,
    bundle_manifest: dict[str, object] | None,
    bundle_dir: str | None,
    bundle_key: str,
) -> dict[str, object] | None:
    if explicit_path:
        return read_json_artifact(Path(explicit_path))
    if bundle_manifest is not None:
        bundle_path = bundle_artifact_path_from_manifest(bundle_manifest, key=bundle_key)
        if bundle_path is not None and bundle_path.exists():
            return read_json_artifact(bundle_path)
    if bundle_dir:
        bundle_path = build_websearch_live_bundle_artifact_paths(Path(bundle_dir))[bundle_key]
        if bundle_path.exists():
            return read_json_artifact(bundle_path)
    return None


if __name__ == "__main__":
    raise SystemExit(main())
