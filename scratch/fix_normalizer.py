import os
from pathlib import Path

def fix_normalizer():
    for d in ["app", "tests", "scripts"]:
        for root, _, files in os.walk(d):
            for file in files:
                if not file.endswith(".py"): continue
                p = Path(root) / file
                try:
                    content = p.read_text(encoding="utf-8")
                except: continue
                
                changed = False
                if "app.runtime.application.context_normalizer" in content:
                    content = content.replace("app.runtime.application.context_normalizer", "app.nutrition.application.context_normalizer")
                    changed = True
                if "app.application.context_normalizer" in content:
                    content = content.replace("app.application.context_normalizer", "app.nutrition.application.context_normalizer")
                    changed = True
                    
                if changed:
                    p.write_text(content, encoding="utf-8")
                    print(f"Fixed {p}")

fix_normalizer()
