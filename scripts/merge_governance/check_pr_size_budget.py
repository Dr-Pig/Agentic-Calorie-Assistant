from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from scripts.merge_governance.build_merge_governance_advisory import (
    evaluate_size_budget,
    infer_track,
    load_config,
    normalize_pr_files,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check PR additions against merge-governance size budgets.")
    parser.add_argument("--pr-json", type=Path, required=True)
    parser.add_argument("--config", type=Path)
    args = parser.parse_args(argv)
    config = load_config(args.config) if args.config else load_config()
    pr = json.loads(args.pr_json.read_text(encoding="utf-8"))
    track = infer_track(pr)
    if track in set(config["future_shadow_tracks"]):
        mainline_status = "future_shadow"
    elif track in set(config["mvp_mainline_tracks"]):
        mainline_status = "mvp_mainline"
    else:
        mainline_status = "unknown"
    status, findings = evaluate_size_budget(
        mainline_status=mainline_status,
        additions=int(pr.get("additions") or 0),
        files=normalize_pr_files(pr),
        config=config,
    )
    print(json.dumps({"fat_file_status": status, "findings": findings}, ensure_ascii=False, indent=2))
    return 1 if status == "fail" else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
