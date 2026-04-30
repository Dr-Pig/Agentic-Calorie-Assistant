from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.shared.contracts.readiness_claim import validate_readiness_claim_integrity


DEFAULT_ARTIFACT_PATHS = (
    ROOT / "artifacts" / "wave1_phase_b_minimal_tool_loop_readiness.json",
    ROOT / "artifacts" / "wave1_phase_b2_evidence_synthesis_readiness.json",
    ROOT / "artifacts" / "wave1_founder_e2e_deterministic_diagnostic.json",
    ROOT / "artifacts" / "wave1_founder_e2e_live_diagnostic.json",
    ROOT / "artifacts" / "wave1_b2_active_runtime_integration_diagnostic.json",
    ROOT / "artifacts" / "wave1_phase_b2_live_llm_diagnostic_canary.json",
    ROOT / "artifacts" / "wave1_phase_b2_exact_brand_tavily_live_trace_canary.json",
)


def audit_readiness_claim_integrity(paths: list[Path] | None = None) -> dict[str, Any]:
    explicit_paths = paths is not None
    candidate_paths = paths if paths is not None else list(DEFAULT_ARTIFACT_PATHS)
    artifact_results: list[dict[str, Any]] = []
    missing_artifacts: list[str] = []

    for path in candidate_paths:
        resolved = path if path.is_absolute() else ROOT / path
        if not resolved.exists():
            missing_artifacts.append(_project_relative(resolved))
            if explicit_paths:
                artifact_results.append(
                    {
                        "artifact_path": _project_relative(resolved),
                        "passed": False,
                        "blockers": [
                            {
                                "code": "readiness_artifact_missing",
                                "detail": "Explicit readiness artifact path does not exist.",
                            }
                        ],
                        "warnings": [],
                    }
                )
            continue
        data = json.loads(resolved.read_text(encoding="utf-8"))
        result = validate_readiness_claim_integrity(data, artifact_path=_project_relative(resolved))
        artifact_results.append(result)

    blockers = [
        {
            "artifact_path": result.get("artifact_path"),
            "code": blocker.get("code"),
            "detail": blocker.get("detail"),
        }
        for result in artifact_results
        for blocker in result.get("blockers", [])
    ]
    report = {
        "artifact_type": "readiness_claim_integrity_audit",
        "generated_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "checked_artifact_count": len(artifact_results),
        "missing_artifacts": missing_artifacts,
        "passed": not blockers,
        "blockers": blockers,
        "artifact_results": artifact_results,
    }
    return _json_safe(report)


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit readiness artifacts for false-green claim integrity.")
    parser.add_argument("artifacts", nargs="*", help="Optional artifact paths. Defaults to official readiness artifacts.")
    args = parser.parse_args()
    paths = [Path(item) for item in args.artifacts] if args.artifacts else None
    report = audit_readiness_claim_integrity(paths)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 1


def _project_relative(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(ROOT).as_posix()
    except ValueError:
        return resolved.as_posix()


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


if __name__ == "__main__":
    raise SystemExit(main())
