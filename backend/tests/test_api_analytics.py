import uuid
import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

from app.main import app
from app.database.session import SessionLocal
from app.models.enums import SocialPlatform
from app.models.profile import Profile, ProfileSnapshot
from app.models.post import Post, PostSnapshot

client = TestClient(app)


@pytest.fixture
def db():
    session = SessionLocal()
    session.query(Profile).delete()
    session.commit()
    try:
        yield session
    finally:
        session.rollback()
        session.query(Profile).delete()
        session.commit()
        session.close()


def create_sample_profile_data(db, username_prefix: str = "api_test"):
    now = datetime.now(timezone.utc)
    profile = Profile(
        platform=SocialPlatform.INSTAGRAM,
        username=f"{username_prefix}_{uuid.uuid4().hex[:6]}",
        profile_url="https://instagram.com/test"
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)

    # Snapshots (10000 -> 10500 -> 11000 -> 12000 -> 20000)
    vals = [10000, 10500, 11000, 12000, 20000]
    for i, val in enumerate(vals):
        snap = ProfileSnapshot(
            profile_id=profile.id,
            collected_at=now - timedelta(days=30 - i * 7),
            followers=val,
            following=400,
            post_count=20 + i
        )
        db.add(snap)

    # Posts
    post1 = Post(
        profile_id=profile.id,
        platform_post_id="p1",
        url="https://instagram.com/p/1",
        caption="Sample Image Post",
        posted_at=now - timedelta(days=5),
        media_type="photo"
    )
    post2 = Post(
        profile_id=profile.id,
        platform_post_id="p2",
        url="https://instagram.com/p/2",
        caption="Sample Video Post",
        posted_at=now - timedelta(days=2),
        media_type="video"
    )
    db.add_all([post1, post2])
    db.flush()

    s1 = PostSnapshot(post_id=post1.id, collected_at=now - timedelta(days=4), likes=500, comments=50, shares=10, views=None)
    s2 = PostSnapshot(post_id=post2.id, collected_at=now - timedelta(days=1), likes=1200, comments=100, shares=30, views=5000)
    db.add_all([s1, s2])
    db.commit()

    return profile


# 1. Overview Endpoint
def test_get_profile_analytics_overview_endpoint(db):
    profile = create_sample_profile_data(db, "overview")
    resp = client.get(f"/api/profiles/{profile.id}/analytics/overview")

    assert resp.status_code == 200
    data = resp.json()
    assert data["profile_id"] == str(profile.id)
    assert data["platform"] == "instagram"
    assert data["growth"]["current_followers"] == 20000
    assert data["engagement"]["total_likes"] == 1700
    assert data["content"]["total_posts"] == 2
    assert data["frequency"]["posts_per_day"] > 0
    assert "anomalies" in data


# 2. Growth Endpoint & Values
def test_get_profile_growth_endpoint(db):
    profile = create_sample_profile_data(db, "growth")
    resp = client.get(f"/api/profiles/{profile.id}/analytics/growth")

    assert resp.status_code == 200
    data = resp.json()
    assert data["current_followers"] == 20000
    assert data["previous_followers"] == 12000
    assert data["absolute_growth"] == 8000
    assert data["growth_percent"] == 66.67
    assert data["growth_velocity"] is not None


# 3. Growth Endpoint Preserves Nulls for Empty History
def test_get_profile_growth_preserves_null_without_history(db):
    profile = Profile(
        platform=SocialPlatform.INSTAGRAM,
        username=f"nohist_{uuid.uuid4().hex[:6]}",
        profile_url="https://instagram.com/nohist"
    )
    db.add(profile)
    db.commit()

    resp = client.get(f"/api/profiles/{profile.id}/analytics/growth")
    assert resp.status_code == 200
    data = resp.json()
    assert data["current_followers"] is None
    assert data["absolute_growth"] is None
    assert data["growth_7d"] is None
    assert data["growth_30d"] is None


# 4. Engagement Endpoint
def test_get_profile_engagement_endpoint(db):
    profile = create_sample_profile_data(db, "eng")
    resp = client.get(f"/api/profiles/{profile.id}/analytics/engagement")

    assert resp.status_code == 200
    data = resp.json()
    assert data["sample_post_count"] == 2
    assert data["total_likes"] == 1700
    assert data["total_comments"] == 150
    assert data["total_shares"] == 40
    assert data["available_metrics"] == ["comments", "likes", "shares", "views"]
    assert data["engagement_rate"] is not None


