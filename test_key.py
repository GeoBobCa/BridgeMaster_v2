# test_key.py
import os
from pathlib import Path
from dotenv import load_dotenv

# 1. Find the .env file
current_dir = Path(__file__).resolve().parent
env_path = current_dir / ".env"

print(f"Looking for .env at: {env_path}")

# 2. Load it
if env_path.exists():
    print("Found .env file!")
    load_dotenv(dotenv_path=env_path)
else:
    print("ERROR: .env file not found at that location.")

# 3. Check for the key
key = os.getenv("GOOGLE_API_KEY")

if key:
    print(f"SUCCESS! Found API Key. It starts with: {key[:4]}...")
else:
    print("ERROR: .env loaded, but GOOGLE_API_KEY is empty or missing inside it.")