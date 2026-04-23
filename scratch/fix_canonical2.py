import os
from pathlib import Path

p = Path("app/shared/infra/canonical_persistence.py")
content = p.read_text(encoding="utf-8")
if "from ..models import (" in content:
    content = content.replace("from ..models import (", "from app.models import (")
    p.write_text(content, encoding="utf-8")
    print("Fixed canonical_persistence.py")
