import uuid
import pytest
from datetime import datetime, timezone, timedelta
from typing import List

from app.models.enums import SocialPlatform
from app.models.profile import Profile, ProfileSnapshot
from app.models.post import Post, PostSnapshot
from app.models.anomaly import Anomaly
from app.analytics import (
    calculate_absolute_growth,
    calculate_growth_percent,
    compute_growth_analytics,
    calculate_engagement_rate,
    compute_engagement_analytics,
    normalize_content_type,
    compute_content_analytics,
    sort_top_posts,
    compute_frequency_analytics,
    detect_follower_anomalies,
    compare_profile_overviews,
)
from app.analytics.schemas import (
    GrowthAnalytics,
    EngagementAnalytics,
    ContentAnalytics,
    FrequencyAnalytics,
    ProfileAnalyticsOverview,
)
from app.database.session import SessionLocal
from app.services.analytics_service import analytics_service


@pytest.fixture
def db_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.query(Profile).delete()
        session.commit()
        session.close()


# ---------------------------------------------------------
# 1. Growth Analytics Unit Tests
# ---------------------------------------------------------

def test_calculate_absolute_growth():
    assert calculate_absolute_growth(101220, 100000) == 1220
    assert calculate_absolute_growth(100000, 101220) == -1220
    assert calculate_absolute_growth(100, None) is None
    assert calculate_absolute_growth(None, 100) is None


def test_calculate_growth_percent():
    assert calculate_growth_percent(101220, 100000) == 1.22
    assert calculate_growth_percent(100, 0) is None
    assert calculate_growth_percent(None, 100) is None
    assert calculate_growth_percent(100, None) is None


def test_compute_growth_analytics_n_day_selection():
    now = datetime.now(timezone.utc)
    snapshots = [
        ProfileSnapshot(collected_at=now - timedelta(days=35), followers=10000),
        ProfileSnapshot(collected_at=now - timedelta(days=30), followers=10500),
        ProfileSnapshot(collected_at=now - timedelta(days=7), followers=12000),
        ProfileSnapshot(collected_at=now, followers=12500),
    ]

    res = compute_growth_analytics(snapshots)

    assert res.current_followers == 12500
    assert res.previous_followers == 12000
    assert res.absolute_growth == 500
    assert res.growth_percent == 4.17
    # 7-day growth: comparing now (12500) vs snapshot at/before now-7d (12000)
    assert res.growth_7d == 500
    # 30-day growth: comparing now (12500) vs snapshot at/before now-30d (10500)
    assert res.growth_30d == 2000
    assert res.growth_velocity is not None
    assert res.growth_velocity > 0


def test_compute_growth_analytics_missing_data():
    now = datetime.now(timezone.utc)
    # Missing follower values should return safe Nulls
    snapshots = [
        ProfileSnapshot(collected_at=now - timedelta(days=2), followers=None),
        ProfileSnapshot(collected_at=now, followers=None),
    ]

    res = compute_growth_analytics(snapshots)
    assert res.current_followers is None
    assert res.absolute_growth is None
    assert res.growth_percent is None
    assert res.growth_7d is None
    assert res.growth_30d is None


# ---------------------------------------------------------
# 2. Engagement Analytics Unit Tests
# ---------------------------------------------------------

def test_calculate_engagement_rate():
    assert calculate_engagement_rate(5000.0, 100000) == 5.0
    assert calculate_engagement_rate(5000.0, 0) is None
    assert calculate_engagement_rate(None, 100000) is None
    assert calculate_engagement_rate(5000.0, None) is None


def test_compute_engagement_analytics_null_preservation():
    # Post snapshot with likes and comments, but NULL shares and NULL views
    s1 = PostSnapshot(likes=100, comments=20, shares=None, views=None)
    s2 = PostSnapshot(likes=200, comments=40, shares=10, views=None)

    res = compute_engagement_analytics([s1, s2], current_followers=1000)

    assert res.sample_post_count == 2
    assert res.total_likes == 300
    assert res.total_comments == 60
    assert res.total_shares == 10
    assert res.total_views is None  # Views preserved as None (not converted to 0)
    assert res.available_metrics == ["comments", "likes", "shares"]
    assert res.total_engagement == 370.0
    assert res.average_engagement == 185.0
    assert res.median_engagement == 185.0
    assert res.engagement_rate == 37.0


# ---------------------------------------------------------
# 3. Content Analytics Unit Tests
# ---------------------------------------------------------

