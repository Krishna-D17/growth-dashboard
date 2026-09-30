import os, sys, shutil
from pathlib import Path

dist_dir = Path("dist/SocialScope")
if dist_dir.exists():
    try:
        shutil.rmtree(dist_dir)
        print("Successfully removed dist/SocialScope")
    except Exception as e:
        print(f"Could not remove dist/SocialScope directly: {e}")
        stale_dir = Path(f"dist/SocialScope_stale_{os.getpid()}")
        try:
            dist_dir.rename(stale_dir)
            print(f"Renamed dist/SocialScope to {stale_dir}")
        except Exception as e2:
            print(f"Failed to rename dist/SocialScope: {e2}")
else:
    print("dist/SocialScope does not exist.")
