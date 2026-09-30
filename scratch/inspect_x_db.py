import sys
import os
sys.path.insert(0, os.path.abspath("backend"))

from app.database.session import SessionLocal
from app.models.profile import Profile
from app.models.post import Post, PostSnapshot
from app.models.enums import SocialPlatform

db = SessionLocal()
x_profiles = db.query(Profile).filter_by(platform=SocialPlatform.X).all()
print(f"Found {len(x_profiles)} X profiles:")
for p in x_profiles:
    print(f"\nProfile: @{p.username} (ID: {p.id})")
    posts = db.query(Post).filter_by(profile_id=p.id).all()
    print(f"Total Posts: {len(posts)}")
    for post in posts:
        snaps = db.query(PostSnapshot).filter_by(post_id=post.id).order_by(PostSnapshot.collected_at.desc()).all()
        if snaps:
            s = snaps[0]
            print(f"  Post ID {post.platform_post_id}: likes={s.likes}, comments={s.comments}, shares={s.shares}, views={s.views}, posted_at={post.posted_at}")
