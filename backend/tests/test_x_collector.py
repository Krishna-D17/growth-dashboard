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
from app.collectors.x import XCollector, XParser
from app.collectors.browser import MockBrowserDriver
from app.collectors.registry import registry, CollectorRegistry
from app.collectors.exceptions import (
    TargetValidationError,
    PlatformNotSupportedError,
    ContentUnavailableError,
    RateLimitError,
)
from app.services.collection_service import CollectionService

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures", "x")


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


def test_x_target_validation_and_normalization():
    mock_driver = MockBrowserDriver()
    collector = XCollector(browser_driver=mock_driver)

    # 1. Bare username
    t1 = CollectorTarget(platform=SocialPlatform.X, username="krishna", profile_url="https://x.com/krishna/")
    assert collector.validate_target(t1) is True

    # 2. @username
    t2 = CollectorTarget(platform=SocialPlatform.X, username="@krishna", profile_url="https://x.com/krishna")
    assert collector.validate_target(t2) is True

    # 3. x.com URL
    t3 = CollectorTarget(platform=SocialPlatform.X, username="krishna", profile_url="https://x.com/krishna")
    assert collector.validate_target(t3) is True

    # 4. twitter.com URL
    t4 = CollectorTarget(platform=SocialPlatform.X, username="krishna", profile_url="https://twitter.com/krishna")
    assert collector.validate_target(t4) is True

    # 5. Trailing slash normalization
    assert collector._normalize_profile_url(t1) == "https://x.com/krishna/"
    assert collector._normalize_profile_url(t4) == "https://x.com/krishna/"

    # 6. Case normalization
    t6 = CollectorTarget(platform=SocialPlatform.X, username="@Krishna", profile_url="https://x.com/Krishna/")
    assert collector.validate_target(t6) is True
    assert collector._normalize_profile_url(t6) == "https://x.com/krishna/"

    # 7. Invalid Instagram URL rejection
    t7 = CollectorTarget(platform=SocialPlatform.X, username="krishna", profile_url="https://instagram.com/krishna")
    assert collector.validate_target(t7) is False

    # 8. Invalid Facebook URL rejection
    t8 = CollectorTarget(platform=SocialPlatform.X, username="krishna", profile_url="https://facebook.com/krishna")
    assert collector.validate_target(t8) is False

    # 9. Invalid X route rejection
    for route in ["/home", "/explore", "/search", "/i/flow/login", "/settings", "/notifications", "/messages"]:
        t_bad = CollectorTarget(platform=SocialPlatform.X, username="krishna", profile_url=f"https://x.com{route}")
        assert collector.validate_target(t_bad) is False


def test_x_profile_parsing_from_fixture():
    html = load_fixture("public_profile.html")
    profile = XParser.parse_profile(html, "techinsider", "https://x.com/techinsider/")

    # 10. profile parsing
    assert profile.platform == SocialPlatform.X
    assert profile.username == "techinsider"
    assert profile.profile_url == "https://x.com/techinsider/"

    # 11. platform profile ID behavior (genuine numeric ID, never fake UUID)
    assert profile.platform_profile_id == "123456789"

    # 12. display name parsing
    assert profile.display_name == "Tech Insider"

    # 13. bio parsing
    assert "ultimate source for tech news" in profile.bio

    # 14. follower parsing
    assert profile.followers == 250500

    # 15. following parsing
    assert profile.following == 320

    # 16. verified parsing
    assert profile.verified is True
    assert profile.post_count == 15200
    assert profile.profile_image_url == "https://pbs.twimg.com/profile_images/techinsider_avatar.jpg"


def test_x_post_parsing_from_fixture():
    html = load_fixture("public_profile.html")
    posts = XParser.parse_posts(html, "techinsider", "https://x.com/techinsider/", limit=10)

    # 17. post parsing
    assert len(posts) == 3

    # 18. post ID parsing
    assert posts[0].platform_post_id == "1834567890123456789"

    # 19. post URL parsing
    assert posts[0].url == "https://x.com/techinsider/status/1834567890123456789"

    # 20. post text parsing
    assert "quantum computing" in posts[0].caption

    # 21. timestamp parsing
    assert isinstance(posts[0].posted_at, datetime)

    # 22. media type parsing
    assert posts[0].media_type == "IMAGE"
    assert posts[1].media_type == "VIDEO"
    assert posts[2].media_type == "TEXT"

    # 23. likes parsing
    assert posts[0].metrics.likes == 1450

    # 24. replies/comments parsing
    assert posts[0].metrics.comments == 85

    # 25. repost/shares parsing
    assert posts[0].metrics.shares == 320

    # 26. views parsing
    assert posts[0].metrics.views == 45200

    # 27. unavailable metrics -> None
    assert posts[0].metrics.engagement is None


