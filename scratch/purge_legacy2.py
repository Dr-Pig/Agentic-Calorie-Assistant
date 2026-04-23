import os
from pathlib import Path

# 1. app/intake/application/decision_payload.py
p1 = Path("app/intake/application/decision_payload.py")
if p1.exists():
    c = p1.read_text(encoding="utf-8")
    c = c.replace("from app.shared.contracts.intake import PlanningBrief", "")
    c = c.replace("planner_result: PlanningBrief | None,", "")
    p1.write_text(c, encoding="utf-8")

# 2. app/intake/application/state_transition.py
p2 = Path("app/intake/application/state_transition.py")
if p2.exists():
    c = p2.read_text(encoding="utf-8")
    c = c.replace("from app.shared.contracts.intake import TurnIntentResult", "")
    c = c.replace("planner_result: TurnIntentResult | None,", "")
    p2.write_text(c, encoding="utf-8")

# 3. app/nutrition/application/nutrition_payload.py
p3 = Path("app/nutrition/application/nutrition_payload.py")
if p3.exists():
    c = p3.read_text(encoding="utf-8")
    c = c.replace("from app.shared.contracts.intake import PlanningBrief", "")
    c = c.replace("planner_result: PlanningBrief | None,", "")
    p3.write_text(c, encoding="utf-8")

# 4. app/nutrition/application/tool_dispatch.py
p4 = Path("app/nutrition/application/tool_dispatch.py")
if p4.exists():
    c = p4.read_text(encoding="utf-8")
    c = c.replace("from app.shared.contracts.intake import TurnIntentResult", "")
    c = c.replace("planner_result: TurnIntentResult,", "")
    p4.write_text(c, encoding="utf-8")

# 5. app/shared/domain/__init__.py
p5 = Path("app/shared/domain/__init__.py")
if p5.exists():
    c = p5.read_text(encoding="utf-8")
    c = c.replace("TurnIntentResult,", "")
    c = c.replace('"TurnIntentResult",', "")
    p5.write_text(c, encoding="utf-8")

print("Remaining legacy terms removed.")
