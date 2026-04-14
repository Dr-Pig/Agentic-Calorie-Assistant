"""Post-run audit safety scan for encoding corruption.
Scans logs and artifacts for mangled characters (`????`, `\ufffd`) that escaped
the pre-run file-backed audit input guard.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

DANGER_PATTERNS = ["????", "\ufffd"]

def check_directory(dir_path: Path) -> list[str]:
    violations = []
    if not dir_path.exists() or not dir_path.is_dir():
        return violations
        
    for file_path in dir_path.rglob("*"):
        if not file_path.is_file() or file_path.suffix not in {".md", ".json", ".txt"}:
            continue
            
        try:
            content = file_path.read_text(encoding="utf-8")
            for pattern in DANGER_PATTERNS:
                if pattern in content:
                    violations.append(f"{file_path.relative_to(ROOT)} contains mangled character pattern: '{pattern}'")
                    break
        except UnicodeDecodeError:
            violations.append(f"{file_path.relative_to(ROOT)} is not valid UTF-8.")
            
    return violations

def main() -> int:
    logs_dir = ROOT / ".logs"
    artifacts_dir = ROOT / "artifacts"
    
    all_violations = check_directory(logs_dir) + check_directory(artifacts_dir)
    
    if all_violations:
        print("[FAIL] HARNESS GATE FAILED: ENCODING CORRUPTION DETECTED", file=sys.stderr)
        print("The following files contain evidence of PowerShell pipe corruption or invalid UTF-8:", file=sys.stderr)
        for v in all_violations:
            print(f"  - {v}", file=sys.stderr)
        print("\nPlease fix the source of the corruption, delete these artifacts, and use file-backed inputs.", file=sys.stderr)
        return 1
        
    print("[OK] Audit safety check passed: No encoding corruption detected in logs or artifacts.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
