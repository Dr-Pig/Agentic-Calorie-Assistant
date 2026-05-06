from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.composition.accurate_intake_manager_tool_choice_regression_wall import (  # noqa: E402
    build_manager_tool_choice_regression_wall_artifact,
)
from app.composition.accurate_intake_manager_tool_surface_inventory import (  # noqa: E402
    build_manager_tool_surface_inventory_artifact,
)
from app.composition.accurate_intake_non_fooddb_mutation_tool_guard_smoke import (  # noqa: E402
    build_non_fooddb_mutation_tool_guard_smoke_artifact,
)
from app.composition.accurate_intake_non_fooddb_read_only_tool_loop_fake_smoke import (  # noqa: E402
    build_non_fooddb_read_only_tool_loop_fake_smoke_artifact,
)
from app.composition.accurate_intake_pl_ce_browser_activation_evidence_gate import (  # noqa: E402
    REQUIRED_INPUTS as BROWSER_GATE_REQUIRED_INPUTS,
    build_pl_ce_browser_activation_evidence_gate_artifact,
)
from app.composition.accurate_intake_pl_ce_product_pages_self_use_flow_gate import (  # noqa: E402
    build_pl_ce_product_pages_self_use_flow_gate_artifact,
)
from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact  # noqa: E402
from scripts.build_accurate_intake_pl_ce_product_pages_self_use_flow_gate import (  # noqa: E402
    DEFAULT_ARTIFACT_PATHS as PRODUCT_PAGES_FLOW_ARTIFACT_PATHS,
    build_input_artifacts as build_product_pages_flow_inputs,
)
from scripts.build_accurate_intake_local_web_self_use_candidate_v2 import (  # noqa: E402
    build_local_web_self_use_candidate_v2,
)
from scripts.build_accurate_intake_pl_ce_browser_activation_evidence_gate import (  # noqa: E402
    DEFAULT_ARTIFACT_PATHS as BROWSER_GATE_ARTIFACT_PATHS,
)
from scripts.build_accurate_intake_pre_live_self_use_decision_pack import (  # noqa: E402
    build_pre_live_self_use_decision_pack,
)
from scripts.run_accurate_intake_context_live_diagnostic_gate import (  # noqa: E402
    build_context_live_diagnostic_gate_artifact,
)
from scripts.run_accurate_intake_local_web_self_use_candidate_v2_gate import (  # noqa: E402
    DEFAULT_EVIDENCE_PATHS,
    build_candidate_evidence_payload,
    build_local_web_candidate_gate_evidence,
)


REFRESHED_ARTIFACT_FILENAMES = {
    "manager_tool_surface_inventory": "accurate_intake_manager_tool_surface_inventory.json",
    "manager_tool_choice_regression_wall": "accurate_intake_manager_tool_choice_regression_wall.json",
    "non_fooddb_read_only_tool_loop_fake_smoke": "accurate_intake_non_fooddb_read_only_tool_loop_fake_smoke.json",
    "non_fooddb_mutation_tool_guard_smoke": "accurate_intake_non_fooddb_mutation_tool_guard_smoke.json",
    "product_pages_self_use_flow_gate": "accurate_intake_pl_ce_product_pages_self_use_flow_gate.json",
    "browser_activation_evidence_gate": "accurate_intake_pl_ce_browser_activation_evidence_gate.json",
    "context_live_diagnostic_gate": "accurate_intake_context_live_diagnostic_gate.json",
    "pre_live_evidence": "accurate_intake_pre_live_evidence.json",
    "pre_live_decision_pack": "accurate_intake_pre_live_self_use_decision_pack.json",
    "local_web_candidate": "accurate_intake_local_web_self_use_candidate_v2.json",
}


def _artifact_path(artifacts_dir: Path, filename: str) -> Path:
    return artifacts_dir / filename


def _group_path(artifacts_dir: Path, path: Path) -> Path:
    return artifacts_dir / path.name


def _read_payload(path: Path) -> dict[str, Any]:
    try:
        payload = read_json_artifact(path)
    except FileNotFoundError:
        return {
            "artifact_type": "missing",
            "status": "missing",
            "_source_artifact_path": str(path),
            "autofix_attempted": False,
        }
    except (OSError, ValueError, json.JSONDecodeError):
        return {
            "artifact_type": "invalid_json",
            "status": "invalid_json",
            "_source_artifact_path": str(path),
            "autofix_attempted": False,
        }
    payload.setdefault("_source_artifact_path", str(path))
    return payload


def _browser_gate_inputs(artifacts_dir: Path) -> dict[str, dict[str, Any]]:
    return {
        group_id: _read_payload(_group_path(artifacts_dir, BROWSER_GATE_ARTIFACT_PATHS[group_id]))
        for group_id in BROWSER_GATE_REQUIRED_INPUTS
    }


def _product_pages_flow_path_overrides(artifacts_dir: Path) -> dict[str, Path]:
    return {
        group_id: _group_path(artifacts_dir, path)
        for group_id, path in PRODUCT_PAGES_FLOW_ARTIFACT_PATHS.items()
    }


