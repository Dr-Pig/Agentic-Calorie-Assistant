from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.nutrition.application.fooddb_manager_contract_handoff_inspection import (  # noqa: E402
    build_fooddb_manager_contract_handoff_inspection,
)
from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact  # noqa: E402
from scripts.fooddb_live_bundle_artifacts import bundle_artifact_path_from_manifest  # noqa: E402

DEFAULT_OUTPUT = ROOT / "artifacts" / "accurate_intake_fooddb_manager_contract_handoff_inspection.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build FoodDB manager contract handoff inspection.")
    parser.add_argument("--manager-contract-handoff-artifact", default=None)
    parser.add_argument("--live-diagnostic-report", default=None)
    parser.add_argument("--contract-probe-artifact", default=None)
    parser.add_argument("--repair-pack-artifact", default=None)
    parser.add_argument("--bundle-manifest", default=None)
    parser.add_argument("--bundle-dir", default=None)
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args(argv)

    manifest = read_json_artifact(Path(args.bundle_manifest)) if args.bundle_manifest else None
    bundle_dir = Path(args.bundle_dir) if args.bundle_dir else None
    artifact = build_fooddb_manager_contract_handoff_inspection(
        manager_contract_handoff_artifact=_read_payload(
            args.manager_contract_handoff_artifact,
            manifest=manifest,
            bundle_dir=bundle_dir,
            manifest_key="manager_contract_handoff",
            bundle_name="accurate_intake_fooddb_manager_contract_handoff.json",
        ),
        live_diagnostic_report=_read_optional_payload(
            args.live_diagnostic_report,
            manifest=manifest,
            bundle_dir=bundle_dir,
            manifest_key="report",
            bundle_name="accurate_intake_fooddb_live_diagnostic_report.json",
        ),
        contract_probe_artifact=_read_optional_payload(
            args.contract_probe_artifact,
            manifest=manifest,
            bundle_dir=bundle_dir,
            manifest_key="manager_contract_probe",
            bundle_name="accurate_intake_fooddb_manager_contract_probe.json",
        ),
        repair_pack_artifact=_read_optional_payload(
            args.repair_pack_artifact,
            manifest=manifest,
            bundle_dir=bundle_dir,
            manifest_key="manager_contract_repair_pack",
            bundle_name="accurate_intake_fooddb_manager_contract_repair_pack.json",
        ),
    )
    write_json_artifact(Path(args.output), artifact)
    return 0 if artifact["status"] == "pass" else 1


def _read_payload(
    direct_path: str | None,
    *,
    manifest: dict | None,
    bundle_dir: Path | None,
    manifest_key: str,
    bundle_name: str,
) -> dict:
    return read_json_artifact(_resolve_path(direct_path, manifest=manifest, bundle_dir=bundle_dir, manifest_key=manifest_key, bundle_name=bundle_name))


def _read_optional_payload(
    direct_path: str | None,
    *,
    manifest: dict | None,
    bundle_dir: Path | None,
    manifest_key: str,
    bundle_name: str,
) -> dict | None:
    path = _resolve_path(direct_path, manifest=manifest, bundle_dir=bundle_dir, manifest_key=manifest_key, bundle_name=bundle_name, required=False)
    return None if path is None else read_json_artifact(path)


def _resolve_path(
    direct_path: str | None,
    *,
    manifest: dict | None,
    bundle_dir: Path | None,
    manifest_key: str,
    bundle_name: str,
    required: bool = True,
) -> Path | None:
    if direct_path:
        return Path(direct_path)
    if manifest is not None:
        path = bundle_artifact_path_from_manifest(manifest, key=manifest_key)
        if path is not None:
            return path
    if bundle_dir is not None:
        candidate = bundle_dir / bundle_name
        if candidate.exists() or required:
            return candidate
    if required:
        raise ValueError(f"missing_required_artifact:{manifest_key}")
    return None


if __name__ == "__main__":
    raise SystemExit(main())
