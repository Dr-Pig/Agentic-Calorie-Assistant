import json
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

with open(r".logs\text_meal_events.jsonl", encoding="utf-8") as f:
    lines = f.readlines()

events = [json.loads(l) for l in lines if l.strip()]

# Find the latest test run - look for the 4 test inputs in the last 10 events
for idx in range(max(0, len(events)-10), len(events)):
    e = events[idx]
    text = e.get("text", "")
    p = e.get("payload") or {}
    action = e.get("action_taken") or p.get("action_taken","")
    route = e.get("route_target") or p.get("route_target","")
    title = p.get("meal_title","")
    comps = p.get("components",[])
    kcal = p.get("estimated_kcal",0)
    print(f"Event {idx+1}: text={text}")
    print(f"  title={title}  route={route}  action={action}")
    print(f"  comps={json.dumps(comps, ensure_ascii=False)}  kcal={kcal}")
    print(f"  protein={p.get('protein_g',0)} carb={p.get('carb_g',0)} fat={p.get('fat_g',0)}")
    
    traces = e.get("llm_traces") or p.get("llm_traces") or []
    for ti, tr in enumerate(traces):
        rc = (tr.get("raw_content") or "")
        # Check: does model return in English or Chinese?
        has_english = sum(1 for c in rc if c.isascii() and c.isalpha())
        has_chinese = sum(1 for c in rc if '\u4e00' <= c <= '\u9fff')
        ct = tr.get("completion_tokens","")
        print(f"  trace[{ti}]: stage={tr.get('stage','')} comp={ct} EN_chars={has_english} ZH_chars={has_chinese}")
        
        # Show the role values used
        import re
        roles_found = re.findall(r'\|\s*(\w+)\s*\|', rc)
        if roles_found:
            print(f"    roles_used: {roles_found}")
    print()
