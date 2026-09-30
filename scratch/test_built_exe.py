import os
import time
import socket
import urllib.request
import subprocess
from pathlib import Path

exe_path = Path(r"c:\Users\krish\Desktop\growth dashboard\dist\SocialScope\SocialScope.exe")

print("=== SMOKE TESTING BUILT EXECUTABLE ===")
print("Executable path:", exe_path, "Exists?", exe_path.exists())

if not exe_path.exists():
    print("Executable missing!")
    exit(1)

# Check if port 8000 is open
def check_health():
    try:
        with urllib.request.urlopen("http://127.0.0.1:8000/health", timeout=2) as resp:
            return resp.status == 200
    except Exception:
        return False

print("Initial health check:", check_health())
