import os
from pathlib import Path

def fix_base_import():
    for root, _, files in os.walk("app"):
        for file in files:
            if file == "models.py" and root != "app":
                p = Path(root) / file
                content = p.read_text(encoding="utf-8")
                
                # Replace bad relative infrastructure.models import with shared database import
                lines = content.split('\n')
                new_lines = []
                changed = False
                for line in lines:
                    if "from app.models import Base" in line:
                        # Change to point directly to shared.infra to avoid circular import
                        line = "from app.shared.infra.models import Base, utcnow"
                        changed = True
                    new_lines.append(line)
                
                if changed:
                    p.write_text("\n".join(new_lines), encoding="utf-8")
                    print(f"Fixed {p}")

fix_base_import()
