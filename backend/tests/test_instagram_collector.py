import os
import uuid
import pytest
from app.database.session import SessionLocal
from app.models.enums import SocialPlatform, JobStatus
from app.models.profile import Profile, ProfileSnapshot
from app.models.post import Post, PostSnapshot
from app.models.collection import CollectionJob
from app.schemas.collector import CollectorTarget
from app.collectors.instagram import InstagramCollector, InstagramParser
from app.collectors.browser import MockBrowserDriver
from app.collectors.registry import registry, CollectorRegistry
from app.collectors.exceptions import (
    TargetValidationError,
    PlatformNotSupportedError,
    ContentUnavailableError,
    RateLimitError,
)
from app.services.collection_service import CollectionService

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures", "instagram")


def load_fixture(filename: str) -> str:
    path = os.path.join(FIXTURES_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def test_instagram_target_validation():
    mock_driver = MockBrowserDriver()
    collector = InstagramCollector(browser_driver=mock_driver)

    valid_url_target = CollectorTarget(
        platform=SocialPlatform.INSTAGRAM,
        username="techinsider",
        profile_url="https://www.instagram.com/techinsider/"
    )
    assert collector.validate_target(valid_url_target) is True

    valid_handle_target = CollectorTarget(
        platform=SocialPlatform.INSTAGRAM,
        username="@techinsider",
        profile_url="https://instagram.com/techinsider"
    )
    assert collector.validate_target(valid_handle_target) is True

    invalid_x_target = CollectorTarget(
        platform=SocialPlatform.INSTAGRAM,
        username="techinsider",
        profile_url="https://x.com/techinsider"
    )
    assert collector.validate_target(invalid_x_target) is False

    invalid_fb_target = CollectorTarget(
        platform=SocialPlatform.INSTAGRAM,
        username="techinsider",
        profile_url="https://facebook.com/techinsider"
    )
    assert collector.validate_target(invalid_fb_target) is False


def test_instagram_profile_parsing_from_fixture():
    html = load_fixture("public_profile.html")
    profile = InstagramParser.parse_profile(html, "techinsider", "https://www.instagram.com/techinsider/")

    assert profile.platform == SocialPlatform.INSTAGRAM
    assert profile.username == "techinsider"
    assert profile.display_name == "Tech Insider"
    assert profile.followers == 12500
    assert profile.following == 450
    assert profile.post_count == 88
    assert profile.verified is True
    assert profile.profile_image_url == "https://instagram.fcdn.net/v/t51.2885-19/techinsider_avatar.jpg"
    assert "ultimate source for tech news" in profile.bio
    assert profile.platform_profile_id == "ig_techinsider"  # Deterministic stable ID


def test_instagram_post_parsing_from_fixture():
    html = load_fixture("public_profile.html")
    posts = InstagramParser.parse_posts(html, "techinsider", "https://www.instagram.com/techinsider/", limit=10)

    assert len(posts) == 3
    assert posts[0].platform_post_id == "C1234567890"
    assert posts[0].media_type == "IMAGE"
    assert posts[0].metrics.shares is None  # Shares non-public on Instagram

    assert posts[1].platform_post_id == "C0987654321"
    assert posts[1].media_type == "REEL"


def test_instagram_failure_modes_from_fixtures():
    login_html = load_fixture("login_wall.html")
    with pytest.raises(ContentUnavailableError):
        InstagramParser.parse_profile(login_html, "private_user", "https://www.instagram.com/private_user/")

    not_found_html = load_fixture("not_found.html")
    with pytest.raises(ContentUnavailableError):
        InstagramParser.parse_profile(not_found_html, "missing_user", "https://www.instagram.com/missing_user/")

    rate_limit_html = "<html><head><title>Too Many Requests</title></head><body>rate limit exceeded</body></html>"
    with pytest.raises(RateLimitError):
        InstagramParser.parse_profile(rate_limit_html, "rl_user", "https://www.instagram.com/rl_user/")


def test_global_registry_status():
    """Verify Instagram, X, and Facebook are all registered on global registry."""
    inst_collector = registry.get_collector(SocialPlatform.INSTAGRAM)
    assert isinstance(inst_collector, InstagramCollector)

    from app.collectors.x import XCollector
    x_collector = registry.get_collector(SocialPlatform.X)
    assert isinstance(x_collector, XCollector)

    from app.collectors.facebook import FacebookPageCollector
    fb_collector = registry.get_collector(SocialPlatform.FACEBOOK)
    assert isinstance(fb_collector, FacebookPageCollector)


def test_instagram_duplicate_profile_prevention(db):
    """Verify that handle/URL variations resolve to the exact same Profile identity without creating duplicates."""
    html = load_fixture("public_profile.html")
    mock_driver = MockBrowserDriver(simulated_html=html)
    inst_collector = InstagramCollector(browser_driver=mock_driver)

    test_reg = CollectorRegistry()
    test_reg.register(SocialPlatform.INSTAGRAM, inst_collector)
    service = CollectionService(registry=test_reg)

    uid = uuid.uuid4().hex[:8]
    handle_base = f"ident_test_{uid}"

    # Variant 1: bare username
    t1 = CollectorTarget(
        platform=SocialPlatform.INSTAGRAM,
        username=handle_base,
        profile_url=f"https://www.instagram.com/{handle_base}/"
    )
    job1 = service.execute_collection(db, t1, post_limit=1)
    assert job1.status == JobStatus.SUCCESS

    # Variant 2: prefixed with @
    t2 = CollectorTarget(
        platform=SocialPlatform.INSTAGRAM,
        username=f"@{handle_base}",
        profile_url=f"https://instagram.com/{handle_base}"
    )
    job2 = service.execute_collection(db, t2, post_limit=1)
    assert job2.status == JobStatus.SUCCESS

    # Variant 3: uppercase variation
    t3 = CollectorTarget(
        platform=SocialPlatform.INSTAGRAM,
        username=handle_base.upper(),
        profile_url=f"https://www.instagram.com/{handle_base.upper()}/"
    )
    job3 = service.execute_collection(db, t3, post_limit=1)
    assert job3.status == JobStatus.SUCCESS

    # Verify exactly 1 Profile record was created for all 3 variations
    profiles = db.query(Profile).filter_by(platform=SocialPlatform.INSTAGRAM, username=handle_base.lower()).all()
    assert len(profiles) == 1

    # Verify 3 distinct ProfileSnapshot observations were preserved over time
    snapshots = db.query(ProfileSnapshot).filter_by(profile_id=profiles[0].id).all()
    assert len(snapshots) == 3


def test_instagram_collection_service_integration(db):
    html = load_fixture("public_profile.html")
    mock_driver = MockBrowserDriver(simulated_html=html)
    inst_collector = InstagramCollector(browser_driver=mock_driver)

    test_reg = CollectorRegistry()
    test_reg.register(SocialPlatform.INSTAGRAM, inst_collector)

    uid = uuid.uuid4().hex[:8]
    username = f"ig_test_{uid}"
    target = CollectorTarget(
        platform=SocialPlatform.INSTAGRAM,
        username=username,
        profile_url=f"https://www.instagram.com/{username}/"
    )

    service = CollectionService(registry=test_reg)

    # 1st Collection run
    job1 = service.execute_collection(db, target, post_limit=2)
    assert job1.status == JobStatus.SUCCESS
    assert job1.records_collected == 2

    profile = db.query(Profile).filter_by(platform=SocialPlatform.INSTAGRAM, username=username).first()
    assert profile is not None

    snapshots1 = db.query(ProfileSnapshot).filter_by(profile_id=profile.id).all()
    assert len(snapshots1) == 1
    assert snapshots1[0].followers == 12500

    posts1 = db.query(Post).filter_by(profile_id=profile.id).all()
    assert len(posts1) == 2

    # 2nd Collection run (verify historical snapshot preservation)
    job2 = service.execute_collection(db, target, post_limit=2)
    assert job2.status == JobStatus.SUCCESS

    snapshots2 = db.query(ProfileSnapshot).filter_by(profile_id=profile.id).all()
    assert len(snapshots2) == 2
    assert snapshots2[0].id != snapshots2[1].id


def test_instagram_parse_post_detail_from_fixture():
    post_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta property="og:description" content="308 likes, 12 comments - techinsider on September 26, 2026: &quot;Advancing Communication Capabilities&quot;." />
    </head>
    <body>
        <time datetime="2026-09-26T14:49:13.000Z">Sep 26, 2026</time>
    </body>
    </html>
    """
    likes, comments, posted_at, caption = InstagramParser.parse_post_detail(post_html)

    assert likes == 308
    assert comments == 12
    assert posted_at is not None
    assert posted_at.year == 2026
    assert posted_at.month == 9
    assert posted_at.day == 26
    assert "Advancing Communication Capabilities" in caption


def test_abbreviated_metric_parsing():
    html_12k = """<meta property="og:description" content="12.5k likes, 1.2k comments - user on Sep 20" />"""
    likes, comments, _, _ = InstagramParser.parse_post_detail(html_12k)
    assert likes == 12500
    assert comments == 1200

    html_1m = """<meta property="og:description" content="1.2m likes, 45 comments - user on Sep 20" />"""
    likes_m, comments_m, _, _ = InstagramParser.parse_post_detail(html_1m)
    assert likes_m == 1200000
    assert comments_m == 45

