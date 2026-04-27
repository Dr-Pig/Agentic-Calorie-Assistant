from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    if len(sys.argv) < 2:
        raise SystemExit("usage: python scripts/run_powershell_hook.py <script.ps1> [args...]")

    shell = shutil.which("pwsh") or shutil.which("powershell")
    if shell is None:
        raise SystemExit("PowerShell runtime not found. Install pwsh or powershell to run this hook.")

    script_path = Path(sys.argv[1])
    if not script_path.is_absolute():
        script_path = ROOT / script_path

    command = [shell, "-ExecutionPolicy", "Bypass", "-File", str(script_path), *sys.argv[2:]]
    completed = subprocess.run(command, cwd=ROOT, check=False)
    return int(completed.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
