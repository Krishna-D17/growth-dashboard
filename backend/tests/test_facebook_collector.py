import os
import uuid
import pytest
from datetime import datetime
from app.database.session import SessionLocal
from app.models.enums import SocialPlatform, JobStatus
from app.models.profile import Profile, ProfileSnapshot
from app.models.post import Post, PostSnapshot
from app.models.collection import CollectionJob
from app.schemas.collector import CollectorTarget
from app.collectors.facebook import FacebookPageCollector, FacebookParser
from app.collectors.browser import MockBrowserDriver
from app.collectors.registry import registry, CollectorRegistry
from app.collectors.exceptions import (
    TargetValidationError,
    PlatformNotSupportedError,
    ContentUnavailableError,
    RateLimitError,
)
from app.services.collection_service import CollectionService

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures", "facebook")


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


def test_facebook_target_validation_and_normalization():
    mock_driver = MockBrowserDriver()
    collector = FacebookPageCollector(browser_driver=mock_driver)

    # 1. Facebook URL validation
    t1 = CollectorTarget(platform=SocialPlatform.FACEBOOK, username="techinsider", profile_url="https://facebook.com/techinsider")
    assert collector.validate_target(t1) is True

    # 2. www normalization
    t2 = CollectorTarget(platform=SocialPlatform.FACEBOOK, username="techinsider", profile_url="https://www.facebook.com/techinsider")
    assert collector.validate_target(t2) is True

    # 3. Trailing slash normalization
    t3 = CollectorTarget(platform=SocialPlatform.FACEBOOK, username="techinsider", profile_url="https://www.facebook.com/techinsider/")
    assert collector.validate_target(t3) is True
    assert collector._normalize_profile_url(t3) == "https://www.facebook.com/techinsider/"

    # 4. Invalid Instagram URL rejection
    t4 = CollectorTarget(platform=SocialPlatform.FACEBOOK, username="techinsider", profile_url="https://instagram.com/techinsider")
    assert collector.validate_target(t4) is False

    # 5. Invalid X URL rejection
    t5 = CollectorTarget(platform=SocialPlatform.FACEBOOK, username="techinsider", profile_url="https://x.com/techinsider")
    assert collector.validate_target(t5) is False

    # 6. Supported Page target parsing (including dotted slugs like indianarmy.adgpi)
    t_dotted = CollectorTarget(platform=SocialPlatform.FACEBOOK, username="indianarmy.adgpi", profile_url="https://www.facebook.com/indianarmy.adgpi/")
    assert collector.validate_target(t_dotted) is True
    assert collector._normalize_profile_url(t_dotted) == "https://www.facebook.com/indianarmy.adgpi/"

    # 7. Personal profile and unsupported route rejection
    for bad_route in ["/profile.php?id=123", "/people/john-doe/123", "/groups/mygroup", "/events/123", "/marketplace/item/123", "/login", "/recover", "/settings"]:
        t_bad = CollectorTarget(platform=SocialPlatform.FACEBOOK, username="techinsider", profile_url=f"https://www.facebook.com{bad_route}")
        assert collector.validate_target(t_bad) is False


def test_facebook_page_parsing_from_fixture():
    html = load_fixture("public_page.html")
    profile = FacebookParser.parse_profile(html, "techinsider", "https://www.facebook.com/techinsider/")

    # 8. platform ID extraction
    assert profile.platform == SocialPlatform.FACEBOOK
    assert profile.platform_profile_id == "10987654321"

    # 9. page name parsing
    assert profile.display_name == "Tech Insider"

    # 10. username/slug parsing
    assert profile.username == "techinsider"

    # 11. description parsing
    assert "ultimate digital destination for tech news" in profile.bio

    # 12. profile image parsing
    assert profile.profile_image_url == "https://scontent.fcdn.net/v/t51.2885-19/fb_techinsider_avatar.jpg"

    # 13. verified status parsing
    assert profile.verified is True

    # 14. follower parsing
    assert profile.followers == 520000

    # 15. page likes parsing (stored in other_platform_metrics)
    assert profile.other_platform_metrics == {"page_likes": 450000}


def test_facebook_personal_profile_rejection_from_fixture():
    # 7. personal profile rejection during parsing
    personal_html = load_fixture("personal_profile.html")
    with pytest.raises(TargetValidationError):
        FacebookParser.parse_profile(personal_html, "johndoe", "https://www.facebook.com/johndoe/")


