import os
from pathlib import Path
import re

def fix_all():
    for root, _, files in os.walk("app"):
        for file in files:
            if not file.endswith(".py"): continue
            p = Path(root) / file
            content = p.read_text(encoding="utf-8")
            
            # Revert the wrong "app.shared.infra" to "..infrastructure"
            if "from app.shared.infra." in content:
                # Except for database, env, logging which ARE in app.shared.infra
                lines = content.split('\n')
                new_lines = []
                changed = False
                for line in lines:
                    if "from app.shared.infra." in line:
                        target = line.split("from app.shared.infra.")[1].split()[0]
                        if target not in ["database", "env", "logging"]:
                            line = line.replace("from app.shared.infra.", "from ..infrastructure.")
                            changed = True
                    new_lines.append(line)
                
                if changed:
                    p.write_text("\n".join(new_lines), encoding="utf-8")
                    print(f"Fixed {p}")

fix_all()
