import os, stat, shutil
from pathlib import Path

def remove_readonly(func, path, excinfo):
    os.chmod(path, stat.S_IWRITE)
    func(path)

dist_dir = Path("dist/SocialScope")
if dist_dir.exists():
    shutil.rmtree(dist_dir, onerror=remove_readonly)
    print("Successfully removed dist/SocialScope after clearing read-only flags!")
else:
    print("dist/SocialScope does not exist.")
