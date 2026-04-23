import os
from pathlib import Path
import re

def aggressive_replace():
    for d in ["app", "tests", "scripts"]:
        for root, _, files in os.walk(d):
            for file in files:
                if not file.endswith(".py"): continue
                p = Path(root) / file
                content = p.read_text(encoding="utf-8")
                changed = False
                
                # test_canonical_persistence
                if "app.shared.infra.meal_log_persistence" in content:
                    content = content.replace("app.shared.infra.meal_log_persistence", "app.intake.infrastructure.meal_log_persistence")
                    changed = True
                
                # nutrition_resolution_normalizer
                if "app.runtime.agent.nutrition_resolution_normalizer" in content:
                    content = content.replace("app.runtime.agent.nutrition_resolution_normalizer", "app.nutrition.agent.resolution_normalizer")
                    changed = True
                    
                # app.runtime.infrastructure.agent -> app.runtime.agent
                if "app.runtime.infrastructure.agent" in content:
                    content = content.replace("app.runtime.infrastructure.agent", "app.runtime.agent")
                    changed = True
                    
                # app.application.context_assembly -> app.runtime.application.context_assembly or state_resolver
                if "app.application.context_assembly" in content:
                    content = content.replace("app.application.context_assembly", "app.runtime.application.state_resolver")
                    changed = True
                    
                # _build_report
                if "run_v2_bundle2_live_eval" in content and "_build_report" in content:
                    pass # Let's see if we can just fix the import in test_v2_bundle2_live_eval_runner

                if changed:
                    p.write_text(content, encoding="utf-8")
                    print(f"Fixed {p}")

aggressive_replace()