def test_normalize_content_type():
    assert normalize_content_type("photo") == "IMAGE"
    assert normalize_content_type("image") == "IMAGE"
    assert normalize_content_type("video") == "VIDEO"
    assert normalize_content_type("reels") == "REEL"
    assert normalize_content_type("carousel") == "CAROUSEL"
    assert normalize_content_type("tweet") == "TEXT"
    assert normalize_content_type("url") == "LINK"
    assert normalize_content_type("thread") == "THREAD"
    assert normalize_content_type("unknown_custom") == "UNKNOWN"
    assert normalize_content_type(None) == "UNKNOWN"


def test_compute_content_analytics():
    p1 = Post(id=uuid.uuid4(), media_type="photo", posted_at=datetime.now(timezone.utc))
    p2 = Post(id=uuid.uuid4(), media_type="video", posted_at=datetime.now(timezone.utc))
    s1 = PostSnapshot(post_id=p1.id, likes=100, comments=10)
    s2 = PostSnapshot(post_id=p2.id, likes=500, comments=50, views=2000)

    latest_map = {p1.id: s1, p2.id: s2}
    res = compute_content_analytics([p1, p2], latest_map)

    assert res.total_posts == 2
    types_found = {c.content_type: c for c in res.by_content_type}
    assert "IMAGE" in types_found
    assert types_found["IMAGE"].post_count == 1
    assert types_found["IMAGE"].average_engagement == 110.0

    assert "VIDEO" in types_found
    assert types_found["VIDEO"].post_count == 1
    assert types_found["VIDEO"].average_engagement == 550.0
    assert types_found["VIDEO"].total_views == 2000


# ---------------------------------------------------------
# 4. Posting Frequency Unit Tests
# ---------------------------------------------------------

def test_compute_frequency_analytics():
    now = datetime.now(timezone.utc)
    dates = [
        now - timedelta(days=10),
        now - timedelta(days=8),
        now - timedelta(days=5),
        now - timedelta(days=1),
    ]
    posts = [Post(id=uuid.uuid4(), posted_at=d, platform_post_id=str(i), url="http://x.com") for i, d in enumerate(dates)]

    res = compute_frequency_analytics(posts)

    assert res.posts_per_day > 0
    assert res.posts_per_week > 0
    assert res.avg_posting_interval_hours is not None
    assert res.median_posting_interval_hours is not None
    assert len(res.weekday_distribution) == 7
    assert len(res.hourly_distribution) == 24


def test_compute_frequency_analytics_zero_or_one_post():
    # 0 posts
    res0 = compute_frequency_analytics([])
    assert res0.posts_per_day == 0.0
    assert res0.avg_posting_interval_hours is None

    # 1 post
    res1 = compute_frequency_analytics([Post(id=uuid.uuid4(), posted_at=datetime.now(timezone.utc), platform_post_id="1", url="http://x.com")])
    assert res1.posts_per_day == 1.0
    assert res1.avg_posting_interval_hours is None


# ---------------------------------------------------------
# 5. Top Content Sorting Unit Tests
# ---------------------------------------------------------

def test_sort_top_posts():
    p1 = Post(id=uuid.uuid4(), platform_post_id="1", url="http://1", posted_at=datetime.now(timezone.utc) - timedelta(days=2))
    p2 = Post(id=uuid.uuid4(), platform_post_id="2", url="http://2", posted_at=datetime.now(timezone.utc) - timedelta(days=1))

    # p1 has 500 likes, p2 has NULL likes
    s1 = PostSnapshot(post_id=p1.id, likes=500, comments=10)
    s2 = PostSnapshot(post_id=p2.id, likes=None, comments=50)

    latest_map = {p1.id: s1, p2.id: s2}

    # Sort by likes: p1 (500) comes first, p2 (None) comes last
    top_likes = sort_top_posts([p1, p2], latest_map, sort_by="likes", limit=10)
    assert top_likes[0].post_id == p1.id
    assert top_likes[0].metric_value == 500.0
    assert top_likes[1].post_id == p2.id
    assert top_likes[1].metric_value is None

    # Sort by newest: p2 (1 day ago) comes before p1 (2 days ago)
    top_newest = sort_top_posts([p1, p2], latest_map, sort_by="newest", limit=10)
    assert top_newest[0].post_id == p2.id
    assert top_newest[1].post_id == p1.id


