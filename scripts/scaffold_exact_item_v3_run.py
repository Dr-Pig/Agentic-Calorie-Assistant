from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from data_build.wide_research.exact_item_v3 import main


if __name__ == "__main__":
    raise SystemExit(main(["scaffold"]))
