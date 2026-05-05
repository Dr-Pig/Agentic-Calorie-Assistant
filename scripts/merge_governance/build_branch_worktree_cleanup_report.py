from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.merge_governance.build_merge_debt_matrix import ROOT  # noqa: E402


DEFAULT_JSON_OUT = ROOT / "artifacts" / "branch_worktree_cleanup_report.json"
DEFAULT_MD_OUT = ROOT / "artifacts" / "branch_worktree_cleanup_report.md"


def _run_text(command: list[str], *, cwd: Path = ROOT) -> str:
    completed = subprocess.run(
        command,
        cwd=cwd,
        check=False,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if completed.returncode != 0:
        return ""
    return completed.stdout


def _run_json(command: list[str], *, cwd: Path = ROOT) -> Any:
    text = _run_text(command, cwd=cwd)
    return json.loads(text) if text.strip() else []


def _approved_worktree_root() -> Path:
    common_dir_text = _run_text(["git", "rev-parse", "--git-common-dir"]).strip()
    common_dir = Path(common_dir_text)
    if not common_dir.is_absolute():
        common_dir = (ROOT / common_dir).resolve()
    project_name = common_dir.parent.name if common_dir.name == ".git" else ROOT.name
    return Path.home() / ".config" / "superpowers" / "worktrees" / project_name


def _inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True


def _parse_worktrees(raw: str) -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    current: dict[str, str] = {}
    for line in raw.splitlines():
        if not line.strip():
            if current:
                records.append(current)
                current = {}
            continue
        key, _, value = line.partition(" ")
        current[key] = value
    if current:
        records.append(current)
    return records


def _pr_state_by_head(limit: int) -> dict[str, dict[str, Any]]:
    prs = _run_json(["gh", "pr", "list", "--state", "all", "--limit", str(limit), "--json", "number,state,headRefName,title"])
    return {str(pr.get("headRefName") or ""): pr for pr in prs}


def _is_clean_worktree(path: Path) -> bool:
    return not _run_text(["git", "status", "--porcelain"], cwd=path).strip()


def classify_worktree(record: dict[str, Any]) -> str:
    if not record.get("inside_approved_root"):
        return "keep_outside_approved_root"
    if not record.get("clean"):
        return "keep_dirty"
    if record.get("branch") == "main":
        return "keep_main_worktree"
    pr_state = record.get("pr_state")
    if pr_state == "OPEN":
        return "keep_open_pr"
    if pr_state == "MERGED":
        return "remove_worktree_candidate"
    if pr_state is None:
        return "needs_review_no_pr"
    return "needs_review_closed_pr"


def classify_branch(record: dict[str, Any]) -> str:
    name = str(record.get("name") or "")
    if name in {"main", "master"}:
        return "keep_main_branch"
    if record.get("pr_state") == "OPEN":
        return "keep_open_pr"
    if int(record.get("unpushed_commits") or 0) > 0 and not record.get("merged_into_origin_main"):
        return "keep_unpushed"
    if (
        record.get("pr_state") == "MERGED"
        and record.get("merged_into_origin_main")
        and int(record.get("unpushed_commits") or 0) == 0
    ):
        return "delete_local_candidate"
    if record.get("pr_state") is None and record.get("merged_into_origin_main"):
        return "needs_review_no_pr_merged"
    return "needs_review"


def _branch_name_from_ref(ref: str) -> str:
    prefix = "refs/heads/"
    return ref[len(prefix) :] if ref.startswith(prefix) else ref


def collect_worktrees(*, pr_by_head: dict[str, dict[str, Any]], approved_root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in _parse_worktrees(_run_text(["git", "worktree", "list", "--porcelain"])):
        path = Path(item.get("worktree") or "")
        branch = _branch_name_from_ref(item.get("branch") or "")
        pr = pr_by_head.get(branch)
        row = {
            "path": str(path),
            "branch": branch,
            "clean": _is_clean_worktree(path) if path.exists() else False,
            "inside_approved_root": _inside(path, approved_root),
            "pr_number": pr.get("number") if pr else None,
            "pr_state": pr.get("state") if pr else None,
        }
        row["cleanup_verdict"] = classify_worktree(row)
        rows.append(row)
    return rows


def _ref_exists(ref: str) -> bool:
    return subprocess.run(
        ["git", "rev-parse", "--verify", "--quiet", ref],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    ).returncode == 0


def _merge_base_is_ancestor(ancestor: str, descendant: str) -> bool:
    return subprocess.run(
        ["git", "merge-base", "--is-ancestor", ancestor, descendant],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    ).returncode == 0


def _rev_list_count(left: str, right: str) -> int:
    text = _run_text(["git", "rev-list", "--count", f"{left}..{right}"])
    return int(text.strip() or 0)


def collect_local_branches(*, pr_by_head: dict[str, dict[str, Any]], main_ref: str = "origin/main") -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for branch in _run_text(["git", "branch", "--format=%(refname:short)"]).splitlines():
        remote_ref = f"origin/{branch}"
        remote_exists = _ref_exists(remote_ref)
        pr = pr_by_head.get(branch)
        row = {
            "name": branch,
            "remote_exists": remote_exists,
            "pr_number": pr.get("number") if pr else None,
            "pr_state": pr.get("state") if pr else None,
            "merged_into_origin_main": _merge_base_is_ancestor(branch, main_ref) if _ref_exists(main_ref) else False,
            "unpushed_commits": _rev_list_count(remote_ref, branch) if remote_exists else 0,
        }
        row["cleanup_verdict"] = classify_branch(row)
        rows.append(row)
    return rows


def build_cleanup_report(*, limit: int = 300, approved_root: Path | None = None) -> dict[str, Any]:
    pr_by_head = _pr_state_by_head(limit)
    root = approved_root or _approved_worktree_root()
    worktrees = collect_worktrees(pr_by_head=pr_by_head, approved_root=root)
    branches = collect_local_branches(pr_by_head=pr_by_head)
    return {
        "artifact_type": "branch_worktree_cleanup_report",
        "script_mutates_repository": False,
        "approved_worktree_root": str(root),
        "worktree_count": len(worktrees),
        "branch_count": len(branches),
        "worktrees": worktrees,
        "local_branches": branches,
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Branch and Worktree Cleanup Report",
        "",
        f"- Script mutates repository: `{str(report.get('script_mutates_repository')).lower()}`",
        f"- Approved worktree root: `{report.get('approved_worktree_root')}`",
        f"- Worktrees: `{report.get('worktree_count')}`",
        f"- Local branches: `{report.get('branch_count')}`",
        "",
        "## Worktrees",
        "",
        "| Path | Branch | Clean | PR | Verdict |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in report.get("worktrees") or []:
        pr = f"#{row['pr_number']} {row['pr_state']}" if row.get("pr_number") else "-"
        lines.append(
            f"| `{row['path']}` | `{row['branch']}` | `{row['clean']}` | {pr} | `{row['cleanup_verdict']}` |"
        )
    lines.extend(
        [
            "",
            "## Local Branches",
            "",
            "| Branch | Remote | PR | Merged into origin/main | Unpushed | Verdict |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )
    for row in report.get("local_branches") or []:
        pr = f"#{row['pr_number']} {row['pr_state']}" if row.get("pr_number") else "-"
        lines.append(
            f"| `{row['name']}` | `{row['remote_exists']}` | {pr} | "
            f"`{row['merged_into_origin_main']}` | `{row['unpushed_commits']}` | `{row['cleanup_verdict']}` |"
        )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a non-mutating branch/worktree cleanup candidate report.")
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON_OUT)
    parser.add_argument("--md-out", type=Path, default=DEFAULT_MD_OUT)
    parser.add_argument("--approved-worktree-root", type=Path)
    parser.add_argument("--limit", type=int, default=300)
    args = parser.parse_args(argv)

    report = build_cleanup_report(limit=args.limit, approved_root=args.approved_worktree_root)
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.md_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    args.md_out.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps({"json_report": str(args.json_out), "markdown_report": str(args.md_out)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