def test_facebook_post_parsing_from_fixture():
    html = load_fixture("public_page.html")
    posts = FacebookParser.parse_posts(html, "techinsider", "https://www.facebook.com/techinsider/", limit=10)

    # 17. public post parsing
    assert len(posts) == 3

    # 18. post ID parsing
    assert posts[0].platform_post_id == "pfbid0123456789"

    # 19. post URL parsing
    assert posts[0].url == "https://www.facebook.com/techinsider/posts/pfbid0123456789"

    # 20. post text parsing
    assert "solar energy technology" in posts[0].caption

    # 21. timestamp parsing
    assert isinstance(posts[0].posted_at, datetime)

    # 22. media type parsing
    assert posts[0].media_type == "IMAGE"
    assert posts[1].media_type == "VIDEO"
    assert posts[2].media_type == "TEXT"

    # 23. reactions/likes parsing
    assert posts[0].metrics.likes == 3200

    # 24. comments parsing
    assert posts[0].metrics.comments == 410

    # 25. shares parsing
    assert posts[0].metrics.shares == 185

    # 26. unavailable metrics -> None
    assert posts[0].metrics.views is None
    assert posts[0].metrics.engagement is None


def test_facebook_failure_modes_from_fixtures():
    # 27. login-wall handling
    login_html = load_fixture("login_wall.html")
    with pytest.raises(ContentUnavailableError):
        FacebookParser.parse_profile(login_html, "private_page", "https://www.facebook.com/private_page/")

    # 28. not-found handling
    not_found_html = load_fixture("not_found.html")
    with pytest.raises(ContentUnavailableError):
        FacebookParser.parse_profile(not_found_html, "missing_page", "https://www.facebook.com/missing_page/")

    # 29. rate-limit handling
    rate_limit_html = "<html><head><title>Too Many Requests</title></head><body>Rate limit exceeded</body></html>"
    with pytest.raises(RateLimitError):
        FacebookParser.parse_profile(rate_limit_html, "rl_page", "https://www.facebook.com/rl_page/")


def test_facebook_registry_behavior():
    # 30. registry behavior
    fb_collector = registry.get_collector(SocialPlatform.FACEBOOK)
    assert isinstance(fb_collector, FacebookPageCollector)

    supported = registry.list_supported_platforms()
    assert SocialPlatform.FACEBOOK in supported
    assert SocialPlatform.INSTAGRAM in supported
    assert SocialPlatform.X in supported


def test_facebook_collection_service_and_persistence(db):
    html = load_fixture("public_page.html")
    mock_driver = MockBrowserDriver(simulated_html=html)
    fb_collector = FacebookPageCollector(browser_driver=mock_driver)

    test_reg = CollectorRegistry()
    test_reg.register(SocialPlatform.FACEBOOK, fb_collector)
    service = CollectionService(registry=test_reg)

    uid = uuid.uuid4().hex[:8]
    slug = f"fb_page_{uid}"

    target = CollectorTarget(
        platform=SocialPlatform.FACEBOOK,
        username=slug,
        profile_url=f"https://www.facebook.com/{slug}/"
    )

    # 31. CollectionService integration
    job1 = service.execute_collection(db, target, post_limit=2)
    assert job1.status == JobStatus.SUCCESS
    assert job1.records_collected == 2

    # 32. PostgreSQL persistence
    profile = db.query(Profile).filter_by(platform=SocialPlatform.FACEBOOK, username=slug).first()
    assert profile is not None
    assert profile.display_name == "Tech Insider"

    snapshots1 = db.query(ProfileSnapshot).filter_by(profile_id=profile.id).all()
    assert len(snapshots1) == 1
    assert snapshots1[0].followers == 520000
    assert snapshots1[0].other_platform_metrics == {"page_likes": 450000}

    posts1 = db.query(Post).filter_by(profile_id=profile.id).all()
    assert len(posts1) == 2


def test_facebook_duplicate_prevention_and_historical_snapshots(db):
    html = load_fixture("public_page.html")
    mock_driver = MockBrowserDriver(simulated_html=html)
    fb_collector = FacebookPageCollector(browser_driver=mock_driver)

    test_reg = CollectorRegistry()
    test_reg.register(SocialPlatform.FACEBOOK, fb_collector)
    service = CollectionService(registry=test_reg)

    uid = uuid.uuid4().hex[:8]
    slug_base = f"ident_fb_{uid}"

    # Variant 1: standard URL
    t1 = CollectorTarget(
        platform=SocialPlatform.FACEBOOK,
        username=slug_base,
        profile_url=f"https://facebook.com/{slug_base}/"
    )
    job1 = service.execute_collection(db, t1, post_limit=2)
    assert job1.status == JobStatus.SUCCESS

    # Variant 2: www prefix
    t2 = CollectorTarget(
        platform=SocialPlatform.FACEBOOK,
        username=f"@{slug_base}",
        profile_url=f"https://www.facebook.com/{slug_base}"
    )
    job2 = service.execute_collection(db, t2, post_limit=2)
    assert job2.status == JobStatus.SUCCESS

    # Variant 3: uppercase slug
    t3 = CollectorTarget(
        platform=SocialPlatform.FACEBOOK,
        username=slug_base.upper(),
        profile_url=f"https://www.facebook.com/{slug_base.upper()}/"
    )
    job3 = service.execute_collection(db, t3, post_limit=2)
    assert job3.status == JobStatus.SUCCESS

    # 33. Repeated collection creates historical snapshots
    # 34. Repeated collection does NOT create duplicate Profile
    profiles = db.query(Profile).filter_by(platform=SocialPlatform.FACEBOOK, username=slug_base.lower()).all()
    assert len(profiles) == 1

    snapshots = db.query(ProfileSnapshot).filter_by(profile_id=profiles[0].id).all()
    assert len(snapshots) == 3

    # 35. Repeated collection does NOT create duplicate Post
    posts = db.query(Post).filter_by(profile_id=profiles[0].id).all()
    assert len(posts) == 2

    post_snapshots = db.query(PostSnapshot).filter_by(post_id=posts[0].id).all()
    assert len(post_snapshots) == 3


