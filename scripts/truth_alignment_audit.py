from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.repo_policy import ROOT, focus_modules, line_count, load_active_code_policy, normalize_repo_path


DEFAULT_JSON_PATH = ROOT / "artifacts" / "truth_alignment_audit.json"
DEFAULT_MD_PATH = ROOT / "artifacts" / "truth_alignment_audit.md"


REFERENCE_ROOTS = (
    ROOT / "app",
    ROOT / "tests",
    ROOT / "scripts",
    ROOT / "docs",
)


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _reference_summary(target_path: str) -> dict[str, Any]:
    path_token = target_path.replace("/", ".").removesuffix(".py")
    file_token = Path(target_path).name
    counts = {"app": 0, "tests": 0, "scripts": 0, "docs": 0}
    samples: list[str] = []
    for root in REFERENCE_ROOTS:
        for candidate in root.rglob("*"):
            if not candidate.is_file():
                continue
            normalized = normalize_repo_path(candidate)
            if normalized == target_path or "__pycache__" in normalized:
                continue
            if candidate.suffix.lower() not in {".py", ".md", ".json"}:
                continue
            content = _read_text(candidate)
            if path_token not in content and file_token not in content:
                continue
            bucket = normalized.split("/")[0]
            if bucket in counts:
                counts[bucket] += 1
            if len(samples) < 8:
                samples.append(normalized)
    return {"counts": counts, "sample_paths": samples}


def build_truth_alignment_audit() -> dict[str, Any]:
    policy = load_active_code_policy()
    focus = focus_modules(policy)
    modules: list[dict[str, Any]] = []
    suspicious_residue: list[dict[str, Any]] = []
    for repo_path, entry in focus.items():
        path = ROOT / repo_path
        if not path.exists():
            continue
        refs = _reference_summary(repo_path)
        item = {
            "path": repo_path,
            "classification": entry["classification"],
            "recommended_action": entry["recommended_action"],
            "line_count": line_count(path),
            "reference_counts": refs["counts"],
            "reference_samples": refs["sample_paths"],
            "note": entry["note"],
        }
        modules.append(item)
        if entry["classification"] in {"later_wave_premature_active", "historical_workaround_residue"}:
            suspicious_residue.append(item)

    domain_status = policy.get("domain_status", {})
    skeleton_inventory: list[dict[str, Any]] = []
    app_root = ROOT / "app"
    for domain_dir in sorted(path for path in app_root.iterdir() if path.is_dir()):
        layers = sorted(
            child.name
            for child in domain_dir.iterdir()
            if child.is_dir() and child.name not in {"__pycache__"}
        )
        skeleton_inventory.append(
            {
                "domain": domain_dir.name,
                "status": domain_status.get(domain_dir.name, "missing_but_should_not_exist_yet"),
                "layers": layers,
            }
        )

    note_map = {item["path"]: item for item in modules}
    return {
        "policy_version": policy["policy_version"],
        "focus_modules": modules,
        "suspicious_residue": suspicious_residue,
        "domain_skeleton_inventory": skeleton_inventory,
        "short_audit_notes": {
            "app/rescue/application/proposal.py": note_map.get("app/rescue/application/proposal.py"),
            "app/providers/builderspace_adapter.py": note_map.get("app/providers/builderspace_adapter.py"),
        },
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Truth Alignment Audit",
        "",
        "## Focus Modules",
        "",
        "| Path | Classification | Action | Lines | App | Tests | Scripts | Docs |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for item in report["focus_modules"]:
        refs = item["reference_counts"]
        lines.append(
            f"| `{item['path']}` | `{item['classification']}` | `{item['recommended_action']}` | "
            f"{item['line_count']} | {refs['app']} | {refs['tests']} | {refs['scripts']} | {refs['docs']} |"
        )

    lines.extend(["", "## Suspicious Residue", ""])
    for item in report["suspicious_residue"]:
        lines.append(f"- `{item['path']}`: `{item['classification']}` -> `{item['recommended_action']}`")
        lines.append(f"  note: {item['note']}")

    lines.extend(["", "## Domain Skeleton Inventory", "", "| Domain | Status | Layers |", "| --- | --- | --- |"])
    for item in report["domain_skeleton_inventory"]:
        layers = ", ".join(item["layers"]) if item["layers"] else "(none)"
        lines.append(f"| `{item['domain']}` | `{item['status']}` | {layers} |")

    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a truth-alignment audit for active code.")
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON_PATH)
    parser.add_argument("--md-out", type=Path, default=DEFAULT_MD_PATH)
    args = parser.parse_args()

    report = build_truth_alignment_audit()
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    args.md_out.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps({"json_report": str(args.json_out), "markdown_report": str(args.md_out)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
