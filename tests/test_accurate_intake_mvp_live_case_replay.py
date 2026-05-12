from __future__ import annotations

import copy
import json
from pathlib import Path

from scripts.build_accurate_intake_mvp_live_case_replay import (
    build_live_case_replay,
    write_live_case_replay,
)


MANIFEST_PATH = Path("docs/quality/accurate_intake_mvp_live_diagnostic_case_manifest.json")


def _manifest() -> dict[str, object]:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def _all_layers(manifest: dict[str, object]) -> list[str]:
    return [str(item["layer_id"]) for item in manifest["trace_layers"]]


def _trace_artifact(manifest: dict[str, object], *, layers: list[str] | None = None) -> dict[str, object]:
    trace_layers = layers or _all_layers(manifest)
    return {
        "artifact_type": "accurate_intake_mvp_live_diagnostic",
        "claim_scope": "test_trace_artifact",
        "cases": [
            {
                "case_id": case["case_id"],
                "trace_layers_present": trace_layers,
                "runner_inferred_semantics": False,
                "semantic_keyword_oracle_used": False,
                "raw_text_routing_used": False,
                "deterministic_semantic_override_used": False,
            }
            for case in manifest["cases"]
        ],
    }


def test_manifest_case_replay_accepts_all_cases_with_required_trace_layers() -> None:
    manifest = _manifest()
    replay = build_live_case_replay(manifest=manifest, trace_artifact=_trace_artifact(manifest))

    assert replay["artifact_type"] == "accurate_intake_mvp_live_case_replay"
    assert replay["manifest_id"] == "accurate_intake_mvp_live_diagnostic_18_case_manifest_v1"
    assert replay["live_invoked_by_replay"] is False
    assert replay["readiness_claimed"] is False
    assert replay["private_self_use_approved"] is False
    assert replay["semantic_keyword_oracle_used"] is False
    assert replay["summary"]["manifest_case_count"] == 18
    assert replay["summary"]["graded_case_count"] == 18
    assert replay["summary"]["failed_case_count"] == 0
    assert replay["summary"]["strict_trace_replay_passed"] is True
    assert replay["input_integrity"]["passed"] is True


def test_manifest_case_replay_blocks_missing_required_trace_layer() -> None:
    manifest = _manifest()
    layers = [layer for layer in _all_layers(manifest) if layer != "manager_pass_2_synthesis"]

    replay = build_live_case_replay(manifest=manifest, trace_artifact=_trace_artifact(manifest, layers=layers))

    assert replay["summary"]["strict_trace_replay_passed"] is False
    assert replay["summary"]["trace_layer_failure_count"] == 18
    assert replay["input_integrity"]["passed"] is False
    assert "case_trace_grade_failed" in replay["input_integrity"]["blockers"]
    assert all(
        "missing_layer:manager_pass_2_synthesis" in case["blockers"]
        for case in replay["cases"]
    )


def test_manifest_case_replay_blocks_missing_manifest_case() -> None:
    manifest = _manifest()
    source = _trace_artifact(manifest)
    source["cases"] = list(source["cases"][:-1])

    replay = build_live_case_replay(manifest=manifest, trace_artifact=source)

    assert replay["summary"]["missing_case_count"] == 1
    assert replay["summary"]["strict_trace_replay_passed"] is False
    assert replay["cases"][-1]["blockers"] == ["case_missing", *_missing_layer_blockers(manifest)]


def test_manifest_case_replay_blocks_semantic_keyword_oracle_shortcuts() -> None:
    manifest = _manifest()
    source = _trace_artifact(manifest)
    source["cases"][0]["semantic_keyword_oracle_used"] = True
    source["cases"][1]["raw_text_routing_used"] = True
    source["cases"][2]["deterministic_semantic_override_used"] = True

    replay = build_live_case_replay(manifest=manifest, trace_artifact=source)

    assert replay["summary"]["strict_trace_replay_passed"] is False
    assert replay["summary"]["semantic_oracle_failure_count"] == 3
    assert "forbidden_true_flag:semantic_keyword_oracle_used" in replay["cases"][0]["blockers"]
    assert "forbidden_true_flag:raw_text_routing_used" in replay["cases"][1]["blockers"]
    assert "forbidden_true_flag:deterministic_semantic_override_used" in replay["cases"][2]["blockers"]


def test_manifest_case_replay_does_not_depend_on_utterance_text_for_semantic_grade() -> None:
    manifest = _manifest()
    altered = copy.deepcopy(manifest)
    for case in altered["cases"]:
        case["turns"] = [{"turn": 1, "utterance_zh_tw": "semantic-sentinel-not-used"}]

    replay = build_live_case_replay(manifest=altered, trace_artifact=_trace_artifact(altered))

    assert replay["summary"]["strict_trace_replay_passed"] is True
    assert replay["input_integrity"]["passed"] is True


def test_manifest_case_replay_writer_creates_artifact(tmp_path: Path) -> None:
    manifest = _manifest()
    source = _trace_artifact(manifest)
    manifest_path = tmp_path / "manifest.json"
    source_path = tmp_path / "trace.json"
    output_path = tmp_path / "case-replay.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    source_path.write_text(json.dumps(source, ensure_ascii=False), encoding="utf-8")

    output = write_live_case_replay(
        manifest_path=manifest_path,
        trace_artifact_path=source_path,
        output_path=output_path,
    )

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert output == output_path
    assert payload["artifact_type"] == "accurate_intake_mvp_live_case_replay"
    assert payload["summary"]["strict_trace_replay_passed"] is True


def test_live_runbook_mentions_manifest_case_replay() -> None:
    runbook = Path("docs/quality/ACCURATE_INTAKE_MVP_LIVE_DIAGNOSTIC_RUNBOOK.md").read_text(
        encoding="utf-8-sig"
    )

    assert "build_accurate_intake_mvp_live_case_replay.py" in runbook


def _missing_layer_blockers(manifest: dict[str, object]) -> list[str]:
    return [f"missing_layer:{layer}" for layer in _all_layers(manifest)]