# ---------------------------------------------------------
# 6. Anomaly Detection Unit Tests
# ---------------------------------------------------------

def test_detect_follower_anomalies_no_false_positive():
    now = datetime.now(timezone.utc)
    # Steady follower growth ~300/day
    snapshots = [
        ProfileSnapshot(collected_at=now - timedelta(days=i), followers=10000 + (10 - i) * 300)
        for i in range(10, -1, -1)
    ]

    p_id = uuid.uuid4()
    anomalies = detect_follower_anomalies(p_id, snapshots, min_samples=5)
    assert len(anomalies) == 0


def test_detect_follower_anomalies_outlier_detection():
    now = datetime.now(timezone.utc)
    # Steady +300/day, then sudden +8700 spike on latest day
    followers_series = [10000 + i * 300 for i in range(9)] + [10000 + 8 * 300 + 8700]

    snapshots = [
        ProfileSnapshot(collected_at=now - timedelta(days=10 - i), followers=followers_series[i])
        for i in range(len(followers_series))
    ]

    p_id = uuid.uuid4()
    anomalies = detect_follower_anomalies(p_id, snapshots, min_samples=5)

    assert len(anomalies) >= 1
    anom = anomalies[0]
    assert anom.profile_id == p_id
    assert anom.metric == "follower_growth"
    assert anom.method == "rolling_median_mad"
    assert anom.observed_value >= 8000.0
    assert anom.severity in ("medium", "high")
    assert "rolling median baseline" in anom.description
    # Ensure NO causal claims in description text!
    assert "controversial" not in anom.description
    assert "viral" not in anom.description


# ---------------------------------------------------------
# 7. Comparison Unit Tests
# ---------------------------------------------------------

def test_compare_profile_overviews_descriptive_only():
    ov1 = ProfileAnalyticsOverview(
        profile_id=uuid.uuid4(),
        platform="instagram",
        username="user_a",
        growth=GrowthAnalytics(current_followers=100000, growth_7d=1200),
        engagement=EngagementAnalytics(average_engagement=450.0),
        content=ContentAnalytics(),
        frequency=FrequencyAnalytics(posts_per_week=5.0)
    )
    ov2 = ProfileAnalyticsOverview(
        profile_id=uuid.uuid4(),
        platform="x",
        username="user_b",
        growth=GrowthAnalytics(current_followers=85000, growth_7d=2100),
        engagement=EngagementAnalytics(average_engagement=300.0),
        content=ContentAnalytics(),
        frequency=FrequencyAnalytics(posts_per_week=8.0)
    )

    comp = compare_profile_overviews([ov1, ov2])

    assert len(comp.profiles) == 2
    p_map = {p.username: p for p in comp.profiles}

    assert p_map["user_a"].current_followers == 100000
    assert p_map["user_a"].growth_7d == 1200
    assert p_map["user_b"].current_followers == 85000
    assert p_map["user_b"].growth_7d == 2100

    # Ensure result schema contains NO winner / best_profile fields!
    dict_repr = comp.model_dump()
    assert "winner" not in dict_repr
    assert "best_profile" not in dict_repr
    assert "rank" not in dict_repr


# ---------------------------------------------------------
# 8. PostgreSQL Integration Test & Snapshot Integrity
# ---------------------------------------------------------