def test_facebook_new_page_experience_parsing():
    """Verify Page parsing for Facebook New Page Experience targets using app link app-deep-link meta tags."""
    npe_html = """<!DOCTYPE html>
<html>
<head>
    <title>ADGPI - Indian Army | Facebook</title>
    <meta property="og:title" content="ADGPI - Indian Army">
    <meta property="og:type" content="video.other">
    <meta property="og:description" content="ADGPI - Indian Army. 10,905,420 followers · 53,056 talking about this · 94,347 were here. The Official Indian Army Facebook Page">
    <meta property="al:android:url" content="fb://profile/100068806646502">
    <meta property="al:ios:url" content="fb://profile/100068806646502">
</head>
<body>
</body>
</html>"""

    profile = FacebookParser.parse_profile(npe_html, "indianarmy.adgpi", "https://www.facebook.com/indianarmy.adgpi/")
    assert profile.platform == SocialPlatform.FACEBOOK
    assert profile.username == "indianarmy.adgpi"
    assert profile.platform_profile_id == "100068806646502"
    assert profile.display_name == "ADGPI - Indian Army"
    assert profile.followers == 10905420
    assert profile.following is None
    assert profile.post_count is None


def test_facebook_modern_post_parsing():
    """Verify post parsing for modern Facebook Pages with pfbid permalinks, photo links, and script payloads."""
    modern_html = """<!DOCTYPE html>
<html>
<head><title>Virat Kohli - Home | Facebook</title></head>
<body>
    <a href="https://www.facebook.com/photo/?fbid=341873783971722&set=a.277218383770596" aria-label="View profile cover photo"></a>
    <a href="https://www.facebook.com/photo/?fbid=627780925381005&set=a.277218390437262" aria-label="Virat Kohli photo update"></a>
    <script type="application/json">
    {
        "post_id": "1652613199564434",
        "publish_time": 1790319459,
        "message": {"text": "A signature piece, made to be different. Wrogn"},
        "story_attachment_style": "video_autoplay",
        "pfbid": "pfbid02gHCgMdsMwiL65rtAbgE51ALHii8J3PQRJERSVzAkPopaGfYgzFGEGjzZfFKpBqZ2l"
    }
    </script>
</body>
</html>"""

    posts = FacebookParser.parse_posts(modern_html, "virat.kohli", "https://www.facebook.com/virat.kohli/", limit=10)
    assert len(posts) >= 3

    # Check pfbid or photo post extraction
    photo_post = next((p for p in posts if "341873783971722" in p.url), None)
    assert photo_post is not None
    assert photo_post.media_type == "IMAGE"
    assert photo_post.caption == "View profile cover photo"
    assert photo_post.posted_at is None  # Unobserved timestamp remains None

    # Check script payload post extraction
    script_post = next((p for p in posts if p.platform_post_id.startswith("pfbid") or p.platform_post_id == "1652613199564434"), None)
    assert script_post is not None
    assert isinstance(script_post.posted_at, datetime)
    assert "virat.kohli/posts/" in script_post.url


def test_facebook_interaction_metric_extraction():
    """Verify Facebook interaction metrics extraction (reactions, comments, shares, views) from script payloads."""
    payload_html = """<!DOCTYPE html>
<html>
<head><title>Virat Kohli - Home | Facebook</title></head>
<body>
    <script type="application/json">
    {
        "post_id": "1652613199564434",
        "publish_time": 1790319459,
        "message": {"text": "A signature piece, made to be different."},
        "reaction_count": {"count": 99267},
        "share_count": {"count": 237},
        "comments": {"total_count": 1685},
        "video_view_count": 588247
    }
    </script>
</body>
</html>"""

    posts = FacebookParser.parse_posts(payload_html, "virat.kohli", "https://www.facebook.com/virat.kohli/", limit=10)
    assert len(posts) == 1

    post = posts[0]
    assert post.platform_post_id == "1652613199564434"
    assert post.metrics.likes == 99267
    assert post.metrics.comments == 1685
    assert post.metrics.shares == 237
    assert post.metrics.views == 588247

    # Abbreviated metric parsing verification
    assert FacebookParser._parse_number("99K") == 99000
    assert FacebookParser._parse_number("1.2M") == 1200000
    assert FacebookParser._parse_number("237") == 237



