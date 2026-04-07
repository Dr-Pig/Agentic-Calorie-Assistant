from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import SCHEMA_SIGNATURE
from data_build.wide_research.base_nutrition_v2 import main


if __name__ == "__main__":
    raise SystemExit(main(["scaffold", "--schema-signature", SCHEMA_SIGNATURE, *sys.argv[1:]]))
