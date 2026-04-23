import os
from pathlib import Path

for root, _, files in os.walk("app"):
    for file in files:
        if not file.endswith(".py"): continue
        p = Path(root) / file
        content = p.read_text(encoding="utf-8")
        changed = False
        
        if "app.runtime.application.context_normalizer" in content:
            content = content.replace("app.runtime.application.context_normalizer", "app.nutrition.application.context_normalizer")
            changed = True
        if "app.shared.infra.session_record_store" in content:
            content = content.replace("app.shared.infra.session_record_store", "app.memory.infrastructure.session_record_store")
            changed = True
        if "app.nutrition.infrastructure.infrastructure" in content:
            content = content.replace("app.nutrition.infrastructure.infrastructure", "app.nutrition.infrastructure")
            changed = True
            
        if changed:
            p.write_text(content, encoding="utf-8")
            print(f"Fixed {p}")

for root, _, files in os.walk("tests"):
    for file in files:
        if not file.endswith(".py"): continue
        p = Path(root) / file
        content = p.read_text(encoding="utf-8")
        changed = False
        if "app.runtime.application.context_normalizer" in content:
            content = content.replace("app.runtime.application.context_normalizer", "app.nutrition.application.context_normalizer")
            changed = True
        if "app.shared.infra.session_record_store" in content:
            content = content.replace("app.shared.infra.session_record_store", "app.memory.infrastructure.session_record_store")
            changed = True
        if "app.nutrition.application.evidence_assembly" in content:
            content = content.replace("app.nutrition.application.evidence_assembly", "app.nutrition.application.tool_dispatch") # Or whatever is correct
            changed = True
        if changed:
            p.write_text(content, encoding="utf-8")
            print(f"Fixed {p}")
