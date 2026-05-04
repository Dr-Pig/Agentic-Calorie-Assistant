from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from scripts.merge_governance.build_merge_debt_matrix import REQUIRED_TRACK_REPORT_KEYS, extract_track_report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate required merge-governance track-report fields in PR body text.")
    parser.add_argument("--body-file", type=Path, required=True)
    args = parser.parse_args(argv)
    flags = extract_track_report(args.body_file.read_text(encoding="utf-8"))
    missing = [key for key in REQUIRED_TRACK_REPORT_KEYS if key not in flags]
    print(json.dumps({"status": "fail" if missing else "pass", "missing": missing}, ensure_ascii=False, indent=2))
    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
