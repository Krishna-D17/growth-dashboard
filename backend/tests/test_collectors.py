import uuid
import pytest
from app.database.session import SessionLocal
from app.models.enums import SocialPlatform, JobStatus
from app.models.profile import Profile, ProfileSnapshot
from app.models.post import Post, PostSnapshot
from app.models.collection import CollectionJob, CollectionError
from app.schemas.collector import CollectorTarget
from app.collectors.mock import MockCollector
from app.collectors.instagram import InstagramCollector
from app.collectors.registry import CollectorRegistry, registry
from app.collectors.browser import BaseBrowserDriver, MockBrowserDriver, SeleniumBrowserDriver
from app.collectors.exceptions import (
    TargetValidationError,
    PlatformNotSupportedError,
    CollectorExecutionError,
    RateLimitError,
)
from app.services.collection_service import CollectionService


@pytest.fixture
def db():
    """Fixture providing a transactional database session for collector tests."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def test_collector_target_validation():
    target = CollectorTarget(
        platform=SocialPlatform.INSTAGRAM,
        username="valid_user",
        profile_url="https://instagram.com/valid_user"
    )
    collector = MockCollector(platform=SocialPlatform.INSTAGRAM)
    assert collector.validate_target(target) is True

    invalid_target = CollectorTarget(
        platform=SocialPlatform.INSTAGRAM,
        username="invalid_user",
        profile_url="https://instagram.com/invalid_user"
    )
    assert collector.validate_target(invalid_target) is False
    with pytest.raises(TargetValidationError):
        collector.collect(invalid_target)


def test_nullable_metrics_contract():
    """Verify that unavailable metrics remain None and are NOT converted to 0."""
    target = CollectorTarget(
        platform=SocialPlatform.X,
        username="null_metrics_user",
        profile_url="https://x.com/null_metrics_user"
    )
    collector = MockCollector(platform=SocialPlatform.X, simulate_null_metrics=True)
    result = collector.collect(target)

    assert result.profile.followers is None
    assert result.profile.following is None
    assert result.profile.post_count is None

    for post in result.posts:
        if post.metrics:
            assert post.metrics.likes is None
            assert post.metrics.comments is None


def test_unimplemented_real_platforms_raise_error():
    """Verify that Instagram, X, and Facebook are all registered on default global registry."""
    inst_collector = registry.get_collector(SocialPlatform.INSTAGRAM)
    assert isinstance(inst_collector, InstagramCollector)

    from app.collectors.x import XCollector
    x_collector = registry.get_collector(SocialPlatform.X)
    assert isinstance(x_collector, XCollector)

    from app.collectors.facebook import FacebookPageCollector
    fb_collector = registry.get_collector(SocialPlatform.FACEBOOK)
    assert isinstance(fb_collector, FacebookPageCollector)


def test_mock_collector_resolution_and_execution():
    """Verify that MockCollector can be resolved and executed when registered explicitly on a test registry."""
    test_registry = CollectorRegistry()
    mock_collector = MockCollector(platform=SocialPlatform.INSTAGRAM)
    test_registry.register(SocialPlatform.INSTAGRAM, mock_collector)

    resolved = test_registry.get_collector(SocialPlatform.INSTAGRAM)
    assert resolved == mock_collector

    target = CollectorTarget(
        platform=SocialPlatform.INSTAGRAM,
        username="mock_target",
        profile_url="https://instagram.com/mock_target"
    )
    result = resolved.collect(target)
    assert result.profile.username == "mock_target"
    assert len(result.posts) > 0


def test_collector_registry_behavior():
    custom_registry = CollectorRegistry()

    with pytest.raises(PlatformNotSupportedError):
        custom_registry.get_collector(SocialPlatform.INSTAGRAM)

    mock_inst = MockCollector(platform=SocialPlatform.INSTAGRAM)
    custom_registry.register(SocialPlatform.INSTAGRAM, mock_inst)

    retrieved = custom_registry.get_collector(SocialPlatform.INSTAGRAM)
    assert retrieved == mock_inst
    assert custom_registry.list_supported_platforms() == [SocialPlatform.INSTAGRAM]


def test_browser_driver_abstraction():
    driver = MockBrowserDriver(simulated_html="<div id='test'>Hello</div>")
    driver.start()
    content = driver.fetch_page_content("https://example.com/profile")
    assert "Hello" in content
    assert "https://example.com/profile" in content
    driver.close()
    assert driver.is_started is False


def test_selenium_browser_driver_contract():
    """Verify that SeleniumBrowserDriver implements BaseBrowserDriver contract."""
    driver = SeleniumBrowserDriver(headless=True)
    assert isinstance(driver, BaseBrowserDriver)
    assert driver.headless is True
    assert driver._is_started is False


def test_collection_service_success_pipeline(db):
    uid = uuid.uuid4().hex[:8]
    username = f"success_target_{uid}"

    target = CollectorTarget(
        platform=SocialPlatform.INSTAGRAM,
        username=username,
        profile_url=f"https://instagram.com/{username}"
    )

    custom_registry = CollectorRegistry()
    custom_registry.register(SocialPlatform.INSTAGRAM, MockCollector(platform=SocialPlatform.INSTAGRAM))

    service = CollectionService(registry=custom_registry)
    job = service.execute_collection(db, target, post_limit=2)

    assert job.status == JobStatus.SUCCESS
    assert job.records_collected == 2
    assert job.completed_at is not None

    # Verify Profile created
    profile = db.query(Profile).filter_by(platform=SocialPlatform.INSTAGRAM, username=username).first()
    assert profile is not None
    assert profile.verified is True

    # Verify ProfileSnapshot created
    snapshots = db.query(ProfileSnapshot).filter_by(profile_id=profile.id).all()
    assert len(snapshots) == 1
    assert snapshots[0].followers == 12500

    # Verify Posts and PostSnapshots created
    posts = db.query(Post).filter_by(profile_id=profile.id).all()
    assert len(posts) == 2
    post_snapshots = db.query(PostSnapshot).filter_by(post_id=posts[0].id).all()
    assert len(post_snapshots) == 1


def test_collection_service_failure_pipeline(db):
    uid = uuid.uuid4().hex[:8]
    username = f"fail_target_{uid}"

    target = CollectorTarget(
        platform=SocialPlatform.FACEBOOK,
        username=username,
        profile_url=f"https://facebook.com/{username}"
    )

    custom_registry = CollectorRegistry()
    custom_registry.register(SocialPlatform.FACEBOOK, MockCollector(platform=SocialPlatform.FACEBOOK, should_fail=True))

    service = CollectionService(registry=custom_registry)

    with pytest.raises(CollectorExecutionError):
        service.execute_collection(db, target)

    profile = db.query(Profile).filter_by(platform=SocialPlatform.FACEBOOK, username=username).first()
    assert profile is not None

    job = db.query(CollectionJob).filter_by(profile_id=profile.id).first()
    assert job is not None
    assert job.status == JobStatus.FAILED
    assert "failed as requested" in job.error_message

    errors = db.query(CollectionError).filter_by(collection_job_id=job.id).all()
    assert len(errors) == 1
    assert errors[0].error_type == "CollectorExecutionError"


def test_historical_snapshot_preservation(db):
    """Verify multiple collection runs preserve historical snapshots without overwriting."""
    uid = uuid.uuid4().hex[:8]
    username = f"preserve_target_{uid}"

    target = CollectorTarget(
        platform=SocialPlatform.X,
        username=username,
        profile_url=f"https://x.com/{username}"
    )

    custom_registry = CollectorRegistry()
    custom_registry.register(SocialPlatform.X, MockCollector(platform=SocialPlatform.X))
    service = CollectionService(registry=custom_registry)

    # Run collection 1
    job1 = service.execute_collection(db, target, post_limit=2)
    assert job1.status == JobStatus.SUCCESS

    # Run collection 2
    job2 = service.execute_collection(db, target, post_limit=2)
    assert job2.status == JobStatus.SUCCESS

    profile = db.query(Profile).filter_by(platform=SocialPlatform.X, username=username).first()
    snapshots = db.query(ProfileSnapshot).filter_by(profile_id=profile.id).all()

    # 2 separate snapshots preserved
    assert len(snapshots) == 2
    assert snapshots[0].id != snapshots[1].id


def test_selenium_driver_timeout_handling_and_cleanup():
    """Verify that navigation timeout in SeleniumBrowserDriver cleans up browser driver and raises RuntimeError."""
    from unittest.mock import MagicMock
    driver = SeleniumBrowserDriver(headless=True, timeout=1000)
    mock_chrome = MagicMock()
    mock_chrome.get.side_effect = Exception("timeout: Timed out receiving message from renderer: -0.012")
    mock_chrome.page_source = ""

    driver._driver = mock_chrome
    driver._is_started = True

    with pytest.raises(RuntimeError) as exc_info:
        driver.fetch_page_content("https://example.com/slow")

    assert "Selenium fetch_page_content failed" in str(exc_info.value)
    assert driver._driver is None
    assert driver._is_started is False
    mock_chrome.quit.assert_called_once()

