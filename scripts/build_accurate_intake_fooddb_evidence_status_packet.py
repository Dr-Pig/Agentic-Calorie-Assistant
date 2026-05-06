from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.nutrition.application.fooddb_evidence_status_packet import (  # noqa: E402
    build_fooddb_evidence_status_packet,
)
from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact  # noqa: E402
from scripts.fooddb_live_bundle_artifacts import (  # noqa: E402
    build_fooddb_live_bundle_artifact_paths,
    bundle_artifact_path_from_manifest,
)


DEFAULT_SMALL_ANCHOR_STORE = ROOT / "app" / "knowledge" / "small_anchor_store_tw.json"
DEFAULT_TFDA_SOURCE = ROOT / "app" / "knowledge" / "tfda_per100g_source_evidence_tw.json"
DEFAULT_EXACT_CARDS = ROOT / "app" / "knowledge" / "exact_item_cards_tw.json"
DEFAULT_OUTPUT = ROOT / "artifacts" / "accurate_intake_fooddb_evidence_status_packet.json"
DEFAULT_BUNDLE_DIR = ROOT / "artifacts" / "accurate_intake_fooddb_live_diagnostic_bundle"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build a compact FoodDB/WebSearch evidence status packet."
    )
    parser.add_argument("--small-anchor-store", default=str(DEFAULT_SMALL_ANCHOR_STORE))
    parser.add_argument("--tfda-source", default=str(DEFAULT_TFDA_SOURCE))
    parser.add_argument("--exact-cards", default=str(DEFAULT_EXACT_CARDS))
    parser.add_argument("--contract-handoff-artifact")
    parser.add_argument("--bundle-manifest")
    parser.add_argument("--bundle-dir")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args(argv)

    bundle_manifest = _read_bundle_manifest(args.bundle_manifest, args.bundle_dir)

    packet = build_fooddb_evidence_status_packet(
        small_anchor_payload=read_json_artifact(Path(args.small_anchor_store)),
        tfda_source_payload=read_json_artifact(Path(args.tfda_source)),
        exact_card_payload=read_json_artifact(Path(args.exact_cards)),
        contract_handoff_artifact=_read_optional_or_bundle(
            explicit_path=args.contract_handoff_artifact,
            bundle_manifest=bundle_manifest,
            bundle_dir=args.bundle_dir,
            bundle_key="manager_contract_handoff",
        ),
    )
    write_json_artifact(Path(args.output), packet)
    print(
        json.dumps(
            {
                "artifact": str(args.output),
                "claim_scope": packet["claim_scope"],
                "runtime_truth_changed": packet["runtime_truth_changed"],
                "readiness_claimed": packet["readiness_claimed"],
                "summary": packet["summary"],
                "next_required_slices": packet["next_required_slices"],
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
        manifest_path = build_fooddb_live_bundle_artifact_paths(Path(bundle_dir_arg))["manifest"]
    else:
        default_manifest = build_fooddb_live_bundle_artifact_paths(DEFAULT_BUNDLE_DIR)["manifest"]
        if default_manifest.exists():
            manifest_path = default_manifest
    if manifest_path is None or not manifest_path.exists():
        return None
    return read_json_artifact(manifest_path)


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
        bundle_path = build_fooddb_live_bundle_artifact_paths(Path(bundle_dir))[bundle_key]
        if bundle_path.exists():
            return read_json_artifact(bundle_path)
    return None


if __name__ == "__main__":
    raise SystemExit(main())
