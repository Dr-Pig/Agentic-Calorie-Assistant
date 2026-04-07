import re

with open("app/usecases/text_meal.py", "r", encoding="utf-8") as f:
    code = f.read()

# Replace PlannerPassResult with TurnIntentResult
code = code.replace("PlannerPassResult", "TurnIntentResult")

# Remove planner_result.route references
code = re.sub(r'"route": planner_result\.route,?\s*', '', code)
code = re.sub(r'route=planner_result\.route,?\s*', '', code)

# Update PLANNER_PROMPT
old_prompt = "輸出格式：必須為 JSON，包含 intent, route, normalized_user_input。"
new_prompt = "輸出格式：必須為 JSON，包含 intent, resolved_query, resolution_mode, normalized_user_input。"
code = code.replace(old_prompt, new_prompt)

with open("app/usecases/text_meal.py", "w", encoding="utf-8") as f:
    f.write(code)

print("Updated text_meal.py")
