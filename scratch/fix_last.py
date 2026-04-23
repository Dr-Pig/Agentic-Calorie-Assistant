import os
from pathlib import Path

# 1. Fix canonical_persistence schemas import
p = Path("app/shared/infra/canonical_persistence.py")
content = p.read_text(encoding="utf-8")
content = content.replace("from ..schemas import ", "from app.schemas import ")
p.write_text(content, encoding="utf-8")

# 2. Fix the double "infrastructure" in exact_item_lookup.py
p2 = Path("app/nutrition/infrastructure/web_search/exact_item_lookup.py")
if p2.exists():
    content = p2.read_text(encoding="utf-8")
    content = content.replace("from ..infrastructure.exact_item_search", "from ..exact_item_search")
    p2.write_text(content, encoding="utf-8")

print("Fixed final imports")
