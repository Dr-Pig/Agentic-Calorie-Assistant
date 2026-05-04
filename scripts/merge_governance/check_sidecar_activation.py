from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from scripts.merge_governance.build_merge_debt_matrix import (
    evaluate_sidecar_activation,
    extract_track_report,
    infer_track,
    load_config,
    normalize_pr_files,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check whether a future sidecar PR touches active runtime surfaces.")
    parser.add_argument("--pr-json", type=Path, required=True)
    parser.add_argument("--config", type=Path)
    args = parser.parse_args(argv)
    config = load_config(args.config) if args.config else load_config()
    pr = json.loads(args.pr_json.read_text(encoding="utf-8"))
    track = infer_track(pr)
    mainline_status = "future_shadow" if track in set(config["future_shadow_tracks"]) else "unknown"
    flags = extract_track_report(str(pr.get("body") or ""))
    files = normalize_pr_files(pr)
    boundary_status, runtime_status, findings = evaluate_sidecar_activation(
        track=track,
        mainline_status=mainline_status,
        files=files,
        flags=flags,
        config=config,
    )
    print(
        json.dumps(
            {"boundary_status": boundary_status, "runtime_activation_status": runtime_status, "findings": findings},
            ensure_ascii=False,
            indent=2,
        )
    )
    return 1 if boundary_status == "fail" else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
