from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "create_benchmark_artifact.py"


def test_create_benchmark_artifact_scaffolds_official_pack(tmp_path: Path) -> None:
    output_rel = Path("artifacts") / "test-generated" / "generated_official_pack.json"
    output_path = ROOT / output_rel
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        completed = subprocess.run(
            [
                sys.executable,
                str(SCRIPT_PATH),
                "--template",
                "official_pack",
                "--output",
                str(output_rel),
                "--replace",
                "__PACK_ID__=retrieval_candidate_selection_golden_v1",
                "--replace",
                "__APPROVAL_STATUS__=agent_promoted_v1",
                "--replace",
                "__SUITE_ARCHETYPE__=capability_service",
                "--replace",
                "__APPROVAL_MODE__=agent_allowed",
                "--replace",
                "__TRUTH_SOURCE__=canonical_spec_derivation",
                "--replace",
                "__PRIMARY_ORACLE_FIELD__=expected_service_outcome",
                "--replace",
                "__CASE_ID__=retrieval_candidate_selection_official_001",
                "--replace",
                "__SUITE_ID__=retrieval_candidate_selection_golden_v1",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

        assert completed.returncode == 0, completed.stderr
        payload = json.loads(output_path.read_text(encoding="utf-8"))
        assert payload["pack_mode"] == "official_canonical"
        assert payload["approval_mode"] == "agent_allowed"
        assert payload["truth_source"] == "canonical_spec_derivation"
    finally:
        if output_path.exists():
            output_path.unlink()
