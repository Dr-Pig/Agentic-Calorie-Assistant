from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.advanced_shadow_lab.product_lab_activation_wall_audit import (  # noqa: E402
    build_product_lab_activation_wall_audit,
)
from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build the advanced product-lab activation-wall audit."
    )
    parser.add_argument("--closure-pack-json", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)

    audit = build_product_lab_activation_wall_audit(
        closure_pack=read_json_artifact(args.closure_pack_json),
        repo_root=ROOT,
        source_closure_pack_path=args.closure_pack_json,
    )
    write_json_artifact(args.output, audit)
    print(json.dumps(audit, ensure_ascii=False))
    return 0 if audit["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
