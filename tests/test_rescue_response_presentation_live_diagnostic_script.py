from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys


def test_response_presentation_live_diagnostic_script_fake_mode(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    output = tmp_path / "rescue_response_presentation_provider_diagnostic.json"

    result = subprocess.run(
        [
            sys.executable,
            str(root / "scripts" / "run_rescue_response_presentation_live_diagnostic.py"),
            "--provider-mode",
            "fake",
            "--output",
            str(output),
        ],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    artifact = json.loads(output.read_text(encoding="utf-8"))
    assert artifact["artifact_type"] == "rescue_response_presentation_provider_diagnostic"
    assert artifact["status"] == "pass"
    assert artifact["provider_mode"] == "fake"
    assert artifact["provider_called"] is True
    assert artifact["live_llm_invoked"] is False
    assert artifact["validation"]["status"] == "pass"
    assert artifact["response_card_packet"]["status"] == "pass"
    assert artifact["mainline_activation_enabled"] is False
