from __future__ import annotations

from pathlib import Path


def build_evidence_track_live_bundle_artifact_paths(output_dir: Path) -> dict[str, Path]:
    return {
        "fooddb_dir": output_dir / "fooddb_bundle",
        "websearch_dir": output_dir / "websearch_bundle",
        "handoff": output_dir / "evidence_track_live_handoff.json",
        "manifest": output_dir / "evidence_track_live_manifest.json",
    }


__all__ = ["build_evidence_track_live_bundle_artifact_paths"]
