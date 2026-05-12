from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.advanced_shadow_lab.product_lab_activation_wall_audit import (  # noqa: E402
    build_product_lab_activation_wall_audit,
)
from app.advanced_shadow_lab.product_lab_calibration_fixture_inputs import (  # noqa: E402
    build_product_lab_calibration_fixture_inputs,
)
from app.advanced_shadow_lab.product_lab_memory_record_closure_pack import (  # noqa: E402
    build_memory_record_closure_pack,
)
from app.advanced_shadow_lab.product_lab_memory_record_dogfood_summary import (  # noqa: E402
    build_memory_record_dogfood_summary,
)
from app.advanced_shadow_lab.product_lab_memory_record_holdout import (  # noqa: E402
    build_memory_record_holdout_report,
    build_memory_record_holdout_turns,
)
from app.advanced_shadow_lab.product_lab_memory_record_integrated_e2e import (  # noqa: E402
    run_memory_record_integrated_e2e_chain,
)
from app.advanced_shadow_lab.product_lab_memory_record_live_diagnostic import (  # noqa: E402
    run_memory_record_live_diagnostic,
)
from app.advanced_shadow_lab.product_lab_memory_record_readiness import (  # noqa: E402
    build_memory_record_readiness_report,
)
from app.advanced_shadow_lab.product_lab_memory_record_session import (  # noqa: E402
    run_advanced_product_lab_memory_record_session,
)
from app.advanced_shadow_lab.product_lab_simulated_scenario import (  # noqa: E402
    build_product_lab_simulated_turns,
)
from app.shared.infra.json_artifacts import write_json_artifact  # noqa: E402


class FakeClosureDiagnosticProvider:
    def readiness(self) -> dict[str, Any]:
        return {"provider": "fake-memory-record-closure-diagnostic", "configured": True}

    async def complete_with_trace(self, **_: Any) -> tuple[dict[str, Any], dict[str, Any]]:
        return {
            "diagnostic_notes": "The MemoryRecord product-lab closure chain is reviewable.",
            "risk_notes": "Lab diagnostic only; no mainline delivery or mutation.",
            "claim_scope": "diagnostic_only",
            "action_request": False,
            "delivery_request": False,
            "mutation_request": False,
            "reason_codes": ["memory_record_closure_pipeline"],
        }, {"stage": "memory_record_closure_pipeline", "provider": "fake"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the complete MemoryRecord advanced product-lab closure pipeline."
    )
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--session-id", default="advanced-product-lab-memory-closure")
    args = parser.parse_args(argv)

    outputs = _output_paths(args.output_root)
    summary = _build_summary(args.output_root, str(args.session_id))
    write_json_artifact(outputs["summary"], summary)
    readiness = build_memory_record_readiness_report(
        summary,
        source_summary_path=outputs["summary"],
    )
    write_json_artifact(outputs["readiness"], readiness)
    integrated = run_memory_record_integrated_e2e_chain(
        summary_artifact=summary,
        readiness_report=readiness,
        source_summary_path=outputs["summary"],
        source_readiness_path=outputs["readiness"],
    )
    write_json_artifact(outputs["integrated"], integrated)
    live = run_memory_record_live_diagnostic(
        integrated_e2e_artifact=integrated,
        provider=FakeClosureDiagnosticProvider(),
        provider_mode="fake_provider_contract_test",
        live_invoked=False,
        source_integrated_e2e_path=outputs["integrated"],
        output_path=outputs["live"],
    )
    holdout = _build_holdout(args.output_root, str(args.session_id))
    write_json_artifact(outputs["holdout"], holdout)
    closure = build_memory_record_closure_pack(
        summary_artifact=summary,
        readiness_report=readiness,
        integrated_e2e_artifact=integrated,
        live_diagnostic_artifact=live,
        holdout_report=holdout,
        source_summary_path=outputs["summary"],
        source_readiness_path=outputs["readiness"],
        source_integrated_e2e_path=outputs["integrated"],
        source_live_diagnostic_path=outputs["live"],
        source_holdout_path=outputs["holdout"],
    )
    write_json_artifact(outputs["closure"], closure)
    audit = build_product_lab_activation_wall_audit(
        closure_pack=closure,
        repo_root=ROOT,
        source_closure_pack_path=outputs["closure"],
    )
    write_json_artifact(outputs["activation_wall"], audit)
    print(
        json.dumps(
            {
                "status": audit["status"],
                "final_artifact": str(outputs["activation_wall"]),
                "blockers": audit["blockers"],
            },
            ensure_ascii=False,
        )
    )
    return 0 if audit["status"] == "pass" else 1


def _output_paths(output_root: Path) -> dict[str, Path]:
    return {
        "summary": output_root / "summary.json",
        "readiness": output_root / "readiness.json",
        "integrated": output_root / "integrated_e2e.json",
        "live": output_root / "live_diagnostic.json",
        "holdout": output_root / "holdout.json",
        "closure": output_root / "closure_pack.json",
        "activation_wall": output_root / "activation_wall.json",
    }


def _build_summary(output_root: Path, session_id: str) -> dict[str, Any]:
    session = run_advanced_product_lab_memory_record_session(
        artifact_root=output_root / "memory-session",
        session_id=session_id,
        fixture_inputs=build_product_lab_calibration_fixture_inputs(),
        turns=build_product_lab_simulated_turns(),
    )
    return build_memory_record_dogfood_summary(session)


def _build_holdout(output_root: Path, session_id: str) -> dict[str, Any]:
    session = run_advanced_product_lab_memory_record_session(
        artifact_root=output_root / "holdout-session",
        session_id=f"{session_id}-holdout",
        fixture_inputs=build_product_lab_calibration_fixture_inputs(),
        turns=[*build_product_lab_simulated_turns(), *build_memory_record_holdout_turns()],
    )
    return build_memory_record_holdout_report(session)


if __name__ == "__main__":
    raise SystemExit(main())
