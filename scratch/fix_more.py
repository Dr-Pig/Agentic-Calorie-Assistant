import os
from pathlib import Path

def fix_more():
    for root, _, files in os.walk("app"):
        for file in files:
            if not file.endswith(".py"): continue
            p = Path(root) / file
            content = p.read_text(encoding="utf-8")
            
            changed = False
            
            # Fix manager_service
            if "from ...agent.manager" in content and "app\\runtime\\application" in str(p):
                content = content.replace("from ...agent.manager", "from ..agent.manager")
                changed = True
                
            # Fix test_context_memory_contract
            if "from app.runtime.infrastructure.agent" in content:
                content = content.replace("app.runtime.infrastructure.agent", "app.runtime.agent")
                changed = True
                
            # Fix shared.schemas to app.schemas
            if "app.shared.schemas" in content:
                content = content.replace("app.shared.schemas", "app.schemas")
                changed = True
            if "from ..schemas" in content and "shared\\infra\\canonical_persistence" in str(p):
                content = content.replace("from ..schemas", "from app.schemas")
                changed = True
                
            # Fix app.infrastructure
            if "app.infrastructure" in content:
                content = content.replace("app.infrastructure", "app.shared.infra")
                changed = True
            
            # Fix app.application
            if "from app.application" in content:
                content = content.replace("from app.application", "from app.runtime.application")
                changed = True

            if changed:
                p.write_text(content, encoding="utf-8")
                print(f"Fixed {p}")

    # Tests fixes
    for root, _, files in os.walk("tests"):
        for file in files:
            if not file.endswith(".py"): continue
            p = Path(root) / file
            content = p.read_text(encoding="utf-8")
            changed = False
            if "app.infrastructure" in content:
                content = content.replace("app.infrastructure", "app.shared.infra")
                changed = True
            if "app.application" in content:
                content = content.replace("app.application", "app.runtime.application")
                changed = True
            if "app.runtime.infrastructure.agent" in content:
                content = content.replace("app.runtime.infrastructure.agent", "app.runtime.agent")
                changed = True
            if changed:
                p.write_text(content, encoding="utf-8")
                print(f"Fixed {p}")

fix_more()
