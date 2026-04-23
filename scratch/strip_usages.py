import os
import re

for file in ["app/intake/application/decision_payload.py", "app/intake/application/state_transition.py", "app/nutrition/application/nutrition_payload.py", "app/nutrition/application/tool_dispatch.py"]:
    if os.path.exists(file):
        content = open(file, "r", encoding="utf-8").read()
        # Find any references and remove them
        content = re.sub(r"planner_result[^,]+,", "", content)
        content = re.sub(r"intent\s*=\s*planner_result.*?,\n", "", content)
        open(file, "w", encoding="utf-8").write(content)
        
print("Stripped usages.")
