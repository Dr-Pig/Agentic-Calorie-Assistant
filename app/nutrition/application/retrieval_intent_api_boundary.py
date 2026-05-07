from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
import re
from typing import Any


_AMBIGUOUS_BUILDER_NAME = "build_" "retrieval_intent"
_RAW_HINT_BUILDER_NAME = "build_" "raw_text_retrieval_hint"
_AMBIGUOUS_BUILDER_RE = re.compile(r"\b" + _AMBIGUOUS_BUILDER_NAME + r"\(")
_RAW_HINT_BUILDER_RE = re.compile(r"\b" + _RAW_HINT_BUILDER_NAME + r"\(")
_ALLOWED_RAW_HINT_CALL_FILES = (
    "app/nutrition/application/exact_brand_web_canary.py",
    "app/nutrition/application/retrieval_intent.py",
    "app/nutrition/application/retrieval_intent_runtime_boundary.py",
    "app/nutrition/application/retrieval_request.py",
)
_IGNORED_SCAN_FILES = (
    "app/nutrition/application/retrieval_intent.py",
    "app/nutrition/application/retrieval_intent_api_boundary.py",
    "scripts/build_accurate_intake_retrieval_intent_api_boundary.py",
)


def build_retrieval_intent_api_boundary_artifact(
    *,
    ambiguous_builder_call_files: tuple[str, ...] | None = None,
    raw_hint_call_files: tuple[str, ...] | None = None,
) -> dict[str, Any]:
    observed_ambiguous_calls = tuple(ambiguous_builder_call_files or _scan_call_files(_AMBIGUOUS_BUILDER_RE))
    observed_raw_hint_calls = tuple(raw_hint_call_files or _scan_call_files(_RAW_HINT_BUILDER_RE))
    unexpected_ambiguous_calls = tuple(sorted(observed_ambiguous_calls))
    unexpected_raw_hint_calls = tuple(
        sorted(path for path in observed_raw_hint_calls if path not in _ALLOWED_RAW_HINT_CALL_FILES)
    )
    blockers = [
        *[f"unexpected_ambiguous_retrieval_builder_call:{path}" for path in unexpected_ambiguous_calls],
        *[f"unexpected_raw_hint_builder_call:{path}" for path in unexpected_raw_hint_calls],
    ]
    return {
        "artifact_type": "accurate_intake_retrieval_intent_api_boundary_v1",
        "artifact_schema_version": "1.0",
        "generated_at_utc": _now(),
        "track": "FDB",
        "classification": "diagnostic_retrieval_hint_api_boundary_only",
        "claim_scope": "raw_text_retrieval_hint_api_must_stay_non_runtime",
        "status": "pass" if not blockers else "blocked",
        "blockers": blockers,
        "runtime_truth_changed": False,
        "mutation_changed": False,
        "shared_contract_changed": False,
        "manager_context_changed": False,
        "readiness_claimed": False,
        "ambiguous_builder_audit": {
            "builder_name": _AMBIGUOUS_BUILDER_NAME,
            "observed_call_files": list(observed_ambiguous_calls),
        },
        "raw_hint_builder_audit": {
            "builder_name": _RAW_HINT_BUILDER_NAME,
            "allowed_call_files": list(_ALLOWED_RAW_HINT_CALL_FILES),
            "observed_call_files": list(observed_raw_hint_calls),
            "unexpected_call_files": list(unexpected_raw_hint_calls),
        },
        "summary": {
            "ambiguous_builder_call_file_count": len(observed_ambiguous_calls),
            "unexpected_raw_hint_call_file_count": len(unexpected_raw_hint_calls),
            "runtime_boundary_guard_present": True,
        },
        "non_claims": [
            "no_runtime_truth_promotion",
            "no_runtime_mutation",
            "no_shared_contract_change",
            "no_manager_context_change",
            "no_readiness_claim",
        ],
    }


def _scan_call_files(pattern: re.Pattern[str]) -> list[str]:
    repo_root = Path(__file__).resolve().parents[3]
    observed: set[str] = set()
    for root_name in ("app", "scripts"):
        root = repo_root / root_name
        if not root.exists():
            continue
        for path in root.rglob("*.py"):
            relative_path = path.relative_to(repo_root).as_posix()
            if relative_path in _IGNORED_SCAN_FILES:
                continue
            for line in path.read_text(encoding="utf-8-sig").splitlines():
                stripped = line.lstrip()
                if stripped.startswith(f"def {_AMBIGUOUS_BUILDER_NAME}("):
                    continue
                if stripped.startswith(f"def {_RAW_HINT_BUILDER_NAME}("):
                    continue
                if pattern.search(line):
                    observed.add(relative_path)
                    break
    return sorted(observed)


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


__all__ = ["build_retrieval_intent_api_boundary_artifact"]
