from __future__ import annotations

import json
import subprocess
from pathlib import Path


TODAY_PAGE = Path("static/accurate-intake-today.html")


def _extract_function_source(html: str, function_name: str) -> str:
    marker = f"function {function_name}("
    start = html.find(marker)
    if start == -1:
        raise AssertionError(f"Could not find {function_name} in Today page")
    brace_start = html.find("{", start)
    if brace_start == -1:
        raise AssertionError(f"Could not find opening brace for {function_name}")

    depth = 0
    index = brace_start
    while index < len(html):
        char = html[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return html[start : index + 1]
        index += 1
    raise AssertionError(f"Could not find closing brace for {function_name}")


def _run_render_macro_panel(payload: dict[str, object]) -> dict[str, object]:
    html = TODAY_PAGE.read_text(encoding="utf-8")
    function_source = _extract_function_source(html, "renderMacroPanel")
    payload_json = json.dumps(payload)
    node_script = f"""
const elements = new Map();
function makeElement(id) {{
  return {{
    id,
    textContent: "",
    hidden: false,
    dataset: {{}},
  }};
}}
const document = {{
  getElementById(id) {{
    if (!elements.has(id)) {{
      elements.set(id, makeElement(id));
    }}
    return elements.get(id);
  }},
}};
function el(id) {{
  return document.getElementById(id);
}}
function writeText(id, value) {{
  el(id).textContent = value == null ? "--" : String(value);
}}
{function_source}
const payload = {payload_json};
renderMacroPanel(payload);
const result = {{
  macroPanelHidden: el("macro-panel").hidden,
  macroState: el("macro-panel").dataset.macroState,
  macroGridHidden: el("macro-grid").hidden,
  macroGuardReasonHidden: el("macro-guard-reason").hidden,
  macroGuardReasonText: el("macro-guard-reason").textContent,
  proteinText: el("protein-g").textContent,
  carbsText: el("carbs-g").textContent,
  fatText: el("fat-g").textContent,
}};
process.stdout.write(JSON.stringify(result));
"""
    completed = subprocess.run(
        ["node", "-e", node_script],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout)


def test_render_macro_panel_surfaces_backend_macro_values_only_when_visible() -> None:
    result = _run_render_macro_panel(
        {
            "show_macro": True,
            "macro_guard_reason": "backend hidden reason should not show here",
            "consumed_protein": 31,
            "consumed_carbs": 44,
            "consumed_fat": 12,
        }
    )

    assert result["macroPanelHidden"] is False
    assert result["macroState"] == "visible"
    assert result["macroGridHidden"] is False
    assert result["macroGuardReasonHidden"] is True
    assert result["proteinText"] == "31"
    assert result["carbsText"] == "44"
    assert result["fatText"] == "12"


def test_render_macro_panel_hides_backend_macro_values_when_guarded() -> None:
    result = _run_render_macro_panel(
        {
            "show_macro": False,
            "macro_guard_reason": "Backend says macros are insufficient today.",
            "consumed_protein": 31,
            "consumed_carbs": 44,
            "consumed_fat": 12,
        }
    )

    assert result["macroPanelHidden"] is False
    assert result["macroState"] == "guarded"
    assert result["macroGridHidden"] is True
    assert result["macroGuardReasonHidden"] is False
    assert result["macroGuardReasonText"] == "Backend says macros are insufficient today."
    assert result["proteinText"] != "31"
    assert result["carbsText"] != "44"
    assert result["fatText"] != "12"
