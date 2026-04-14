from __future__ import annotations

from pathlib import Path

from scripts.check_user_facing_mojibake import find_issues_in_text


def test_guard_detects_private_use_and_replacement_characters() -> None:
    path = Path("app/application/example.py")
    text = 'reply_text = "正常\uFFFD字元"\nlabel = "含有私用區字元\uE000"\n'

    issues = find_issues_in_text(path, text)

    reasons = {issue.reason for issue in issues}
    assert "replacement_character" in reasons
    assert "private_use_character" in reasons


def test_guard_detects_common_mojibake_shard_cluster() -> None:
    path = Path("app/application/example.py")
    text = 'reply_text = "銝 嚗 憭 蝛"\n'

    issues = find_issues_in_text(path, text)

    assert any(issue.reason == "mojibake_shard_cluster" for issue in issues)


def test_guard_ignores_normal_chinese_copy() -> None:
    path = Path("app/application/example.py")
    text = 'reply_text = "我建議你用 3 天攤回來，每天大約少 150 kcal。"\n'

    issues = find_issues_in_text(path, text)

    assert issues == []
