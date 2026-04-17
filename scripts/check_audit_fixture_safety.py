from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.audit_io_guard import load_json_audit_fixture


REGISTRY_PATH = ROOT / "docs" / "quality" / "AUDIT_FIXTURE_REGISTRY.json"
ALLOWED_AUTHORITY_TIERS = {
    "Official Golden",
    "Provisional Exploratory",
    "Smoke / Infra",
}
ALLOWED_VALIDATION_LAYERS = {
    "workflow_canonical_action",
    "pass_or_node_decision",
    "cross_turn_progression",
    "cross_workflow_boundary",
    "capability_service",
    "response_contract",
    "degraded_or_fallback",
    "smoke_infra",
}
ALLOWED_SUITE_ARCHETYPES = {
    "utterance_governed",
    "executable_workflow",
    "capability_service",
}
ALLOWED_APPROVAL_MODES = {
    "user_required",
    "agent_allowed",
}
ALLOWED_TRUTH_SOURCES = {
    "product_semantic_decision",
    "canonical_spec_derivation",
    "runtime_contract_derivation",
}
REQUIRED_METADATA_FIELDS = (
    "suite_id",
    "authority_tier",
    "workflow_family",
    "capability_family",
    "validation_layer",
    "suite_archetype",
    "approval_mode",
    "truth_source",
)


def main() -> int:
    try:
        registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError:
        print(f"[FAIL] missing audit fixture registry: {REGISTRY_PATH}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as exc:
        print(f"[FAIL] invalid audit fixture registry JSON: {exc}", file=sys.stderr)
        return 1

    if not isinstance(registry, list) or not registry:
        print("[FAIL] audit fixture registry must be a non-empty JSON list", file=sys.stderr)
        return 1

    seen_paths: set[str] = set()
    for entry in registry:
        if not isinstance(entry, dict):
            print("[FAIL] audit fixture registry entries must be objects", file=sys.stderr)
            return 1
        rel_path = entry.get("path")
        fixture_type = entry.get("type")
        if not isinstance(rel_path, str) or not rel_path:
            print("[FAIL] audit fixture registry entry missing string field 'path'", file=sys.stderr)
            return 1
        if fixture_type != "json":
            print(f"[FAIL] unsupported audit fixture type for {rel_path}: {fixture_type}", file=sys.stderr)
            return 1
        for field in REQUIRED_METADATA_FIELDS:
            value = entry.get(field)
            if not isinstance(value, str) or not value:
                print(
                    f"[FAIL] audit fixture registry entry missing string field '{field}' for {rel_path}",
                    file=sys.stderr,
                )
                return 1
        authority_tier = entry["authority_tier"]
        if authority_tier not in ALLOWED_AUTHORITY_TIERS:
            print(f"[FAIL] unsupported authority_tier for {rel_path}: {authority_tier}", file=sys.stderr)
            return 1
        validation_layer = entry["validation_layer"]
        if validation_layer not in ALLOWED_VALIDATION_LAYERS:
            print(
                f"[FAIL] unsupported validation_layer for {rel_path}: {validation_layer}",
                file=sys.stderr,
            )
            return 1
        suite_archetype = entry["suite_archetype"]
        if suite_archetype not in ALLOWED_SUITE_ARCHETYPES:
            print(f"[FAIL] unsupported suite_archetype for {rel_path}: {suite_archetype}", file=sys.stderr)
            return 1
        approval_mode = entry["approval_mode"]
        if approval_mode not in ALLOWED_APPROVAL_MODES:
            print(f"[FAIL] unsupported approval_mode for {rel_path}: {approval_mode}", file=sys.stderr)
            return 1
        truth_source = entry["truth_source"]
        if truth_source not in ALLOWED_TRUTH_SOURCES:
            print(f"[FAIL] unsupported truth_source for {rel_path}: {truth_source}", file=sys.stderr)
            return 1
        if rel_path in seen_paths:
            print(f"[FAIL] duplicate audit fixture path in registry: {rel_path}", file=sys.stderr)
            return 1
        seen_paths.add(rel_path)

        path = ROOT / rel_path
        if not path.exists():
            print(f"[FAIL] missing audit fixture: {rel_path}", file=sys.stderr)
            return 1

        load_json_audit_fixture(path=path, audit_name="audit_fixture_safety")

    print("[OK] audit fixture safety check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
