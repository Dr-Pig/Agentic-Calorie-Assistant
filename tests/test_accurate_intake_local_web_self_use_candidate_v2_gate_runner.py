from __future__ import annotations

import ast
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _write(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _required_payloads() -> dict[str, dict[str, object]]:
    return {
        "phase_c_gate": {
            "artifact_schema_version": "1.0",
            "gate_id": "phase_c_same_truth_gate",
            "status": "pass",
        },
        "accurate_intake_mvp_gate": {
            "artifact_schema_version": "1.0",
            "gate_id": "accurate_intake_mvp_deterministic_v1",
            "status": "pass",
        },
        "browser_shell_smoke": {
            "artifact_schema_version": "1.0",
            "claim_scope": "local_browser_executed_shell_smoke_artifact",
            "status": "pass",
            "browser_executed": True,
        },
        "chat_history_reload_gate": {
            "artifact_schema_version": "1.0",
            "gate_id": "accurate_intake_chat_history_reload_gate_v1",
            "status": "pass",
        },
        "free_text_manual_target_gate": {
            "artifact_schema_version": "1.0",
            "gate_id": "accurate_intake_free_text_manual_target_gate",
            "status": "pass",
        },
        "dogfood_review_queue": {
            "artifact_schema_version": "1.0",
            "artifact_type": "accurate_intake_dogfood_review_queue",
            "status": "generated",
        },
        "local_dogfood_data_hygiene": {
            "artifact_schema_version": "1.0",
            "artifact_type": "accurate_intake_local_dogfood_data_hygiene",
            "status": "pass",
            "writes_performed": False,
            "import_allowed": False,
            "production_db_used": False,
            "fooddb_truth_updated": False,
        },
        "local_operator_data_hygiene_bundle": {
            "artifact_schema_version": "1.0",
            "artifact_type": "accurate_intake_local_operator_data_hygiene_bundle",
            "status": "local_operator_data_hygiene_ready",
            "writes_performed": False,
            "import_allowed": False,
            "production_db_used": False,
            "fooddb_truth_updated": False,
        },
        "pl_ce_local_review_decision_pack": {
            "artifact_schema_version": "1.0",
            "artifact_type": "accurate_intake_pl_ce_local_review_decision_pack",
            "status": "ready_for_human_pl_ce_review",
            "shared_contract_changed": False,
            "ready_for_live_diagnostic_decision": False,
            "ready_for_fdb_integration": False,
            "live_llm_invoked": False,
            "web_tavily_used": False,
            "real_fooddb_pass_claimed": False,
            "private_self_use_approved": False,
        },
        "context_live_diagnostic_case_matrix": {
            "artifact_schema_version": "1.0",
            "artifact_type": "accurate_intake_context_live_diagnostic_case_matrix",
            "status": "pass",
            "plan_only": True,
            "live_llm_invoked": False,
            "live_provider_invoked": False,
            "fooddb_used": False,
            "mutation_changed": False,
            "manager_context_packet_schema_changed": False,
            "summary": {"case_count": 11, "compound_cases": 1},
        },
    }


def _artifact_args(artifact_dir: Path, groups: tuple[str, ...]) -> list[str]:
    args: list[str] = []
    for group_id in groups:
        args.extend(["--artifact", f"{group_id}={artifact_dir / f'{group_id}.json'}"])
    return args


def test_local_web_self_use_candidate_v2_gate_runner_writes_outputs(
    tmp_path: Path,
    capsys,
) -> None:
    from scripts.run_accurate_intake_local_web_self_use_candidate_v2_gate import (
        DEFAULT_EVIDENCE_PATHS,
        main,
    )

    artifact_dir = tmp_path / "artifacts"
    for group_id, payload in _required_payloads().items():
        _write(artifact_dir / f"{group_id}.json", payload)
    pre_live_evidence_output = tmp_path / "pre_live_evidence.json"
    pre_live_output = tmp_path / "pre_live_decision_pack.json"
    candidate_output = tmp_path / "candidate.json"

    exit_code = main(
        [
            "--pre-live-evidence-output",
            str(pre_live_evidence_output),
            "--pre-live-output",
            str(pre_live_output),
            "--candidate-output",
            str(candidate_output),
            *_artifact_args(artifact_dir, tuple(DEFAULT_EVIDENCE_PATHS)),
        ]
    )
    printed = json.loads(capsys.readouterr().out)
    pre_live_evidence = json.loads(pre_live_evidence_output.read_text(encoding="utf-8"))
    pre_live_pack = json.loads(pre_live_output.read_text(encoding="utf-8"))
    candidate = json.loads(candidate_output.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert printed["pre_live_selected_option"] == "ready_for_human_limited_live_canary_decision"
    assert printed["candidate_prepared"] is True
    assert pre_live_evidence["_evidence_metadata"]["status"] == "complete"
    assert pre_live_evidence["_evidence_metadata"]["local_web_candidate_gate_blocked"] is False
    assert pre_live_pack["ready_for_pl_ce_local_review"] is True
    assert candidate["local_web_self_use_candidate_v2"]["candidate_prepared"] is True
    assert candidate["local_web_self_use_candidate_v2"]["private_self_use_approved"] is False


def test_local_web_self_use_candidate_v2_gate_runner_keeps_distinct_default_phase_c_path() -> None:
    from scripts.run_accurate_intake_local_web_self_use_candidate_v2_gate import DEFAULT_EVIDENCE_PATHS

    assert DEFAULT_EVIDENCE_PATHS["phase_c_gate"].name == "phase_c_gate.json"


def test_local_web_self_use_candidate_v2_gate_runner_derives_phase_c_identity_from_mvp_gate(
    tmp_path: Path,
) -> None:
    from scripts.run_accurate_intake_local_web_self_use_candidate_v2_gate import (
        DEFAULT_EVIDENCE_PATHS,
        build_local_web_candidate_gate_evidence,
    )

    mvp_gate = {
        "artifact_schema_version": "1.0",
        "gate_id": "accurate_intake_mvp_deterministic_v1",
        "claim_scope": "local_deterministic_mvp_gate",
        "status": "pass",
        "groups": [
            {"group_id": "ledger_truth_and_read_model", "status": "pass"},
        ],
    }
    mvp_path = tmp_path / "accurate_intake_mvp_gate.json"
    _write(mvp_path, mvp_gate)

    overrides = {
        group_id: tmp_path / f"missing_{group_id}.json"
        for group_id in DEFAULT_EVIDENCE_PATHS
    }
    overrides["phase_c_gate"] = tmp_path / "missing_phase_c_gate.json"
    overrides["accurate_intake_mvp_gate"] = mvp_path

    evidence = build_local_web_candidate_gate_evidence(path_overrides=overrides)

    assert evidence["_evidence_metadata"]["missing_evidence"] == [
        "browser_shell_smoke",
        "chat_history_reload_gate",
        "free_text_manual_target_gate",
        "dogfood_review_queue",
        "local_dogfood_data_hygiene",
        "local_operator_data_hygiene_bundle",
        "pl_ce_local_review_decision_pack",
        "context_live_diagnostic_case_matrix",
    ]
    assert evidence["phase_c_gate"]["artifact_type"] == "accurate_intake_phase_c_gate_from_mvp_gate"
    assert evidence["phase_c_gate"]["status"] == "pass"
    assert evidence["phase_c_gate"]["source_gate_id"] == "accurate_intake_mvp_deterministic_v1"


def test_local_web_self_use_candidate_v2_gate_runner_blocks_missing_artifact_without_autofix(
    tmp_path: Path,
    capsys,
) -> None:
    from scripts.run_accurate_intake_local_web_self_use_candidate_v2_gate import (
        DEFAULT_EVIDENCE_PATHS,
        main,
    )

    artifact_dir = tmp_path / "artifacts"
    payloads = _required_payloads()
    payloads.pop("pl_ce_local_review_decision_pack")
    for group_id, payload in payloads.items():
        _write(artifact_dir / f"{group_id}.json", payload)
    pre_live_evidence_output = tmp_path / "pre_live_evidence.json"
    pre_live_output = tmp_path / "pre_live_decision_pack.json"
    candidate_output = tmp_path / "candidate.json"

    exit_code = main(
        [
            "--pre-live-evidence-output",
            str(pre_live_evidence_output),
            "--pre-live-output",
            str(pre_live_output),
            "--candidate-output",
            str(candidate_output),
            *_artifact_args(artifact_dir, tuple(DEFAULT_EVIDENCE_PATHS)),
        ]
    )
    printed = json.loads(capsys.readouterr().out)
    pre_live_evidence = json.loads(pre_live_evidence_output.read_text(encoding="utf-8"))
    candidate = json.loads(candidate_output.read_text(encoding="utf-8"))

    assert exit_code == 1
    assert printed["evidence_status"] == "blocked_missing_evidence"
    assert printed["candidate_prepared"] is False
    assert printed["missing_evidence"] == ["pl_ce_local_review_decision_pack"]
    assert pre_live_evidence["pl_ce_local_review_decision_pack"]["autofix_attempted"] is False
    assert "missing evidence: pl_ce_local_review_decision_pack" in candidate["local_web_self_use_candidate_v2"]["blockers"]
    assert "local web candidate gate evidence blocked" in candidate["local_web_self_use_candidate_v2"]["blockers"]


def test_local_web_self_use_candidate_v2_gate_runner_blocks_missing_context_live_matrix(
    tmp_path: Path,
    capsys,
) -> None:
    from scripts.run_accurate_intake_local_web_self_use_candidate_v2_gate import (
        DEFAULT_EVIDENCE_PATHS,
        main,
    )

    artifact_dir = tmp_path / "artifacts"
    payloads = _required_payloads()
    payloads.pop("context_live_diagnostic_case_matrix")
    for group_id, payload in payloads.items():
        _write(artifact_dir / f"{group_id}.json", payload)
    candidate_output = tmp_path / "candidate.json"

    exit_code = main(
        [
            "--pre-live-evidence-output",
            str(tmp_path / "pre_live_evidence.json"),
            "--pre-live-output",
            str(tmp_path / "pre_live_decision_pack.json"),
            "--candidate-output",
            str(candidate_output),
            *_artifact_args(artifact_dir, tuple(DEFAULT_EVIDENCE_PATHS)),
        ]
    )
    printed = json.loads(capsys.readouterr().out)
    candidate = json.loads(candidate_output.read_text(encoding="utf-8"))

    assert exit_code == 1
    assert printed["candidate_prepared"] is False
    assert printed["missing_evidence"] == ["context_live_diagnostic_case_matrix"]
    assert (
        "missing evidence: context_live_diagnostic_case_matrix"
        in candidate["local_web_self_use_candidate_v2"]["blockers"]
    )


def test_local_web_self_use_candidate_v2_gate_runner_blocks_pl_ce_overclaim(
    tmp_path: Path,
    capsys,
) -> None:
    from scripts.run_accurate_intake_local_web_self_use_candidate_v2_gate import (
        DEFAULT_EVIDENCE_PATHS,
        main,
    )

    artifact_dir = tmp_path / "artifacts"
    payloads = _required_payloads()
    payloads["pl_ce_local_review_decision_pack"]["ready_for_live_diagnostic_decision"] = True
    for group_id, payload in payloads.items():
        _write(artifact_dir / f"{group_id}.json", payload)
    candidate_output = tmp_path / "candidate.json"

    exit_code = main(
        [
            "--pre-live-evidence-output",
            str(tmp_path / "pre_live_evidence.json"),
            "--pre-live-output",
            str(tmp_path / "pre_live_decision_pack.json"),
            "--candidate-output",
            str(candidate_output),
            *_artifact_args(artifact_dir, tuple(DEFAULT_EVIDENCE_PATHS)),
        ]
    )
    printed = json.loads(capsys.readouterr().out)
    candidate = json.loads(candidate_output.read_text(encoding="utf-8"))

    assert exit_code == 1
    assert printed["candidate_prepared"] is False
    assert "PL+CE local review overclaim" in candidate["local_web_self_use_candidate_v2"]["blockers"]
    assert candidate["local_web_self_use_candidate_v2"]["private_self_use_approved"] is False


def test_local_web_self_use_candidate_v2_gate_runner_blocks_status_only_artifacts(
    tmp_path: Path,
    capsys,
) -> None:
    from scripts.run_accurate_intake_local_web_self_use_candidate_v2_gate import (
        DEFAULT_EVIDENCE_PATHS,
        main,
    )

    artifact_dir = tmp_path / "artifacts"
    payloads = _required_payloads()
    payloads["phase_c_gate"] = {"status": "pass"}
    for group_id, payload in payloads.items():
        _write(artifact_dir / f"{group_id}.json", payload)
    candidate_output = tmp_path / "candidate.json"
    pre_live_evidence_output = tmp_path / "pre_live_evidence.json"

    exit_code = main(
        [
            "--pre-live-evidence-output",
            str(pre_live_evidence_output),
            "--pre-live-output",
            str(tmp_path / "pre_live_decision_pack.json"),
            "--candidate-output",
            str(candidate_output),
            *_artifact_args(artifact_dir, tuple(DEFAULT_EVIDENCE_PATHS)),
        ]
    )
    printed = json.loads(capsys.readouterr().out)
    pre_live_evidence = json.loads(pre_live_evidence_output.read_text(encoding="utf-8"))
    candidate = json.loads(candidate_output.read_text(encoding="utf-8"))

    assert exit_code == 1
    assert printed["evidence_status"] == "blocked_invalid_evidence"
    assert pre_live_evidence["_evidence_metadata"]["invalid_evidence"] == ["phase_c_gate"]
    assert "phase_c_gate_artifact_schema_version_missing" in pre_live_evidence["_evidence_metadata"]["blockers"]
    assert candidate["local_web_self_use_candidate_v2"]["candidate_prepared"] is False
    assert "local web candidate gate evidence blocked" in candidate["local_web_self_use_candidate_v2"]["blockers"]


def test_local_web_self_use_candidate_v2_gate_runner_rejects_wrong_phase_c_artifact_identity(
    tmp_path: Path,
    capsys,
) -> None:
    from scripts.run_accurate_intake_local_web_self_use_candidate_v2_gate import (
        DEFAULT_EVIDENCE_PATHS,
        main,
    )

    artifact_dir = tmp_path / "artifacts"
    payloads = _required_payloads()
    payloads["phase_c_gate"] = {
        "artifact_schema_version": "1.0",
        "gate_id": "accurate_intake_mvp_deterministic_v1",
        "claim_scope": "local_deterministic_mvp_gate",
        "status": "pass",
    }
    for group_id, payload in payloads.items():
        _write(artifact_dir / f"{group_id}.json", payload)
    pre_live_evidence_output = tmp_path / "pre_live_evidence.json"

    exit_code = main(
        [
            "--pre-live-evidence-output",
            str(pre_live_evidence_output),
            "--pre-live-output",
            str(tmp_path / "pre_live_decision_pack.json"),
            "--candidate-output",
            str(tmp_path / "candidate.json"),
            *_artifact_args(artifact_dir, tuple(DEFAULT_EVIDENCE_PATHS)),
        ]
    )
    printed = json.loads(capsys.readouterr().out)
    pre_live_evidence = json.loads(pre_live_evidence_output.read_text(encoding="utf-8"))

    assert exit_code == 1
    assert printed["evidence_status"] == "blocked_invalid_evidence"
    assert "phase_c_gate_artifact_identity_mismatch" in pre_live_evidence["_evidence_metadata"]["blockers"]


def test_local_web_self_use_candidate_v2_gate_runner_blocks_local_operator_overclaims(
    tmp_path: Path,
    capsys,
) -> None:
    from scripts.run_accurate_intake_local_web_self_use_candidate_v2_gate import (
        DEFAULT_EVIDENCE_PATHS,
        main,
    )

    artifact_dir = tmp_path / "artifacts"
    payloads = _required_payloads()
    payloads["local_operator_data_hygiene_bundle"]["production_db_touched"] = True
    for group_id, payload in payloads.items():
        _write(artifact_dir / f"{group_id}.json", payload)
    candidate_output = tmp_path / "candidate.json"

    exit_code = main(
        [
            "--pre-live-evidence-output",
            str(tmp_path / "pre_live_evidence.json"),
            "--pre-live-output",
            str(tmp_path / "pre_live_decision_pack.json"),
            "--candidate-output",
            str(candidate_output),
            *_artifact_args(artifact_dir, tuple(DEFAULT_EVIDENCE_PATHS)),
        ]
    )
    printed = json.loads(capsys.readouterr().out)
    candidate = json.loads(candidate_output.read_text(encoding="utf-8"))

    assert exit_code == 1
    assert printed["candidate_prepared"] is False
    assert "production DB touched" in candidate["local_web_self_use_candidate_v2"]["blockers"]
    assert (
        "pre-live blocker: local_operator_data_hygiene_bundle_production_db_touched"
        in candidate["local_web_self_use_candidate_v2"]["blockers"]
    )


def test_local_web_self_use_candidate_v2_gate_runner_rejects_bad_artifact_override_with_argparse_error(
    capsys,
) -> None:
    from scripts.run_accurate_intake_local_web_self_use_candidate_v2_gate import main

    with pytest.raises(SystemExit) as missing_equals:
        main(["--artifact", "not_a_pair"])
    first_error = capsys.readouterr().err

    with pytest.raises(SystemExit) as unknown_group:
        main(["--artifact", "unknown_group=artifact.json"])
    second_error = capsys.readouterr().err

    assert missing_equals.value.code == 2
    assert unknown_group.value.code == 2
    assert "--artifact must be group_id=path" in first_error
    assert "Unknown local web candidate evidence group" in second_error


def test_local_web_self_use_candidate_v2_gate_runner_stays_out_of_live_fooddb_and_websearch_boundaries() -> None:
    source = Path("scripts/run_accurate_intake_local_web_self_use_candidate_v2_gate.py").read_text(
        encoding="utf-8"
    )
    tree = ast.parse(source)
    imported_modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_modules.add(node.module)

    for fragment in (
        "NutritionEvidenceStorePort",
        "FoodEvidenceRecord",
        "PacketReadyAnchor",
        "TavilyClient",
        "BuilderSpaceAdapter",
        "builderspace_adapter",
        "Food Evidence promotion policy",
    ):
        assert fragment not in source
    for forbidden_import in (
        "requests",
        "httpx",
        "urllib",
        "openai",
        "app.providers",
    ):
        assert forbidden_import not in imported_modules
