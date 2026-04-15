from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.audit_io_guard import load_json_audit_fixture
from scripts.check_official_text_surface_mojibake import _scan_path
from scripts.text_surface_guard import find_issues_in_json_payload


def test_json_fixture_guard_detects_corrupted_high_risk_fields() -> None:
    path = Path("docs/quality/benchmarks/example.json")
    payload = {
        "title": "正常標題",
        "utterance": "銝撠??",
        "state_pack_summary": {
            "pending_question": "不要掃這個 key"
        },
    }

    issues = find_issues_in_json_payload(path, payload)

    assert any(issue.reason == "fixture_text_corruption" for issue in issues)


def test_json_fixture_guard_ignores_clean_semantic_fields(tmp_path: Path) -> None:
    path = tmp_path / "clean_fixture.json"
    payload = {
        "title": "Rescue acceptance in natural language",
        "utterance": "好，就照這個方案做。",
        "pending_question": "你吃了哪些料？有沒有喝湯？",
        "note": "The repo does not yet define a canonical conversation_style_profile.",
    }
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    issues = _scan_path(path)

    assert issues == []


def test_python_surface_guard_detects_corrupted_line(tmp_path: Path) -> None:
    path = tmp_path / "runner.py"
    path.write_text('reply_text = "銝撠??"\n', encoding="utf-8")

    issues = _scan_path(path)

    assert any(issue.reason == "mojibake_pattern" for issue in issues)


def test_load_json_audit_fixture_rejects_corrupted_semantic_field(tmp_path: Path) -> None:
    path = tmp_path / "broken_fixture.json"
    payload = {
        "title": "normal title",
        "utterance": "銝撠??",
    }
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(SystemExit):
        load_json_audit_fixture(path=path, audit_name="test_fixture")
