"""Classify the local verification runtime for Phase C gates."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any


MIN_AUTHORITATIVE_PYTHON = (3, 12)


def classify_runtime_authority(python_version: tuple[int, int, int]) -> str:
    if python_version[:2] >= MIN_AUTHORITATIVE_PYTHON:
        return "python_312_plus"
    return "not_authoritative"


def resolve_verification_runtime(
    *,
    docker_available: bool,
    python_version: tuple[int, int, int],
    venv_path: str | None,
) -> dict[str, Any]:
    if docker_available:
        return {
            "status": "docker_preferred",
            "runtime": "docker_compose",
            "authoritative_for": ["local_phase_c_verification", "container_parity"],
            "not_authoritative_for": [],
            "ci_final_authority": True,
            "do_not_change_product_code_for_python_39": True,
        }

    if classify_runtime_authority(python_version) == "python_312_plus":
        return {
            "status": "local_fallback",
            "runtime": venv_path or "python_312_plus",
            "authoritative_for": ["local_phase_c_verification"],
            "not_authoritative_for": ["container_parity", "os_service_parity"],
            "ci_final_authority": True,
            "do_not_change_product_code_for_python_39": True,
        }

    return {
        "status": "blocked",
        "blocker": "python_312_runtime_missing",
        "runtime": "none",
        "authoritative_for": [],
        "not_authoritative_for": [
            "local_phase_c_verification",
            "container_parity",
            "os_service_parity",
        ],
        "ci_final_authority": True,
        "do_not_change_product_code_for_python_39": True,
    }


def _venv_path_for_executable(executable: str) -> str | None:
    path = Path(executable).resolve()
    for parent in path.parents:
        if parent.name.startswith(".venv"):
            return parent.name
    return None


def _docker_compose_available() -> bool:
    try:
        result = subprocess.run(
            ("docker", "compose", "version"),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    except FileNotFoundError:
        return False
    return result.returncode == 0


def main() -> int:
    docker_available = _docker_compose_available()
    python_version = sys.version_info[:3]
    result = resolve_verification_runtime(
        docker_available=docker_available,
        python_version=python_version,
        venv_path=_venv_path_for_executable(sys.executable),
    )
    result["python_version"] = ".".join(str(part) for part in python_version)
    result["python_executable"] = sys.executable
    result["docker_available"] = docker_available
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] != "blocked" else 2


if __name__ == "__main__":
    raise SystemExit(main())