# 5. Content Endpoint & Normalization
def test_get_profile_content_endpoint(db):
    profile = create_sample_profile_data(db, "content")
    resp = client.get(f"/api/profiles/{profile.id}/analytics/content")

    assert resp.status_code == 200
    data = resp.json()
    assert data["total_posts"] == 2
    types = {item["content_type"]: item for item in data["by_content_type"]}
    assert "IMAGE" in types
    assert "VIDEO" in types
    assert types["IMAGE"]["post_count"] == 1
    assert types["VIDEO"]["total_views"] == 5000


# 6. Frequency Endpoint
def test_get_profile_frequency_endpoint(db):
    profile = create_sample_profile_data(db, "freq")
    resp = client.get(f"/api/profiles/{profile.id}/analytics/frequency")

    assert resp.status_code == 200
    data = resp.json()
    assert data["posts_per_day"] > 0
    assert data["posts_per_week"] > 0
    assert "weekday_distribution" in data
    assert "hourly_distribution" in data


# 7. Top Posts Endpoint & Sorting
def test_get_profile_top_posts_endpoint(db):
    profile = create_sample_profile_data(db, "top")
    resp = client.get(f"/api/profiles/{profile.id}/analytics/top-posts?sort_by=likes&limit=10")

    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert data[0]["platform_post_id"] == "p2"  # 1200 likes > 500 likes
    assert data[0]["likes"] == 1200
    assert data[1]["platform_post_id"] == "p1"
    assert data[1]["likes"] == 500


# 8. Null Metrics Preserved in Top Posts
def test_top_posts_preserves_null_metrics(db):
    profile = create_sample_profile_data(db, "nulltop")
    resp = client.get(f"/api/profiles/{profile.id}/analytics/top-posts?sort_by=views&limit=10")

    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert data[0]["platform_post_id"] == "p2"  # 5000 views
    assert data[0]["views"] == 5000
    assert data[1]["platform_post_id"] == "p1"  # views is NULL
    assert data[1]["views"] is None


# 9. Anomalies Endpoint
def test_get_profile_anomalies_endpoint(db):
    profile = create_sample_profile_data(db, "anom")
    resp = client.get(f"/api/profiles/{profile.id}/analytics/anomalies")

    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    if data:
        assert data[0]["metric"] == "follower_growth"
        assert "severity" in data[0]


# 10 & 11. Comparison Endpoint without Winner/Ranking Fields
def test_get_profile_comparison_endpoint(db):
    p1 = create_sample_profile_data(db, "comp1")
    p2 = create_sample_profile_data(db, "comp2")

    resp = client.get(f"/api/comparison?profile_ids={p1.id},{p2.id}")

    assert resp.status_code == 200
    data = resp.json()
    assert len(data["profiles"]) == 2
    usernames = {p["username"] for p in data["profiles"]}
    assert p1.username in usernames
    assert p2.username in usernames

    # Verify NO subjective ranking or winner fields
    assert "winner" not in data
    assert "best_profile" not in data
    assert "rank" not in data


# 12. Nonexistent Profile returns 404
def test_nonexistent_profile_returns_404():
    fake_id = uuid.uuid4()
    resp = client.get(f"/api/profiles/{fake_id}/analytics/overview")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


# 13. Malformed UUID returns 422
def test_malformed_uuid_returns_422():
    resp = client.get("/api/profiles/not-a-valid-uuid/analytics/overview")
    assert resp.status_code == 422


# 14. Invalid Comparison Request returns 422
def test_invalid_comparison_request_returns_422():
    resp = client.get("/api/comparison?profile_ids=invalid-uuid-string")
    assert resp.status_code == 422


# 15. Invalid Sort Metric returns 422
def test_invalid_sort_metric_returns_422(db):
    profile = create_sample_profile_data(db, "invalsort")
    resp = client.get(f"/api/profiles/{profile.id}/analytics/top-posts?sort_by=nonexistent_metric")
    assert resp.status_code == 422
