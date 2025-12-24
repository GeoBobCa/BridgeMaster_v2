"""
debug_system.py
Checks why the docs folder is empty.
"""
import os
import glob
from pathlib import Path

ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"
LIN_FILES = list(DATA_DIR.glob("*.lin"))
JSON_DIR = DATA_DIR / "session_results"
JSON_FILES = list(JSON_DIR.glob("*.json"))
DOCS_DIR = ROOT / "docs"
HTML_FILES = list(DOCS_DIR.glob("*.html"))

print(f"--- DIAGNOSTIC REPORT ---")
print(f"ROOT: {ROOT}")

print(f"\n1. INPUT CHECK (Data Folder)")
if not LIN_FILES:
    print("❌ ERROR: No .lin files found in /data/")
else:
    print(f"✅ Found {len(LIN_FILES)} .lin files.")

print(f"\n2. INTERMEDIATE CHECK (Session Results)")
if not JSON_DIR.exists():
    print("❌ ERROR: /data/session_results folder does not exist.")
elif not JSON_FILES:
    print("❌ ERROR: Folder exists but is EMPTY. The Parser/Analysis failed to save any hands.")
else:
    print(f"✅ Found {len(JSON_FILES)} JSON result files.")

print(f"\n3. OUTPUT CHECK (Docs Folder)")
if not DOCS_DIR.exists():
    print("❌ ERROR: /docs folder does not exist.")
elif not HTML_FILES:
    print("❌ ERROR: Folder exists but is EMPTY. The Web Generator ran but produced nothing.")
else:
    print(f"✅ Found {len(HTML_FILES)} HTML files.")

print("\n--- CONCLUSION ---")
if not LIN_FILES:
    print("👉 ACTION: Put .lin files in the /data/ folder.")
elif not JSON_FILES:
    print("👉 ACTION: The problem is the PARSER. It is reading the LIN files but discarding them (probably the 39-card deck error).")
    print("   Make sure you updated 'src/parsers/lin_parser.py' with the code that fixes missing hands.")
elif not HTML_FILES:
    print("👉 ACTION: The problem is the WEB GENERATOR. It sees the JSON files but fails to render them.")
else:
    print("❓ Everything looks fine? Check if you are looking in the right folder.")