from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[2]


def _run(command: list[str], *, cwd: Path) -> dict[str, object]:
    completed = subprocess.run(
        command,
        cwd=cwd,
        check=False,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    return {"command": command, "exit_code": completed.returncode, "output": completed.stdout[-4000:]}


def simulate(*, pr_head: str, main_branch: str, gate_commands: list[list[str]]) -> dict[str, object]:
    temp_root = Path(tempfile.mkdtemp(prefix="merge-governance-"))
    worktree = temp_root / "candidate"
    results: list[dict[str, object]] = []
    try:
        results.append(_run(["git", "worktree", "add", "--detach", str(worktree), f"origin/{main_branch}"], cwd=ROOT))
        if results[-1]["exit_code"] != 0:
            return {"status": "failed", "results": results}
        results.append(_run(["git", "merge", "--no-commit", "--no-ff", f"origin/{pr_head}"], cwd=worktree))
        if results[-1]["exit_code"] != 0:
            return {"status": "merge_conflict_or_failed", "results": results}
        for command in gate_commands:
            result = _run(command, cwd=worktree)
            results.append(result)
            if result["exit_code"] != 0:
                return {"status": "gate_failed", "results": results}
        return {"status": "pass", "results": results}
    finally:
        subprocess.run(["git", "worktree", "remove", "--force", str(worktree)], cwd=ROOT, check=False)
        shutil.rmtree(temp_root, ignore_errors=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Simulate applying a PR branch to origin/main in a temporary worktree.")
    parser.add_argument("--head", required=True, help="Remote head branch name, for example codex/my-pr.")
    parser.add_argument("--main", default="main")
    parser.add_argument(
        "--gate",
        action="append",
        default=[],
        help="Gate command as a JSON array, for example '[\"python\",\"scripts/check_runtime_boundaries.py\"]'.",
    )
    args = parser.parse_args(argv)
    gates = [json.loads(item) for item in args.gate]
    report = simulate(pr_head=args.head, main_branch=args.main, gate_commands=gates)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
