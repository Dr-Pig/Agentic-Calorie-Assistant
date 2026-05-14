from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.composition.current_shell_golden_set_request_trace_adapter import (  # noqa: E402
    build_golden_case_trace_from_request_trace,
    build_golden_trace_artifact_from_request_traces,
)


DEFAULT_OUTPUT_PATH = ROOT / "artifacts" / "current_shell_self_use_golden_set_trace_artifact.json"


def build_trace_artifact_from_specs(case_trace_specs: list[str]) -> dict[str, Any]:
    cases = []
    for spec in case_trace_specs:
        case_id, path, assertions_path = _parse_case_trace_spec(spec)
        request_trace = _read_json(path)
        assertions = _read_json(assertions_path) if assertions_path is not None else None
        cases.append(
            build_golden_case_trace_from_request_trace(
                case_id,
                request_trace,
                case_assertions=assertions,
            )
        )
    return build_golden_trace_artifact_from_request_traces(cases)


def write_trace_artifact_from_specs(
    *,
    case_trace_specs: list[str],
    output_path: Path = DEFAULT_OUTPUT_PATH,
) -> Path:
    artifact = build_trace_artifact_from_specs(case_trace_specs)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output_path


def _parse_case_trace_spec(spec: str) -> tuple[str, Path, Path | None]:
    parts = spec.split("=", 2)
    if len(parts) not in {2, 3}:
        raise ValueError("case trace spec must be CASE_ID=REQUEST_TRACE_JSON[=ASSERTIONS_JSON]")
    case_id = parts[0].strip()
    if not case_id:
        raise ValueError("case trace spec case id is required")
    request_trace_path = Path(parts[1])
    assertions_path = Path(parts[2]) if len(parts) == 3 and parts[2].strip() else None
    return case_id, request_trace_path, assertions_path


def _read_json(path: Path) -> dict[str, Any]:
    loaded = json.loads(path.read_text(encoding="utf-8"))
    return dict(loaded) if isinstance(loaded, dict) else {}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Project real request trace JSON files into a Current Shell Golden Set trace artifact."
    )
    parser.add_argument(
        "--case-trace",
        action="append",
        default=[],
        help="CASE_ID=REQUEST_TRACE_JSON or CASE_ID=REQUEST_TRACE_JSON=ASSERTIONS_JSON",
    )
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH))
    args = parser.parse_args()
    output = write_trace_artifact_from_specs(
        case_trace_specs=list(args.case_trace),
        output_path=Path(args.output),
    )
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
