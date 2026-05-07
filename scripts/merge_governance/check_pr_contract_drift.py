from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from scripts.merge_governance.build_merge_governance_advisory import detect_contract_drift


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Scan PR text/diff for stale architecture contract markers.")
    parser.add_argument("--text-file", type=Path, required=True)
    args = parser.parse_args(argv)
    findings = detect_contract_drift({"body": args.text_file.read_text(encoding="utf-8")})
    print(json.dumps({"status": "fail" if findings else "pass", "findings": findings}, ensure_ascii=False, indent=2))
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
