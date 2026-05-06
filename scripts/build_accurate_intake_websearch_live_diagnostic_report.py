from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.nutrition.application.websearch_live_diagnostic_report import (  # noqa: E402
    build_websearch_live_diagnostic_report,
)
from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact  # noqa: E402
from scripts.websearch_live_bundle_artifacts import (  # noqa: E402
    build_websearch_live_bundle_artifact_paths,
    bundle_artifact_path_from_manifest,
)


DEFAULT_INPUT = ROOT / "artifacts" / "accurate_intake_grokfast_websearch_packet_smoke.json"
DEFAULT_PREFLIGHT = ROOT / "artifacts" / "accurate_intake_websearch_live_extract_preflight.json"
DEFAULT_OUTPUT = ROOT / "artifacts" / "accurate_intake_websearch_live_diagnostic_report.json"
DEFAULT_BUNDLE_DIR = ROOT / "artifacts" / "accurate_intake_websearch_live_diagnostic_bundle"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build WebSearch live diagnostic report from a sanitized GrokFast packet smoke artifact."
    )
    parser.add_argument("--diagnostic-artifact")
    parser.add_argument("--preflight-artifact")
    parser.add_argument("--bundle-manifest")
    parser.add_argument("--bundle-dir")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args(argv)

    bundle_manifest = _read_bundle_manifest(args.bundle_manifest, args.bundle_dir)
    diagnostic_path = _resolve_diagnostic_path(args.diagnostic_artifact, bundle_manifest, args.bundle_dir)
    preflight_path = _resolve_preflight_path(args.preflight_artifact, bundle_manifest, args.bundle_dir)

    diagnostic_artifact = read_json_artifact(diagnostic_path)
    preflight_artifact = read_json_artifact(preflight_path) if preflight_path.exists() else None
    report = build_websearch_live_diagnostic_report(
        diagnostic_artifact=diagnostic_artifact,
        preflight_artifact=preflight_artifact,
    )
    output_path = Path(args.output)
    write_json_artifact(output_path, report)
    print(
        json.dumps(
            {
                "artifact": str(output_path),
                "claim_scope": report["claim_scope"],
                "seam_status": report["seam_status"],
                "next_recommended_slice": report["next_recommended_slice"],
                "can_expand_websearch_candidate_pipeline": report[
                    "can_expand_websearch_candidate_pipeline"
                ],
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


def _resolve_diagnostic_path(
    diagnostic_arg: str | None,
    bundle_manifest: dict[str, object] | None,
    bundle_dir_arg: str | None,
) -> Path:
    if diagnostic_arg:
        return Path(diagnostic_arg)
    if bundle_manifest is not None:
        bundle_path = bundle_artifact_path_from_manifest(bundle_manifest, key="diagnostic")
        if bundle_path is not None:
            return bundle_path
    if bundle_dir_arg:
        return build_websearch_live_bundle_artifact_paths(Path(bundle_dir_arg))["diagnostic"]
    default_bundle_path = build_websearch_live_bundle_artifact_paths(DEFAULT_BUNDLE_DIR)["diagnostic"]
    if default_bundle_path.exists():
        return default_bundle_path
    return DEFAULT_INPUT


def _resolve_preflight_path(
    preflight_arg: str | None,
    bundle_manifest: dict[str, object] | None,
    bundle_dir_arg: str | None,
) -> Path:
    if preflight_arg:
        return Path(preflight_arg)
    if bundle_manifest is not None:
        bundle_path = bundle_artifact_path_from_manifest(bundle_manifest, key="preflight")
        if bundle_path is not None:
            return bundle_path
    if bundle_dir_arg:
        return build_websearch_live_bundle_artifact_paths(Path(bundle_dir_arg))["preflight"]
    default_bundle_path = build_websearch_live_bundle_artifact_paths(DEFAULT_BUNDLE_DIR)["preflight"]
    if default_bundle_path.exists():
        return default_bundle_path
    return DEFAULT_PREFLIGHT


if __name__ == "__main__":
    raise SystemExit(main())