def test_x_failure_modes_from_fixtures():
    # 28. login-wall handling
    login_html = load_fixture("login_wall.html")
    with pytest.raises(ContentUnavailableError):
        XParser.parse_profile(login_html, "private_user", "https://x.com/private_user/")

    # 29. not-found handling
    not_found_html = load_fixture("not_found.html")
    with pytest.raises(ContentUnavailableError):
        XParser.parse_profile(not_found_html, "missing_user", "https://x.com/missing_user/")

    # 30. rate-limit handling
    rate_limit_html = "<html><head><title>Rate limit exceeded</title></head><body>Too many requests</body></html>"
    with pytest.raises(RateLimitError):
        XParser.parse_profile(rate_limit_html, "rl_user", "https://x.com/rl_user/")


def test_x_registry_behavior():
    # 31. registry behavior
    x_collector = registry.get_collector(SocialPlatform.X)
    assert isinstance(x_collector, XCollector)

    supported = registry.list_supported_platforms()
    assert SocialPlatform.X in supported
    assert SocialPlatform.INSTAGRAM in supported
    assert SocialPlatform.FACEBOOK in supported


def test_x_collection_service_and_persistence(db):
    html = load_fixture("public_profile.html")
    mock_driver = MockBrowserDriver(simulated_html=html)
    x_collector = XCollector(browser_driver=mock_driver)

    test_reg = CollectorRegistry()
    test_reg.register(SocialPlatform.X, x_collector)
    service = CollectionService(registry=test_reg)

    uid = uuid.uuid4().hex[:8]
    handle = f"x_user_{uid}"

    target = CollectorTarget(
        platform=SocialPlatform.X,
        username=handle,
        profile_url=f"https://x.com/{handle}/"
    )

    # 32. CollectionService integration
    job1 = service.execute_collection(db, target, post_limit=2)
    assert job1.status == JobStatus.SUCCESS
    assert job1.records_collected == 2

    # 33. PostgreSQL persistence
    profile = db.query(Profile).filter_by(platform=SocialPlatform.X, username=handle).first()
    assert profile is not None
    assert profile.display_name == "Tech Insider"

    snapshots1 = db.query(ProfileSnapshot).filter_by(profile_id=profile.id).all()
    assert len(snapshots1) == 1
    assert snapshots1[0].followers == 250500

    posts1 = db.query(Post).filter_by(profile_id=profile.id).all()
    assert len(posts1) == 2


def test_x_duplicate_prevention_and_historical_snapshots(db):
    html = load_fixture("public_profile.html")
    mock_driver = MockBrowserDriver(simulated_html=html)
    x_collector = XCollector(browser_driver=mock_driver)

    test_reg = CollectorRegistry()
    test_reg.register(SocialPlatform.X, x_collector)
    service = CollectionService(registry=test_reg)

    uid = uuid.uuid4().hex[:8]
    handle_base = f"ident_x_{uid}"

    # Variant 1: bare username
    t1 = CollectorTarget(
        platform=SocialPlatform.X,
        username=handle_base,
        profile_url=f"https://x.com/{handle_base}/"
    )
    job1 = service.execute_collection(db, t1, post_limit=2)
    assert job1.status == JobStatus.SUCCESS

    # Variant 2: prefixed with @
    t2 = CollectorTarget(
        platform=SocialPlatform.X,
        username=f"@{handle_base}",
        profile_url=f"https://twitter.com/{handle_base}"
    )
    job2 = service.execute_collection(db, t2, post_limit=2)
    assert job2.status == JobStatus.SUCCESS

    # Variant 3: uppercase variation
    t3 = CollectorTarget(
        platform=SocialPlatform.X,
        username=handle_base.upper(),
        profile_url=f"https://x.com/{handle_base.upper()}/"
    )
    job3 = service.execute_collection(db, t3, post_limit=2)
    assert job3.status == JobStatus.SUCCESS

    # 34. Repeated collection creates historical snapshots
    # 35. Repeated collection does NOT create duplicate Profile
    profiles = db.query(Profile).filter_by(platform=SocialPlatform.X, username=handle_base.lower()).all()
    assert len(profiles) == 1

    snapshots = db.query(ProfileSnapshot).filter_by(profile_id=profiles[0].id).all()
    assert len(snapshots) == 3

    # 36. Repeated collection does NOT create duplicate Post (upserts posts and adds PostSnapshots)
    posts = db.query(Post).filter_by(profile_id=profiles[0].id).all()
    assert len(posts) == 2  # exactly 2 distinct posts

    post_snapshots = db.query(PostSnapshot).filter_by(post_id=posts[0].id).all()
    assert len(post_snapshots) == 3  # 3 observations over time


