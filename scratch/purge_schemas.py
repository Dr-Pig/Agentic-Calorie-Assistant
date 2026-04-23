import os
from pathlib import Path
import re

def purge_legacy_schemas():
    # 1. Purge from app/schemas.py
    schemas_path = Path("app/schemas.py")
    if schemas_path.exists():
        lines = schemas_path.read_text(encoding="utf-8").split("\n")
        new_lines = [l for l in lines if not any(term in l for term in ["PlanningBrief", "TurnIntentResult", "NutritionEstimateResult", "TaskMealLinkResult"])]
        schemas_path.write_text("\n".join(new_lines), encoding="utf-8")

    # 2. Purge from app/shared/contracts/intake.py
    intake_contracts = Path("app/shared/contracts/intake.py")
    if intake_contracts.exists():
        content = intake_contracts.read_text(encoding="utf-8")
        # We just remove the class definitions completely using regex
        content = re.sub(r"class PlanningBrief\(BaseModel\):.*?class ", "class ", content, flags=re.DOTALL)
        content = re.sub(r"class TurnIntentResult\(BaseModel\):.*?(class |$)", r"\1", content, flags=re.DOTALL)
        content = re.sub(r"class TaskMealLinkResult\(BaseModel\):.*?(class |$)", r"\1", content, flags=re.DOTALL)
        content = re.sub(r"class NutritionEstimateResult\(BaseModel\):.*?(class |$)", r"\1", content, flags=re.DOTALL)
        intake_contracts.write_text(content, encoding="utf-8")

    # 3. Purge from app/shared/domain/conversation_state.py
    conv_state = Path("app/shared/domain/conversation_state.py")
    if conv_state.exists():
        content = conv_state.read_text(encoding="utf-8")
        content = re.sub(r"class TurnIntentResult\(BaseModel\):.*?(class |$)", r"\1", content, flags=re.DOTALL)
        conv_state.write_text(content, encoding="utf-8")
        
    # 4. Purge from docs/specs/APP_V2_IMPLEMENTATION_PLAN.md
    docs = Path("docs/specs/APP_V2_IMPLEMENTATION_PLAN.md")
    if docs.exists():
        content = docs.read_text(encoding="utf-8")
        content = content.replace("- `PlanningBrief`", "")
        content = content.replace("- `TurnIntentResult`", "")
        content = content.replace("- `TaskMealLinkResult`", "")
        docs.write_text(content, encoding="utf-8")
        
    print("Purged legacy schemas successfully.")

purge_legacy_schemas()
