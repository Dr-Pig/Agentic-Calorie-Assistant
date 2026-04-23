from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.text_integrity import corruption_summary, find_text_corruption


def _load_payload(path: Path) -> Any:
    text = path.read_text(encoding="utf-8")
    return json.loads(text)


def main() -> int:
    parser = argparse.ArgumentParser(description="Fail if JSON artifacts contain mangled text markers.")
    parser.add_argument("paths", nargs="+", help="JSON file paths to scan")
    args = parser.parse_args()

    failed = False
    for raw_path in args.paths:
        path = Path(raw_path)
        payload = _load_payload(path)
        findings = find_text_corruption(payload)
        if findings:
            failed = True
            print(json.dumps({"path": str(path), "findings": corruption_summary(findings)}, ensure_ascii=False, indent=2))
        else:
            print(json.dumps({"path": str(path), "status": "ok"}, ensure_ascii=False))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