def test_x_number_normalization_cases():
    assert XParser._parse_number("400") == 400
    assert XParser._parse_number("1.2K") == 1200
    assert XParser._parse_number("21K") == 21000
    assert XParser._parse_number("1M") == 1000000
    assert XParser._parse_number("1.5M") == 1500000
    assert XParser._parse_number("2B") == 2000000000
    assert XParser._parse_number("1,234") == 1234
    assert XParser._parse_number("12,345") == 12345
    assert XParser._parse_number("123,456") == 123456
    assert XParser._parse_number("12.5K") == 12500
    assert XParser._parse_number("400400") == 400
    assert XParser._parse_number("379379") == 379
    assert XParser._parse_number(None) is None
    assert XParser._parse_number("") is None


def test_x_semantic_metric_extraction_and_deduplication():
    html = """
    <html>
    <body>
        <article data-post-id="2091050709248791002">
            <div data-testid="tweetText">Known test tweet with duplicate DOM nodes</div>
            <time datetime="2026-08-22T06:31:53.000Z">Aug 22, 2026</time>
            <a href="/imvkohli/status/2091050709248791002">Permalink</a>
            <div role="group">
                <!-- Reply button with duplicate DOM text nodes -->
                <button aria-label="400 Replies. Reply" data-testid="reply">
                    <div dir="ltr"><span dir="ltr">400</span><span dir="ltr">400</span></div>
                </button>
                <!-- Repost button -->
                <button aria-label="1.2K Reposts. Repost" data-testid="retweet">
                    <div dir="ltr"><span dir="ltr">1.2K</span></div>
                </button>
                <!-- Like button -->
                <button aria-label="21K Likes. Like" data-testid="like">
                    <div dir="ltr"><span dir="ltr">21K</span></div>
                </button>
                <!-- Views link -->
                <a aria-label="1M Views. View post analytics" data-testid="views">
                    <div dir="ltr"><span dir="ltr">1M</span></div>
                </a>
                <!-- Bookmarks button (not mapped to metrics) -->
                <button aria-label="142 Bookmarks" data-testid="bookmark">
                    <div dir="ltr"><span dir="ltr">142</span></div>
                </button>
            </div>
        </article>
    </body>
    </html>
    """
    posts = XParser.parse_posts(html, "imvkohli", "https://x.com/imvkohli/")
    assert len(posts) == 1
    m = posts[0].metrics
    assert m.comments == 400
    assert m.shares == 1200
    assert m.likes == 21000
    assert m.views == 1000000
    assert m.engagement is None


def test_x_likes_variations():
    like_samples = [
        ("400", 400),
        ("1.2K", 1200),
        ("21K", 21000),
        ("16K", 16000),
        ("14K", 14000),
        ("123", 123),
        ("1,234", 1234),
        ("12.5K", 12500),
        ("1M", 1000000),
    ]

    for raw_str, expected in like_samples:
        html = f"""
        <html><body>
            <article data-post-id="100001">
                <div role="group">
                    <button aria-label="{raw_str} Likes. Like" data-testid="like">
                        <span>{raw_str}</span>
                    </button>
                </div>
            </article>
        </body></html>
        """
        posts = XParser.parse_posts(html, "user", "https://x.com/user/")
        assert posts[0].metrics.likes == expected


def test_x_missing_metrics_returns_none():
    html = """
    <html><body>
        <article data-post-id="100002">
            <div data-testid="tweetText">Tweet without metric elements</div>
        </article>
    </body></html>
    """
    posts = XParser.parse_posts(html, "user", "https://x.com/user/")
    assert len(posts) == 1
    m = posts[0].metrics
    assert m.likes is None
    assert m.comments is None
    assert m.shares is None
    assert m.views is None

