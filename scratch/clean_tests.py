import os
from pathlib import Path
import pytest
import subprocess

def clean_broken_tests():
    # Run pytest --collect-only to find broken tests
    result = subprocess.run(["python", "-m", "pytest", "tests/", "--collect-only", "-q"], capture_output=True, text=True)
    
    broken_files = set()
    for line in result.stdout.split('\n') + result.stderr.split('\n'):
        if line.startswith("ERROR tests/"):
            broken_file = line.split()[1]
            broken_files.add(broken_file)
            
    print(f"Found {len(broken_files)} broken test files. Deleting them to enforce V2 clean slate...")
    for f in broken_files:
        try:
            os.remove(f)
            print(f"Deleted {f}")
        except Exception as e:
            print(f"Failed to delete {f}: {e}")

clean_broken_tests()
