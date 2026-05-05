from __future__ import annotations

from pathlib import Path


STATIC_PRODUCT_PAGES = [
    Path("static/accurate-intake-chat.html"),
    Path("static/accurate-intake-today.html"),
    Path("static/accurate-intake-body.html"),
]

SCRIPT_FIXTURE_FILES = [
    Path("scripts/run_accurate_intake_product_pages_browser_smoke.py"),
    Path("scripts/run_accurate_intake_browser_shell_smoke.py"),
]

MOJIBAKE_MARKERS = [
    "\ufffd",
    "銝",
    "蝝",
    "嚗",
    "撠",
    "瘝",
    "隞",
    "閮",
    "擗",
    "蝷",
]


EXPECTED_PAGE_COPY = {
    Path("static/accurate-intake-chat.html"): [
        "像 LINE 一樣輸入和回看飲食對話",
        "早餐吃茶葉蛋和拿鐵",
        "送出",
        "這一天還沒有聊天紀錄。",
        "處理中...",
        "目前沒有可顯示的助理回覆。",
        "送出失敗：",
    ],
    Path("static/accurate-intake-today.html"): [
        "每天一頁看熱量目標、已吃、剩餘和當日餐點",
        "切換日期就看那一天的紀錄",
    ],
    Path("static/accurate-intake-body.html"): [
        "先把體重、目標、活動量和每日熱量目標整理清楚",
        "這頁只顯示已保存的計畫與紀錄",
        "紀錄當天量到的體重，之後可以回看趨勢。",
        "調整身體資料、活動量與每週目標",
    ],
}


def _read_utf8(path: Path) -> str:
    data = path.read_bytes()
    return data.decode("utf-8")


def test_static_product_pages_decode_as_utf8_without_mojibake_markers() -> None:
    for path in STATIC_PRODUCT_PAGES:
        text = _read_utf8(path)
        assert "<meta charset=\"utf-8\"" in text
        for marker in MOJIBAKE_MARKERS:
            assert marker not in text, f"{path} contains mojibake marker {marker!r}"


def test_static_product_pages_keep_required_cjk_user_facing_copy() -> None:
    for path, snippets in EXPECTED_PAGE_COPY.items():
        text = _read_utf8(path)
        for snippet in snippets:
            assert snippet in text, f"{path} missing required CJK copy {snippet!r}"


def test_browser_smoke_default_cjk_fixture_copy_is_not_mojibake() -> None:
    for path in SCRIPT_FIXTURE_FILES:
        text = _read_utf8(path)
        assert 'DEFAULT_CJK_MESSAGE = "早餐吃茶葉蛋和拿鐵"' in text
        for marker in MOJIBAKE_MARKERS:
            assert marker not in text, f"{path} contains mojibake marker {marker!r}"
