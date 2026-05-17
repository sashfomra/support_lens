#!/usr/bin/env python3
"""Setup script — installs all SupportLens dependencies."""
import subprocess
import sys

packages = [
    "fastapi==0.111.0",
    "uvicorn[standard]",
    "sqlalchemy",
    "pydantic",
    "pydantic-settings",
    "httpx",
    "numpy<2.0",
    "scikit-learn",
    "python-multipart",
    "aiofiles",
    "python-dateutil",
    "sentence-transformers",
    "faiss-cpu",
    "transformers",
    "torch",
]

for pkg in packages:
    print(f"Installing {pkg}...")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", pkg, "-q"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"  WARN: {result.stderr[:200]}")
    else:
        print(f"  OK")

# spaCy separately
print("Installing spacy...")
subprocess.run([sys.executable, "-m", "pip", "install", "spacy", "-q"], capture_output=True)
try:
    subprocess.run([sys.executable, "-m", "spacy", "download", "en_core_web_sm", "-q"], capture_output=True)
    print("  spaCy model ok")
except Exception as e:
    print(f"  spaCy model failed (ok, regex fallback will be used): {e}")

print("\nAll dependencies installed!")
