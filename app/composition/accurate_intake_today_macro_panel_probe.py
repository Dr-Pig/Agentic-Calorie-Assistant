from __future__ import annotations

import json
import subprocess
from pathlib import Path


TODAY_PAGE = Path("static/accurate-intake-today.html")


def extract_function_source(html: str, function_name: str) -> str:
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


def run_render_macro_panel(
    payload: dict[str, object],
    *,
    html_override: str | None = None,
) -> dict[str, object]:
    html = html_override if html_override is not None else TODAY_PAGE.read_text(encoding="utf-8")
    function_source = extract_function_source(html, "renderMacroPanel")
    payload_json = json.dumps(payload, ensure_ascii=False)
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
  macro_panel_hidden: el("macro-panel").hidden,
  macro_state: el("macro-panel").dataset.macroState,
  macro_grid_hidden: el("macro-grid").hidden,
  macro_guard_reason_hidden: el("macro-guard-reason").hidden,
  macro_guard_reason_text: el("macro-guard-reason").textContent,
  protein_text: el("protein-g").textContent,
  carbs_text: el("carbs-g").textContent,
  fat_text: el("fat-g").textContent,
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


def validate_runtime_macro_case(
    *,
    payload: dict[str, object],
    runtime_case: dict[str, object],
) -> list[str]:
    blockers: list[str] = []
    expected_protein = str(payload.get("consumed_protein"))
    expected_carbs = str(payload.get("consumed_carbs"))
    expected_fat = str(payload.get("consumed_fat"))
    if payload.get("show_macro") is True:
        if runtime_case["macro_state"] != "visible":
            blockers.append("today_macro_runtime_panel.visible_case.macro_state_not_visible")
        if runtime_case["macro_grid_hidden"] is not False:
            blockers.append("today_macro_runtime_panel.visible_case.macro_grid_hidden")
        if runtime_case["macro_guard_reason_hidden"] is not True:
            blockers.append("today_macro_runtime_panel.visible_case.guard_reason_visible")
        if runtime_case["protein_text"] != expected_protein:
            blockers.append("today_macro_runtime_panel.visible_case.protein_text_mismatch")
        if runtime_case["carbs_text"] != expected_carbs:
            blockers.append("today_macro_runtime_panel.visible_case.carbs_text_mismatch")
        if runtime_case["fat_text"] != expected_fat:
            blockers.append("today_macro_runtime_panel.visible_case.fat_text_mismatch")
        return blockers

    if payload.get("show_macro") is False:
        if runtime_case["macro_state"] != "guarded":
            blockers.append("today_macro_runtime_panel.guarded_case.macro_state_not_guarded")
        if runtime_case["macro_grid_hidden"] is not True:
            blockers.append("today_macro_runtime_panel.guarded_case.macro_grid_visible")
        if runtime_case["macro_guard_reason_hidden"] is not False:
            blockers.append("today_macro_runtime_panel.guarded_case.guard_reason_hidden")
        if runtime_case["macro_guard_reason_text"] != str(payload.get("macro_guard_reason")):
            blockers.append("today_macro_runtime_panel.guarded_case.guard_reason_text_mismatch")
        if runtime_case["protein_text"] != "--":
            blockers.append("today_macro_runtime_panel.guarded_case.protein_text_leaked")
        if runtime_case["carbs_text"] != "--":
            blockers.append("today_macro_runtime_panel.guarded_case.carbs_text_leaked")
        if runtime_case["fat_text"] != "--":
            blockers.append("today_macro_runtime_panel.guarded_case.fat_text_leaked")
        if not payload.get("macro_guard_reason"):
            blockers.append("current_budget_payload.guarded_case.missing_macro_guard_reason")
        return blockers

    blockers.append("current_budget_payload.show_macro_not_boolean")
    return blockers


__all__ = [
    "extract_function_source",
    "run_render_macro_panel",
    "validate_runtime_macro_case",
]
