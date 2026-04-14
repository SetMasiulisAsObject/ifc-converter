"""
IFC Converter Launcher
Finds Python and runs ifc_converter.py from its fixed location.
This exe is just a thin wrapper — the actual code lives in the project folder.
"""
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(r"D:\User\OneDrive - Koncepta Engineering\Kodas Python\ifc-converter\ifc_converter.py")
PYTHON = Path(r"C:\Users\User\AppData\Local\Programs\Python\Python311\python.exe")

if not SCRIPT.exists():
    input(f"\nError: Script not found:\n  {SCRIPT}\n\nPress Enter to close...")
    sys.exit(1)

if not PYTHON.exists():
    input(f"\nError: Python not found:\n  {PYTHON}\n\nPress Enter to close...")
    sys.exit(1)

result = subprocess.run([str(PYTHON), str(SCRIPT)])
sys.exit(result.returncode)
