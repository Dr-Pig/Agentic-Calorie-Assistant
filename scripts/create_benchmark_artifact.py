from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_DIR = ROOT / "docs" / "quality" / "benchmarks" / "templates"
TEMPLATES = {
    "candidate_queue": TEMPLATE_DIR / "candidate_review_queue_template.json",
    "official_pack": TEMPLATE_DIR / "official_canonical_pack_template.json",
    "executable_pack": TEMPLATE_DIR / "executable_action_pack_template.json",
}


def _render(template_name: str, replacements: dict[str, str]) -> str:
    template_path = TEMPLATES[template_name]
    text = template_path.read_text(encoding="utf-8")
    for key, value in replacements.items():
        text = text.replace(key, value)
    return text


def main() -> int:
    parser = argparse.ArgumentParser(description="Scaffold a benchmark artifact from a checked-in template.")
    parser.add_argument("--template", choices=sorted(TEMPLATES), required=True)
    parser.add_argument("--output", required=True, help="Repo-relative output path.")
    parser.add_argument("--replace", action="append", default=[], help="Replacement of the form KEY=VALUE.")
    args = parser.parse_args()

    replacements: dict[str, str] = {}
    for item in args.replace:
        if "=" not in item:
            raise SystemExit(f"invalid replacement: {item!r}")
        key, value = item.split("=", 1)
        replacements[key] = value

    rendered = _render(args.template, replacements)
    payload = json.loads(rendered)
    output_path = ROOT / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"[OK] wrote {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
