import sys, os, traceback
sys.path.insert(0, os.path.abspath("backend"))
from app.database.session import SessionLocal
from app.models.profile import Profile

session = SessionLocal()
try:
    test_profiles = session.query(Profile).filter((Profile.username.like("%user%")) | (Profile.username.like("%ai_%"))).all()
    print(f"Found {len(test_profiles)} test profiles to delete:")
    for p in test_profiles:
        print(f"Deleting profile {p.username}...")
        session.delete(p)
    session.commit()
    print("SUCCESS")
except Exception as e:
    print("EXCEPTION:")
    traceback.print_exc()
finally:
    session.close()
