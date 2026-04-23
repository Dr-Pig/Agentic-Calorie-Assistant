import os
from pathlib import Path

p = Path("app/database.py")
if p.exists():
    content = p.read_text(encoding="utf-8")
    content = content.replace(
        "from .infrastructure.exact_item_search import ensure_exact_item_fts",
        "from app.nutrition.infrastructure.web_search.exact_item_lookup import ensure_exact_item_fts" # Or simply comment it out if it fails, since database.py is becoming a shim
    )
    p.write_text(content, encoding="utf-8")
    print("Fixed database.py")
