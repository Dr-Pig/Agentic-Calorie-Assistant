from __future__ import annotations

import subprocess
from pathlib import Path

from scripts import run_codex_exec_with_prompt


def test_wrapper_accepts_planner_mode_and_passes_prompt_to_codex(tmp_path: Path, monkeypatch, capsys) -> None:
    prompt_file = tmp_path / "prompt.md"
    prompt_file.write_text("planner prompt", encoding="utf-8")

    recorded: dict[str, object] = {}

    def fake_run(cmd, *, input, text, capture_output, encoding, errors):
        recorded["cmd"] = cmd
        recorded["input"] = input
        recorded["text"] = text
        recorded["capture_output"] = capture_output
        recorded["encoding"] = encoding
        recorded["errors"] = errors
        return subprocess.CompletedProcess(cmd, 0, stdout="ok", stderr="")

    monkeypatch.setattr(run_codex_exec_with_prompt, "resolve_codex_bin", lambda: "codex")
    monkeypatch.setattr(run_codex_exec_with_prompt.subprocess, "run", fake_run)

    exit_code = run_codex_exec_with_prompt.main(
        [
            "--prompt-file",
            str(prompt_file),
            "--cd",
            str(tmp_path),
            "--mode",
            "planner",
        ]
    )

    assert exit_code == 0
    assert recorded["cmd"] == [
        "codex",
        "exec",
        "-",
        "--sandbox",
        "workspace-write",
        "-C",
        str(tmp_path),
    ]
    assert recorded["input"] == "planner prompt"
    assert capsys.readouterr().out == "ok"


def test_wrapper_accepts_verifier_mode(tmp_path: Path, monkeypatch) -> None:
    prompt_file = tmp_path / "prompt.md"
    prompt_file.write_text("verifier prompt", encoding="utf-8")

    monkeypatch.setattr(run_codex_exec_with_prompt, "resolve_codex_bin", lambda: "codex")
    monkeypatch.setattr(
        run_codex_exec_with_prompt.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 0, stdout="", stderr=""),
    )

    exit_code = run_codex_exec_with_prompt.main(
        [
            "--prompt-file",
            str(prompt_file),
            "--cd",
            str(tmp_path),
            "--mode",
            "verifier",
        ]
    )

    assert exit_code == 0
