from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST_PATH = ROOT / "docs" / "quality" / "accurate_intake_mvp_gate_manifest.json"


@dataclass(frozen=True)
class GateGroup:
    group_id: str
    commands: tuple[tuple[str, ...], ...]


@dataclass(frozen=True)
class GatePlan:
    gate_id: str
    claim_scope: str
    not_claiming: tuple[str, ...]
    groups: tuple[GateGroup, ...]


def load_gate_manifest(path: Path = DEFAULT_MANIFEST_PATH) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _pytest_command(python_executable: str, tests: list[str]) -> tuple[str, ...]:
    return (python_executable, "-m", "pytest", *tests, "-q")


def build_gate_plan(manifest: dict[str, Any], *, python_executable: str = sys.executable) -> GatePlan:
    groups = []
    for group in manifest.get("required_groups", []):
        group_id = str(group["group_id"])
        tests = [str(item) for item in group.get("pytest", [])]
        groups.append(GateGroup(group_id=group_id, commands=(_pytest_command(python_executable, tests),)))
    return GatePlan(
        gate_id=str(manifest["gate_id"]),
        claim_scope=str(manifest["claim_scope"]),
        not_claiming=tuple(str(item) for item in manifest.get("not_claiming", [])),
        groups=tuple(groups),
    )


def run_gate(plan: GatePlan, *, fail_fast: bool = True) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    status = "pass"
    for group in plan.groups:
        group_returncode = 0
        command_results: list[dict[str, Any]] = []
        for command in group.commands:
            completed = subprocess.run(
                list(command),
                cwd=ROOT,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            command_results.append(
                {
                    "command": list(command),
                    "returncode": completed.returncode,
                    "stdout": completed.stdout,
                    "stderr": completed.stderr,
                }
            )
            if completed.returncode != 0:
                group_returncode = completed.returncode
                status = "fail"
                break
        results.append(
            {
                "group_id": group.group_id,
                "returncode": group_returncode,
                "status": "pass" if group_returncode == 0 else "fail",
                "commands": command_results,
            }
        )
        if fail_fast and group_returncode != 0:
            break
    return {
        "gate_id": plan.gate_id,
        "claim_scope": plan.claim_scope,
        "status": status,
        "not_claiming": list(plan.not_claiming),
        "groups": results,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the Accurate Intake MVP deterministic gate.")
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST_PATH))
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--no-fail-fast", action="store_true")
    args = parser.parse_args(argv)

    manifest = load_gate_manifest(Path(args.manifest))
    plan = build_gate_plan(manifest, python_executable=args.python)
    result = run_gate(plan, fail_fast=not args.no_fail_fast)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