def _local_gate_path_overrides(artifacts_dir: Path) -> dict[str, Path]:
    return {
        group_id: _group_path(artifacts_dir, path)
        for group_id, path in DEFAULT_EVIDENCE_PATHS.items()
    }


def build_local_web_self_use_candidate_refresh_chain(
    *,
    artifacts_dir: Path,
) -> dict[str, Any]:
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    refreshed_artifacts = {
        "manager_tool_surface_inventory": build_manager_tool_surface_inventory_artifact(),
        "manager_tool_choice_regression_wall": build_manager_tool_choice_regression_wall_artifact(),
        "non_fooddb_read_only_tool_loop_fake_smoke": build_non_fooddb_read_only_tool_loop_fake_smoke_artifact(),
        "non_fooddb_mutation_tool_guard_smoke": build_non_fooddb_mutation_tool_guard_smoke_artifact(),
    }
    for group_id, artifact in refreshed_artifacts.items():
        write_json_artifact(
            _artifact_path(artifacts_dir, REFRESHED_ARTIFACT_FILENAMES[group_id]),
            artifact,
        )

    product_pages_self_use_flow_gate = build_pl_ce_product_pages_self_use_flow_gate_artifact(
        build_product_pages_flow_inputs(
            path_overrides=_product_pages_flow_path_overrides(artifacts_dir)
        )
    )
    write_json_artifact(
        _artifact_path(
            artifacts_dir,
            REFRESHED_ARTIFACT_FILENAMES["product_pages_self_use_flow_gate"],
        ),
        product_pages_self_use_flow_gate,
    )

    browser_activation_evidence_gate = build_pl_ce_browser_activation_evidence_gate_artifact(
        _browser_gate_inputs(artifacts_dir)
    )
    write_json_artifact(
        _artifact_path(
            artifacts_dir,
            REFRESHED_ARTIFACT_FILENAMES["browser_activation_evidence_gate"],
        ),
        browser_activation_evidence_gate,
    )

    context_live_diagnostic_gate = build_context_live_diagnostic_gate_artifact(
        artifact_dir=artifacts_dir
    )
    write_json_artifact(
        _artifact_path(
            artifacts_dir,
            REFRESHED_ARTIFACT_FILENAMES["context_live_diagnostic_gate"],
        ),
        context_live_diagnostic_gate,
    )

    pre_live_evidence = build_local_web_candidate_gate_evidence(
        path_overrides=_local_gate_path_overrides(artifacts_dir)
    )
    write_json_artifact(
        _artifact_path(artifacts_dir, REFRESHED_ARTIFACT_FILENAMES["pre_live_evidence"]),
        pre_live_evidence,
    )

    pre_live_decision_pack = build_pre_live_self_use_decision_pack(pre_live_evidence)
    write_json_artifact(
        _artifact_path(
            artifacts_dir,
            REFRESHED_ARTIFACT_FILENAMES["pre_live_decision_pack"],
        ),
        pre_live_decision_pack,
    )

    local_web_candidate = build_local_web_self_use_candidate_v2(
        build_candidate_evidence_payload(pre_live_evidence, pre_live_decision_pack)
    )
    write_json_artifact(
        _artifact_path(artifacts_dir, REFRESHED_ARTIFACT_FILENAMES["local_web_candidate"]),
        local_web_candidate,
    )

    candidate_payload = dict(local_web_candidate.get("local_web_self_use_candidate_v2") or {})
    return {
        "artifact_type": "accurate_intake_local_web_self_use_candidate_v2_refresh_chain",
        "status": "pass" if candidate_payload.get("candidate_prepared") is True else "blocked",
        "artifacts_dir": str(artifacts_dir),
        "refreshed_artifacts": {
            group_id: str(_artifact_path(artifacts_dir, filename))
            for group_id, filename in REFRESHED_ARTIFACT_FILENAMES.items()
        },
        "browser_activation_status": browser_activation_evidence_gate.get("status"),
        "product_pages_self_use_flow_status": product_pages_self_use_flow_gate.get("status"),
        "context_live_diagnostic_gate_status": context_live_diagnostic_gate.get("status"),
        "pre_live_evidence_status": pre_live_evidence.get("_evidence_metadata", {}).get("status"),
        "pre_live_selected_option": pre_live_decision_pack.get("selected_option"),
        "candidate_prepared": candidate_payload.get("candidate_prepared") is True,
        "candidate_blockers": list(candidate_payload.get("blockers") or []),
        "live_llm_invoked": False,
        "web_tavily_used": False,
        "fooddb_evidence_used": False,
        "real_fooddb_pass_claimed": False,
        "product_readiness_claimed": False,
        "private_self_use_approved": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Refresh canonical local artifacts for the PLCE pre-live local web self-use gate."
    )
    parser.add_argument(
        "--artifacts-dir",
        default="artifacts",
        help="Directory containing canonical local artifact inputs and outputs.",
    )
    args = parser.parse_args(argv)

    summary = build_local_web_self_use_candidate_refresh_chain(
        artifacts_dir=Path(args.artifacts_dir)
    )
    print(json.dumps(summary, ensure_ascii=False))
    return 0 if summary["candidate_prepared"] is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
