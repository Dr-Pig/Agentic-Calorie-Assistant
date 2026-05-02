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


DEFAULT_DECISION_PACK_ARTIFACT = ROOT / "artifacts" / "accurate_intake_mvp_live_decision_pack.json"
DEFAULT_OUTPUT_DIR = ROOT / "artifacts"

_FORBIDDEN_TRUE_FLAGS = (
    "private_self_use_approved",
    "product_readiness_claimed",
    "production_selected",
    "mutation_rollout_approved",
    "runtime_web_activation_approved",
    "model_portability_claimed",
)


def build_accurate_intake_private_self_use_candidate(decision_pack: dict[str, Any]) -> dict[str, Any]:
    blockers = _input_blockers(decision_pack)
    candidate_prepared = not blockers
    return _json_safe(
        {
            "artifact_type": "accurate_intake_mvp_private_self_use_candidate",
            "artifact_schema_version": "1.0",
            "generated_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "source_artifact_type": decision_pack.get("artifact_type"),
            "claim_scope": "private_self_use_candidate_review",
            "candidate_prepared": candidate_prepared,
            "activation_status": "candidate_review_required" if candidate_prepared else "blocked",
            "requires_human_approval": candidate_prepared,
            "private_self_use_approved": False,
            "product_readiness_claimed": False,
            "production_selected": False,
            "mutation_rollout_approved": False,
            "runtime_web_activation_approved": False,
            "shadow_or_canary_approved": False,
            "model_portability_claimed": False,
            "max_model_claim": decision_pack.get("max_model_claim"),
            "input_integrity": {"passed": not blockers, "blockers": sorted(set(blockers))},
            "decision_pack_summary": {
                "selected_option": decision_pack.get("selected_option"),
                "selection_reason": decision_pack.get("selection_reason"),
                "private_self_use_candidate_prepared": decision_pack.get("private_self_use_candidate_prepared") is True,
                "requires_human_approval_for_private_self_use": (
                    decision_pack.get("requires_human_approval_for_private_self_use") is True
                ),
            },
            "evidence_summary": {
                "offline_replay_summary": _dict(decision_pack.get("offline_replay_summary")),
                "provider_robustness_summary": _dict(decision_pack.get("provider_robustness_summary")),
                "stage_summary": _dict(decision_pack.get("stage_summary")),
            },
            "non_claim_boundaries": {
                "private_self_use_is_approved": False,
                "product_ready": False,
                "production_manager_selected": False,
                "mutation_rollout_ready": False,
                "runtime_web_activation_ready": False,
            },
        }
    )


def write_accurate_intake_private_self_use_candidate(
    *,
    decision_pack_path: Path = DEFAULT_DECISION_PACK_ARTIFACT,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> Path:
    decision_pack = _dict(json.loads(decision_pack_path.read_text(encoding="utf-8")))
    candidate = build_accurate_intake_private_self_use_candidate(decision_pack)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "accurate_intake_mvp_private_self_use_candidate.json"
    path.write_text(json.dumps(candidate, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _input_blockers(decision_pack: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if decision_pack.get("artifact_type") != "accurate_intake_mvp_live_decision_pack":
        blockers.append("decision_pack_artifact_type_invalid")
    if decision_pack.get("selected_option") != "prepare_private_self_use_candidate":
        blockers.append("decision_pack_not_candidate")
    if decision_pack.get("private_self_use_candidate_prepared") is not True:
        blockers.append("decision_pack_candidate_not_prepared")
    if decision_pack.get("requires_human_approval_for_private_self_use") is not True:
        blockers.append("decision_pack_human_approval_flag_missing")
    for flag in _FORBIDDEN_TRUE_FLAGS:
        if decision_pack.get(flag) is True:
            blockers.append(f"decision_pack_{flag}")
    return blockers


def _dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Accurate Intake MVP private self-use candidate artifact.")
    parser.add_argument("--decision-pack", default=str(DEFAULT_DECISION_PACK_ARTIFACT))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()
    output = write_accurate_intake_private_self_use_candidate(
        decision_pack_path=Path(args.decision_pack),
        output_dir=Path(args.output_dir),
    )
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
