from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.repo_policy import (
    ROOT,
    category_for_repo_path,
    effective_cap_for_repo_path,
    iter_active_python_files,
    line_count,
    load_active_code_policy,
    normalize_repo_path,
    target_cap_for_repo_path,
    top_level_domain,
)


DEFAULT_JSON_PATH = ROOT / "artifacts" / "active_code_inventory.json"
DEFAULT_MD_PATH = ROOT / "artifacts" / "active_code_inventory.md"


def build_active_code_inventory() -> dict[str, Any]:
    policy = load_active_code_policy()
    rows: list[dict[str, Any]] = []
    over_target: list[dict[str, Any]] = []
    unmapped: list[str] = []
    for path in iter_active_python_files(policy):
        repo_path = normalize_repo_path(path)
        category = category_for_repo_path(repo_path, policy)
        effective_cap = effective_cap_for_repo_path(repo_path, policy)
        target_cap = target_cap_for_repo_path(repo_path, policy)
        lines = line_count(path)
        row = {
            "path": repo_path,
            "domain": top_level_domain(path),
            "category": category,
            "line_count": lines,
            "target_cap": target_cap,
            "effective_cap": effective_cap,
            "over_target": bool(target_cap is not None and lines > target_cap),
            "over_effective": bool(effective_cap is not None and lines > effective_cap),
            "uses_transition_override": bool(
                repo_path in policy.get("transition_overrides", {})
            ),
        }
        rows.append(row)
        if category is None:
            unmapped.append(repo_path)
        if row["over_target"]:
            over_target.append(row)

    over_target.sort(key=lambda item: (item["line_count"] - (item["target_cap"] or 0)), reverse=True)
    return {
        "policy_version": policy["policy_version"],
        "category_caps": policy["category_caps"],
        "files": rows,
        "unmapped_files": unmapped,
        "over_target_files": over_target,
    }


def render_markdown(report: dict[str, Any]) -> str:
    rows = sorted(report["files"], key=lambda item: item["line_count"], reverse=True)
    lines = [
        "# Active Code Inventory",
        "",
        "| Path | Domain | Category | Lines | Target | Effective | Over Target | Transition |",
        "| --- | --- | --- | ---: | ---: | ---: | --- | --- |",
    ]
    for row in rows[:80]:
        lines.append(
            f"| `{row['path']}` | `{row['domain']}` | `{row['category'] or 'unmapped'}` | {row['line_count']} | "
            f"{row['target_cap'] or '-'} | {row['effective_cap'] or '-'} | {str(row['over_target']).lower()} | "
            f"{str(row['uses_transition_override']).lower()} |"
        )
    if report["unmapped_files"]:
        lines.extend(["", "## Unmapped Files", ""])
        lines.extend(f"- `{path}`" for path in report["unmapped_files"])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate an active-code inventory from the repo policy.")
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON_PATH)
    parser.add_argument("--md-out", type=Path, default=DEFAULT_MD_PATH)
    args = parser.parse_args()

    report = build_active_code_inventory()
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    args.md_out.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps({"json_report": str(args.json_out), "markdown_report": str(args.md_out)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
