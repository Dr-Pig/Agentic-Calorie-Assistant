import os
from pathlib import Path

def fix_domain_infra_imports():
    for root, _, files in os.walk("app"):
        for file in files:
            if not file.endswith(".py"): continue
            p = Path(root) / file
            content = p.read_text(encoding="utf-8")
            
            # Find and fix cases where app.shared.infra was wrongly inserted instead of ..infrastructure
            if "from app.shared.infra." in content:
                print(f"Checking {p}...")
                if "current_budget_read_model" in content and "app\\budget\\application" in str(p):
                    content = content.replace("from app.shared.infra.current_budget_read_model", "from ..infrastructure.current_budget_read_model")
                elif "preference_profile_persistence" in content and "app\\recommendation\\application" in str(p):
                    content = content.replace("from app.shared.infra.preference_profile_persistence", "from ..infrastructure.preference_profile_persistence")
                
                p.write_text(content, encoding="utf-8")

fix_domain_infra_imports()
