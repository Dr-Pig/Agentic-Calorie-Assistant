from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


def resolve_codex_bin() -> str:
    explicit = os.environ.get("PLANNER_LOOP_CODEX_BIN")
    if explicit:
        return explicit

    direct = shutil.which("codex.cmd") or shutil.which("codex")
    if direct and direct.lower().endswith(".cmd"):
        return direct
    if direct and "windowsapps" not in direct.lower():
        return direct

    localappdata = Path(os.environ.get("LOCALAPPDATA", ""))
    winget_root = localappdata / "Microsoft" / "WinGet" / "Packages"
    if winget_root.exists():
        matches = sorted(winget_root.glob("OpenJS.NodeJS.*/*/codex.cmd"))
        if matches:
            return str(matches[-1])

    return "codex"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prompt-file", required=True)
    parser.add_argument("--cd", required=True)
    parser.add_argument("--mode", choices=["worker", "reviewer"], required=True)
    args = parser.parse_args()

    prompt = Path(args.prompt_file).read_text(encoding="utf-8")
    codex_bin = resolve_codex_bin()
    cmd = [
        codex_bin,
        "exec",
        "-",
        "--sandbox",
        "workspace-write",
        "-C",
        args.cd,
    ]
    proc = subprocess.run(
        cmd,
        input=prompt,
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.stdout:
        sys.stdout.write(proc.stdout)
    if proc.stderr:
        sys.stderr.write(proc.stderr)
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
