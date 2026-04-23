from __future__ import annotations

from pathlib import Path

from scripts.check_user_facing_mojibake import find_issues_in_text


def test_guard_detects_private_use_and_replacement_characters() -> None:
    path = Path("app/intake/application/example.py")
    text = 'reply_text = "bad \uFFFD text"\nlabel = "broken\uE000"\n'

    issues = find_issues_in_text(path, text)

    reasons = {issue.reason for issue in issues}
    assert "replacement_character" in reasons
    assert "private_use_character" in reasons


def test_guard_detects_mojibake_pattern() -> None:
    path = Path("app/intake/application/example.py")
    text = 'reply_text = "銝撠??"\n'

    issues = find_issues_in_text(path, text)

    assert any(issue.reason == "mojibake_pattern" for issue in issues)


def test_guard_ignores_normal_chinese_copy() -> None:
    path = Path("app/intake/application/example.py")
    text = 'reply_text = "我先用 3 天幫你慢慢攤回來，每天大約少 150 kcal。"\n'

    issues = find_issues_in_text(path, text)

    assert issues == []
