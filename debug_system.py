import sys
import os

print("--- DIAGNOSTIC START ---")

# 1. CHECK PYTHON ENVIRONMENT
print(f"Python Executable: {sys.executable}")

# 2. CHECK DATA FILE CONTENT
file_path = "data/test_hands.lin"
print(f"\nChecking file: {file_path}")
if os.path.exists(file_path):
    with open(file_path, 'r') as f:
        content = f.read()
        print(f"File Length: {len(content)} chars")
        print(f"First 100 chars: {content[:100]}")
        if "..." in content:
            print("CRITICAL ALERT: File contains '...' dots! It is the OLD data.")
        else:
            print("Status: Data looks clean (No dots found).")
else:
    print("ERROR: File not found!")

# 3. CHECK ENDPLAY IMPORT
print("\nAttempting to import endplay...")
try:
    import endplay
    print(f"SUCCESS: endplay version {getattr(endplay, '__version__', 'unknown')} is installed.")
    from endplay.types import Deal
    print("SUCCESS: endplay.types loaded.")
except ImportError as e:
    print(f"FAILURE: Could not import endplay. Error: {e}")
except Exception as e:
    print(f"FAILURE: endplay crashed on load (DLL issue?). Error: {e}")

print("--- DIAGNOSTIC END ---")