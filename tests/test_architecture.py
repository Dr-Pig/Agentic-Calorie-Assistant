import pytest

def get_all_imports_in_module(module_path):
    import ast
    with open(module_path, "r", encoding="utf-8") as f:
        try:
            tree = ast.parse(f.read(), filename=str(module_path))
        except SyntaxError:
            return []
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for name in node.names:
                imports.append(name.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                # Resolve relative imports somewhat simply
                imports.append(node.module)
    return imports

def test_architecture_domain_does_not_depend_on_infrastructure(tmp_path):
    from pathlib import Path
    
    app_dir = Path("app")
    violations = []
    
    # Collect all python files in any domain folder
    for domain_dir in app_dir.glob("*/domain"):
        if not domain_dir.is_dir():
            continue
            
        for py_file in domain_dir.rglob("*.py"):
            imports = get_all_imports_in_module(py_file)
            for imp in imports:
                # Check absolute imports
                if "infrastructure" in imp or "interface" in imp:
                    violations.append(f"{py_file} imports {imp}")
                
    assert not violations, f"Architecture violation: Domain must not depend on infrastructure/interface. Found: {violations}"

def test_architecture_shared_does_not_depend_on_business_domains():
    from pathlib import Path
    
    shared_dir = Path("app/shared")
    violations = []
    
    # Shared should not import from intake, nutrition, body, budget, rescue, memory, etc.
    business_domains = ["intake", "nutrition", "body", "budget", "knowledge", "rescue", "recommendation", "memory"]
    
    for py_file in shared_dir.rglob("*.py"):
        imports = get_all_imports_in_module(py_file)
        for imp in imports:
            for bd in business_domains:
                if f"app.{bd}" in imp:
                    violations.append(f"{py_file} imports app.{bd} ({imp})")
                    
    assert not violations, f"Architecture violation: Shared must not depend on business domains. Found: {violations}"
