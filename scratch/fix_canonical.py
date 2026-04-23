import os
from pathlib import Path

def fix_canonical_persistence_import():
    for root, _, files in os.walk("app"):
        for file in files:
            if not file.endswith(".py"): continue
            p = Path(root) / file
            content = p.read_text(encoding="utf-8")
            
            lines = content.split('\n')
            new_lines = []
            changed = False
            for line in lines:
                if "canonical_persistence" in line and ("app.intake.infrastructure" in line or "app.infrastructure" in line or "..infrastructure.canonical_persistence" in line or "...infrastructure.canonical_persistence" in line or "app.body.infrastructure" in line):
                    # Strip it down and point to shared
                    if "import" in line:
                        parts = line.split("import")
                        line = f"from app.shared.infra.canonical_persistence import{parts[1]}"
                        changed = True
                new_lines.append(line)
            
            if changed:
                p.write_text("\n".join(new_lines), encoding="utf-8")
                print(f"Fixed {p}")
                
    for root, _, files in os.walk("tests"):
        for file in files:
            if not file.endswith(".py"): continue
            p = Path(root) / file
            content = p.read_text(encoding="utf-8")
            if "canonical_persistence" in content:
                content = content.replace("app.infrastructure.canonical_persistence", "app.shared.infra.canonical_persistence")
                content = content.replace("app.intake.infrastructure.canonical_persistence", "app.shared.infra.canonical_persistence")
                p.write_text(content, encoding="utf-8")

fix_canonical_persistence_import()
