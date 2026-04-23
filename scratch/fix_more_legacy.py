import os
import re

def fix():
    # 1. decision_payload.py
    f1 = "app/intake/application/decision_payload.py"
    if os.path.exists(f1):
        c = open(f1, encoding="utf-8").read()
        c = re.sub(r"from app.schemas import.*?PlanningBrief.*?\n", "", c)
        c = re.sub(r"planning_brief:\s*PlanningBrief\s*\|\s*None\s*=\s*None,", "", c)
        c = c.replace("planning_brief=planning_brief,", "")
        open(f1, "w", encoding="utf-8").write(c)

    # 2. state_transition.py
    f2 = "app/intake/application/state_transition.py"
    if os.path.exists(f2):
        c = open(f2, encoding="utf-8").read()
        c = re.sub(r"from app.schemas import.*?TurnIntentResult.*?\n", "", c)
        c = re.sub(r"turn_intent:\s*TurnIntentResult\s*\|\s*None\s*=\s*None,", "", c)
        c = c.replace("turn_intent=turn_intent,", "")
        open(f2, "w", encoding="utf-8").write(c)

    # 3. nutrition_payload.py
    f3 = "app/nutrition/application/nutrition_payload.py"
    if os.path.exists(f3):
        c = open(f3, encoding="utf-8").read()
        c = re.sub(r"from app.schemas import.*?PlanningBrief.*?\n", "", c)
        c = re.sub(r"planning_brief:\s*PlanningBrief\s*\|\s*None\s*=\s*None,", "", c)
        open(f3, "w", encoding="utf-8").write(c)

    # 4. tool_dispatch.py
    f4 = "app/nutrition/application/tool_dispatch.py"
    if os.path.exists(f4):
        c = open(f4, encoding="utf-8").read()
        c = re.sub(r"from app.schemas import.*?TurnIntentResult.*?\n", "", c)
        c = re.sub(r"turn_intent:\s*TurnIntentResult,", "", c)
        open(f4, "w", encoding="utf-8").write(c)

fix()