def test_analytics_service_db_integration(db_session):
    # 1. Create Profile
    profile = Profile(
        platform=SocialPlatform.INSTAGRAM,
        username=f"analytics_test_{uuid.uuid4().hex[:6]}",
        profile_url="https://instagram.com/analytics_test"
    )
    db_session.add(profile)
    db_session.commit()
    db_session.refresh(profile)

    now = datetime.now(timezone.utc)

    # 2. Add historical snapshots with an outlier growth spike
    follower_values = [10000, 10300, 10600, 10900, 11200, 11500, 20000]
    for i, val in enumerate(follower_values):
        snap = ProfileSnapshot(
            profile_id=profile.id,
            collected_at=now - timedelta(days=7 - i),
            followers=val,
            following=500,
            post_count=50
        )
        db_session.add(snap)

    # 3. Add Posts and PostSnapshots
    post = Post(
        profile_id=profile.id,
        platform_post_id="post_1001",
        url="https://instagram.com/p/1001",
        caption="Analytics Integration Test Post",
        posted_at=now - timedelta(days=2),
        media_type="photo"
    )
    db_session.add(post)
    db_session.flush()

    post_snap = PostSnapshot(
        post_id=post.id,
        collected_at=now - timedelta(days=1),
        likes=350,
        comments=45,
        shares=12,
        views=None
    )
    db_session.add(post_snap)
    db_session.commit()

    # 4. Execute Analytics Service Overview
    overview = analytics_service.get_profile_analytics_overview(db_session, profile.id)

    assert overview.profile_id == profile.id
    assert overview.growth.current_followers == 20000
    assert overview.engagement.sample_post_count == 1
    assert overview.engagement.total_likes == 350
    assert overview.content.total_posts == 1
    assert overview.frequency.posts_per_day > 0

    # 5. Detect and Persist Anomalies
    persisted_anomalies = analytics_service.detect_and_persist_anomalies(db_session, profile.id)
    assert len(persisted_anomalies) >= 1

    anomaly_db = db_session.query(Anomaly).filter_by(profile_id=profile.id).first()
    assert anomaly_db is not None
    assert anomaly_db.metric == "follower_growth"
    assert anomaly_db.method == "rolling_median_mad"

    # 6. Verify Historical Integrity: ProfileSnapshots remain unchanged
    snapshots_after = db_session.query(ProfileSnapshot).filter_by(profile_id=profile.id).order_by(ProfileSnapshot.collected_at.asc()).all()
    assert len(snapshots_after) == 7
    assert [s.followers for s in snapshots_after] == follower_values


def test_null_preservation_and_frequency_semantics_regression():
    """
    Regression test covering:
    1. Valid posted_at vs unavailable posted_at
    2. Available likes/comments vs unavailable engagement metrics
    3. Frequency when posts exist and timestamps exist vs when posts exist but timestamps are missing
    4. Engagement metrics when interaction data exists vs when all interaction metrics are NULL
    5. Top post sorting when ranking metrics exist vs when ranking metrics are unavailable
    """
    now = datetime.now(timezone.utc)
    p_with_dates = [
        Post(id=uuid.uuid4(), posted_at=now - timedelta(days=2), platform_post_id="p1", url="http://x.com/1"),
        Post(id=uuid.uuid4(), posted_at=now - timedelta(days=1), platform_post_id="p2", url="http://x.com/2"),
    ]
    p_no_dates = [
        Post(id=uuid.uuid4(), posted_at=None, platform_post_id="p3", url="http://x.com/3"),
        Post(id=uuid.uuid4(), posted_at=None, platform_post_id="p4", url="http://x.com/4"),
    ]

    # Frequency with valid dates
    freq_valid = compute_frequency_analytics(p_with_dates)
    assert freq_valid.posts_per_day is not None
    assert freq_valid.posts_per_day > 0
    assert freq_valid.posts_per_week is not None

    # Frequency with empty posts (0 posts observed)
    freq_empty = compute_frequency_analytics([])
    assert freq_empty.posts_per_day == 0.0
    assert freq_empty.posts_per_week == 0.0

    # Frequency with posts present BUT timestamps missing (NULL timestamps)
    freq_missing_dates = compute_frequency_analytics(p_no_dates)
    assert freq_missing_dates.posts_per_day is None
    assert freq_missing_dates.posts_per_week is None
    assert freq_missing_dates.posts_per_month is None

    # Engagement with all NULL metrics
    s_null1 = PostSnapshot(post_id=p_no_dates[0].id, likes=None, comments=None, shares=None, views=None)
    s_null2 = PostSnapshot(post_id=p_no_dates[1].id, likes=None, comments=None, shares=None, views=None)

    eng_null = compute_engagement_analytics([s_null1, s_null2], current_followers=1000)
    assert eng_null.sample_post_count == 2
    assert eng_null.total_likes is None
    assert eng_null.total_comments is None
    assert eng_null.total_shares is None
    assert eng_null.total_views is None
    assert eng_null.total_engagement is None
    assert eng_null.average_engagement is None
    assert eng_null.engagement_rate is None
    assert eng_null.available_metrics == []

    # Top posts sorting when all metrics are NULL
    latest_map = {p_no_dates[0].id: s_null1, p_no_dates[1].id: s_null2}
    top_null = sort_top_posts(p_no_dates, latest_map, sort_by="likes", limit=5)
    assert len(top_null) == 2
    assert top_null[0].metric_value is None
    assert top_null[1].metric_value is None
    assert top_null[0].likes is None
    assert top_null[0].posted_at is None

