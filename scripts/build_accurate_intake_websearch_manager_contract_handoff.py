from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.nutrition.application.websearch_manager_contract_handoff import (  # noqa: E402
    build_websearch_manager_contract_handoff,
)
from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact  # noqa: E402
from scripts.websearch_live_bundle_artifacts import (  # noqa: E402
    build_websearch_live_bundle_artifact_paths,
    bundle_artifact_path_from_manifest,
)


DEFAULT_LIVE_REPORT = ROOT / "artifacts" / "accurate_intake_websearch_live_diagnostic_report.json"
DEFAULT_PROBE = ROOT / "artifacts" / "accurate_intake_websearch_manager_contract_probe.json"
DEFAULT_REPAIR_PACK = (
    ROOT / "artifacts" / "accurate_intake_websearch_manager_contract_repair_pack.json"
)
DEFAULT_PREFLIGHT = ROOT / "artifacts" / "accurate_intake_websearch_live_extract_preflight.json"
DEFAULT_OUTPUT = ROOT / "artifacts" / "accurate_intake_websearch_manager_contract_handoff.json"
DEFAULT_BUNDLE_DIR = ROOT / "artifacts" / "accurate_intake_websearch_live_diagnostic_bundle"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build WebSearch manager contract handoff artifact."
    )
    parser.add_argument("--live-diagnostic-report")
    parser.add_argument("--contract-probe-artifact")
    parser.add_argument("--repair-pack-artifact")
    parser.add_argument("--preflight-artifact", default="")
    parser.add_argument("--live-bundle-manifest")
    parser.add_argument("--live-bundle-dir")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args(argv)
    live_bundle_manifest = _read_bundle_manifest(
        args.live_bundle_manifest,
        args.live_bundle_dir,
    )

    artifact = build_websearch_manager_contract_handoff(
        live_diagnostic_report=_read_required_artifact(
            explicit_path=args.live_diagnostic_report,
            bundle_manifest=live_bundle_manifest,
            bundle_dir=args.live_bundle_dir,
            bundle_key="report",
            fallback=DEFAULT_LIVE_REPORT,
        ),
        contract_probe_artifact=_read_required_artifact(
            explicit_path=args.contract_probe_artifact,
            bundle_manifest=live_bundle_manifest,
            bundle_dir=args.live_bundle_dir,
            bundle_key="manager_contract_probe",
            fallback=DEFAULT_PROBE,
        ),
        repair_pack_artifact=_read_required_artifact(
            explicit_path=args.repair_pack_artifact,
            bundle_manifest=live_bundle_manifest,
            bundle_dir=args.live_bundle_dir,
            bundle_key="manager_contract_repair_pack",
            fallback=DEFAULT_REPAIR_PACK,
        ),
        preflight_artifact=_read_optional_artifact(
            explicit_path=args.preflight_artifact,
            bundle_manifest=live_bundle_manifest,
            bundle_dir=args.live_bundle_dir,
            bundle_key="preflight",
            fallback=DEFAULT_PREFLIGHT,
        ),
    )
    output_path = Path(args.output)
    write_json_artifact(output_path, artifact)
    print(
        json.dumps(
            {
                "artifact": str(output_path),
                "status": artifact["status"],
                "selected_next_step": artifact["selected_next_step"],
                "handoff_ready": artifact["handoff_ready"],
            },
            ensure_ascii=False,
        )
    )
    return 0


def _read_bundle_manifest(
    manifest_arg: str | None,
    bundle_dir_arg: str | None,
) -> dict[str, object] | None:
    manifest_path = None
    if manifest_arg:
        manifest_path = Path(manifest_arg)
    elif bundle_dir_arg:
        manifest_path = build_websearch_live_bundle_artifact_paths(Path(bundle_dir_arg))["manifest"]
    else:
        default_manifest = build_websearch_live_bundle_artifact_paths(DEFAULT_BUNDLE_DIR)["manifest"]
        if default_manifest.exists():
            manifest_path = default_manifest
    if manifest_path is None or not manifest_path.exists():
        return None
    return read_json_artifact(manifest_path)


def _read_required_artifact(
    *,
    explicit_path: str | None,
    bundle_manifest: dict[str, object] | None,
    bundle_dir: str | None,
    bundle_key: str,
    fallback: Path,
) -> dict[str, object]:
    artifact = _read_optional_artifact(
        explicit_path=explicit_path,
        bundle_manifest=bundle_manifest,
        bundle_dir=bundle_dir,
        bundle_key=bundle_key,
        fallback=fallback,
    )
    if artifact is None:
        raise FileNotFoundError(f"missing_websearch_bundle_artifact:{bundle_key}")
    return artifact


def _read_optional_artifact(
    *,
    explicit_path: str | None,
    bundle_manifest: dict[str, object] | None,
    bundle_dir: str | None,
    bundle_key: str,
    fallback: Path,
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
    if fallback.exists():
        return read_json_artifact(fallback)
    return None


if __name__ == "__main__":
    raise SystemExit(main())
