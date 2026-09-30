import sys
import os
sys.path.insert(0, os.path.abspath("backend"))

from app.database.session import SessionLocal
from app.models.profile import Profile
from app.models.post import Post, PostSnapshot
from app.models.enums import SocialPlatform
from app.services.analytics_service import analytics_service

db = SessionLocal()
imv = db.query(Profile).filter_by(platform=SocialPlatform.X, username="imvkohli").first()
if imv:
    overview = analytics_service.get_profile_analytics_overview(db, imv.id)
    eng = overview.engagement
    print("\n--- Corrected Engagement Analytics for @imvkohli ---")
    print(f"Total Likes: {eng.total_likes}")
    print(f"Total Comments: {eng.total_comments}")
    print(f"Total Shares: {eng.total_shares}")
    print(f"Total Views: {eng.total_views}")
    print(f"Total Engagement: {eng.total_engagement}")
    print(f"Average Engagement: {eng.average_engagement}")
    print(f"Sample Post Count: {eng.sample_post_count}")

    top_posts = analytics_service.get_top_posts(db, imv.id, sort_by="comments", limit=10)
    print("\n--- Top Posts sorted by Comments ---")
    for tp in top_posts:
        print(f"Post ID {tp.platform_post_id}: comments={tp.comments}, likes={tp.likes}, shares={tp.shares}, views={tp.views}, engagement={tp.engagement}")
