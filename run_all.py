"""
run_all.py

The Master Switch.
1. Clears old results.
2. Runs analysis on all LIN files in data/
3. Generates the website.
"""

import os
import shutil
import subprocess
from pathlib import Path

# CONFIG
PROJECT_ROOT = Path(__file__).parent
DATA_DIR = PROJECT_ROOT / "data"
RESULTS_DIR = DATA_DIR / "session_results"

def clean_old_results():
    """Deletes old JSON files to avoid mixing sessions."""
    if RESULTS_DIR.exists():
        print("🧹 Cleaning old results...")
        for f in os.listdir(RESULTS_DIR):
            if f.endswith(".json"):
                os.remove(RESULTS_DIR / f)

def run_analysis():
    print("🚀 Starting Analysis Engine...")
    # Pass the 'data' folder to src.main. It now handles directories.
    cmd = ["uv", "run", "python", "-m", "src.main", str(DATA_DIR)]
    subprocess.run(cmd, check=True)

def generate_website():
    print("🌐 Building Website...")
    cmd = ["uv", "run", "python", "generate_web.py"]
    subprocess.run(cmd, check=True)

if __name__ == "__main__":
    print("=== BRIDGE MASTER BATCH RUNNER ===")
    
    # 1. Cleanup
    clean_old_results()
    
    # 2. Analyze (Scans 'data/' for ALL .lin files)
    try:
        run_analysis()
    except subprocess.CalledProcessError:
        print("❌ Analysis failed. Stopping.")
        exit(1)
        
    # 3. Publish
    try:
        generate_website()
    except subprocess.CalledProcessError:
        print("❌ Website generation failed.")
        exit(1)
        
    print("\n✅ DONE! Open docs/index.html to view your hands.")