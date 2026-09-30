import os
import uuid
import pytest
from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.database.session import SessionLocal
from app.models.enums import SocialPlatform, JobStatus
from app.models.profile import Profile, ProfileSnapshot
from app.models.post import Post, PostSnapshot
from app.models.collection import CollectionJob, CollectionError
from app.schemas.collector import CollectorTarget
from app.collectors.browser import BaseBrowserDriver
from app.collectors.instagram import InstagramCollector
from app.collectors.x import XCollector
from app.collectors.facebook import FacebookPageCollector
from app.collectors.registry import CollectorRegistry
from app.services.collection_service import collection_service

client = TestClient(app)

FIXTURES_DIR = os.path.dirname(__file__)


def load_fixture(platform: str, filename: str) -> str:
    path = os.path.join(FIXTURES_DIR, "fixtures", platform, filename)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


class FixtureBrowserDriver(BaseBrowserDriver):
    """
    Test-only browser driver implementing BaseBrowserDriver interface contract.
    Returns saved deterministic HTML fixtures based on requested URL patterns
    without performing network requests or launching browser processes.
    """

    def __init__(self, custom_html: Optional[str] = None):
        self.custom_html = custom_html
        self.is_started = False

    def start(self) -> None:
        self.is_started = True

    def close(self) -> None:
        self.is_started = False

    def fetch_page_content(self, url: str, wait_for_selector: Optional[str] = None) -> str:
        if not self.is_started:
            self.start()

        if self.custom_html:
            return self.custom_html

        url_lower = url.lower()
        if "instagram.com" in url_lower:
            return load_fixture("instagram", "public_profile.html")
        elif "x.com" in url_lower or "twitter.com" in url_lower:
            return load_fixture("x", "public_profile.html")
        elif "facebook.com" in url_lower:
            return load_fixture("facebook", "public_page.html")

        return "<html><body><div id='content'>Generic Fixture Page</div></body></html>"

    def extract_json(self, url: str) -> Optional[dict]:
        return {"url": url, "mock": True}


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def create_test_registry(browser_driver: Optional[BaseBrowserDriver] = None) -> CollectorRegistry:
    driver = browser_driver or FixtureBrowserDriver()
    test_reg = CollectorRegistry()
    test_reg.register(SocialPlatform.INSTAGRAM, InstagramCollector(browser_driver=driver))
    test_reg.register(SocialPlatform.X, XCollector(browser_driver=driver))
    test_reg.register(SocialPlatform.FACEBOOK, FacebookPageCollector(browser_driver=driver))
    return test_reg


def test_instagram_end_to_end_pipeline(db, monkeypatch):
    """
    Verify complete Instagram pipeline:
    HTTP API -> Profile -> CollectionService -> CollectorRegistry -> InstagramCollector -> FixtureBrowser -> InstagramParser -> PostgreSQL
    """
    uid = uuid.uuid4().hex[:8]
    handle = f"e2e_ig_{uid}"

    # 1. POST /api/profiles
    r_create = client.post("/api/profiles", json={"platform": "instagram", "target": handle})
    assert r_create.status_code == 201
    profile_id = r_create.json()["id"]

    # Configure fixture-backed real collectors on CollectionService registry
    test_reg = create_test_registry()
    monkeypatch.setattr(collection_service, "registry", test_reg)

    # 2. POST /api/profiles/{id}/collect
    r_collect = client.post(f"/api/profiles/{profile_id}/collect?post_limit=2")
    assert r_collect.status_code == 200
    job_data = r_collect.json()

    assert job_data["profile_id"] == profile_id
    assert job_data["platform"] == "instagram"
    assert job_data["status"] == "success"
    assert job_data["records_collected"] == 2
    assert job_data["collector_version"] == "instagram-1.0.0"

    # 3. Direct PostgreSQL Verification
    profile = db.query(Profile).filter_by(id=profile_id).first()
    assert profile is not None
    assert profile.username == handle
    assert profile.display_name == "Tech Insider"
    assert profile.verified is True
    assert profile.platform_profile_id == f"ig_{handle}"

    snapshots = db.query(ProfileSnapshot).filter_by(profile_id=profile_id).all()
    assert len(snapshots) == 1
    assert snapshots[0].followers == 12500
    assert snapshots[0].following == 450
    assert snapshots[0].post_count == 88

    posts = db.query(Post).filter_by(profile_id=profile_id).all()
    assert len(posts) == 2

    # Instagram shares are non-public and MUST remain None
    post_snapshots = db.query(PostSnapshot).filter_by(post_id=posts[0].id).all()
    assert len(post_snapshots) == 1
    assert post_snapshots[0].shares is None


def test_x_end_to_end_pipeline(db, monkeypatch):
    """
    Verify complete X (Twitter) pipeline:
    HTTP API -> Profile -> CollectionService -> CollectorRegistry -> XCollector -> FixtureBrowser -> XParser -> PostgreSQL
    """
    uid = uuid.uuid4().hex[:8]
    handle = f"e2e_x_{uid}"

    # 1. POST /api/profiles
    r_create = client.post("/api/profiles", json={"platform": "x", "target": f"@{handle}"})
    assert r_create.status_code == 201
    profile_id = r_create.json()["id"]

    test_reg = create_test_registry()
    monkeypatch.setattr(collection_service, "registry", test_reg)

    # 2. POST /api/profiles/{id}/collect
    r_collect = client.post(f"/api/profiles/{profile_id}/collect?post_limit=2")
    assert r_collect.status_code == 200
    job_data = r_collect.json()

    assert job_data["profile_id"] == profile_id
    assert job_data["platform"] == "x"
    assert job_data["status"] == "success"
    assert job_data["records_collected"] == 2

    # 3. Direct PostgreSQL Verification
    profile = db.query(Profile).filter_by(id=profile_id).first()
    assert profile is not None
    assert profile.platform_profile_id == "123456789"

    snapshots = db.query(ProfileSnapshot).filter_by(profile_id=profile_id).all()
    assert len(snapshots) == 1
    assert snapshots[0].followers == 250500
    assert snapshots[0].following == 320

    posts = db.query(Post).filter_by(profile_id=profile_id).all()
    assert len(posts) == 2

    post_snapshots = db.query(PostSnapshot).filter_by(post_id=posts[0].id).all()
    assert len(post_snapshots) == 1
    assert post_snapshots[0].likes == 1450
    assert post_snapshots[0].comments == 85
    assert post_snapshots[0].shares == 320
    assert post_snapshots[0].views == 45200
    assert post_snapshots[0].engagement is None  # Unavailable engagement formula remains None


def test_facebook_page_end_to_end_pipeline(db, monkeypatch):
    """
    Verify complete Facebook Page pipeline:
    HTTP API -> Profile -> CollectionService -> CollectorRegistry -> FacebookPageCollector -> FixtureBrowser -> FacebookParser -> PostgreSQL
    """
    uid = uuid.uuid4().hex[:8]
    slug = f"e2e_fb_{uid}"

    # 1. POST /api/profiles
    r_create = client.post("/api/profiles", json={"platform": "facebook", "target": f"https://www.facebook.com/{slug}"})
    assert r_create.status_code == 201
    profile_id = r_create.json()["id"]

    test_reg = create_test_registry()
    monkeypatch.setattr(collection_service, "registry", test_reg)

    # 2. POST /api/profiles/{id}/collect
    r_collect = client.post(f"/api/profiles/{profile_id}/collect?post_limit=2")
    assert r_collect.status_code == 200
    job_data = r_collect.json()

    assert job_data["profile_id"] == profile_id
    assert job_data["platform"] == "facebook"
    assert job_data["status"] == "success"
    assert job_data["records_collected"] == 2

    # 3. Direct PostgreSQL Verification
    profile = db.query(Profile).filter_by(id=profile_id).first()
    assert profile is not None
    assert profile.platform_profile_id == "10987654321"

    snapshots = db.query(ProfileSnapshot).filter_by(profile_id=profile_id).all()
    assert len(snapshots) == 1
    assert snapshots[0].followers == 520000
    assert snapshots[0].other_platform_metrics == {"page_likes": 450000}

    posts = db.query(Post).filter_by(profile_id=profile_id).all()
    assert len(posts) == 2

    post1 = db.query(Post).filter_by(profile_id=profile_id, platform_post_id="pfbid0123456789").first()
    assert post1 is not None

    post_snapshots = db.query(PostSnapshot).filter_by(post_id=post1.id).all()
    assert len(post_snapshots) == 1
    assert post_snapshots[0].likes == 3200
    assert post_snapshots[0].comments == 410
    assert post_snapshots[0].shares == 185
    assert post_snapshots[0].views is None  # Unavailable views remain None


def test_historical_snapshot_preservation_across_runs(db, monkeypatch):
    """
    Verify historical snapshot principle:
    Repeated collection executions create NEW ProfileSnapshot and PostSnapshot rows
    without overwriting past historical observations.
    """
    uid = uuid.uuid4().hex[:8]
    handle = f"hist_e2e_{uid}"

    r_create = client.post("/api/profiles", json={"platform": "instagram", "target": handle})
    profile_id = r_create.json()["id"]

    test_reg = create_test_registry()
    monkeypatch.setattr(collection_service, "registry", test_reg)

    # Run Collection #1
    r_coll1 = client.post(f"/api/profiles/{profile_id}/collect?post_limit=2")
    assert r_coll1.status_code == 200

    # Run Collection #2
    r_coll2 = client.post(f"/api/profiles/{profile_id}/collect?post_limit=2")
    assert r_coll2.status_code == 200

    # Verify Profile identity remains unique (1 Profile record)
    profiles = db.query(Profile).filter_by(platform=SocialPlatform.INSTAGRAM, username=handle).all()
    assert len(profiles) == 1

    # Verify exactly 2 distinct ProfileSnapshot observations exist
    snapshots = db.query(ProfileSnapshot).filter_by(profile_id=profile_id).all()
    assert len(snapshots) == 2
    assert snapshots[0].id != snapshots[1].id

    # Verify Post identity remains unique (2 Post records)
    posts = db.query(Post).filter_by(profile_id=profile_id).all()
    assert len(posts) == 2

    # Verify PostSnapshot records appended (2 observations per post = 4 total)
    all_post_snapshots = db.query(PostSnapshot).join(Post).filter(Post.profile_id == profile_id).all()
    assert len(all_post_snapshots) == 4


def test_duplicate_prevention_entity_vs_observation(db, monkeypatch):
    """
    Verify that handle/URL target variations (techinsider, @techinsider, https://www.instagram.com/TECHINSIDER/)
    resolve to the exact same Profile entity while recording distinct snapshots and jobs.
    """
    uid = uuid.uuid4().hex[:8]
    handle_base = f"dup_e2e_{uid}"

    # Variant 1: bare handle
    r1 = client.post("/api/profiles", json={"platform": "instagram", "target": handle_base})
    assert r1.status_code == 201
    profile_id = r1.json()["id"]

    # Variant 2: duplicate creation attempt returns 409 Conflict
    r2 = client.post("/api/profiles", json={"platform": "instagram", "target": f"@{handle_base}"})
    assert r2.status_code == 409

    test_reg = create_test_registry()
    monkeypatch.setattr(collection_service, "registry", test_reg)

    # Collect via profile_id
    r_coll1 = client.post(f"/api/profiles/{profile_id}/collect?post_limit=1")
    assert r_coll1.status_code == 200

    r_coll2 = client.post(f"/api/profiles/{profile_id}/collect?post_limit=1")
    assert r_coll2.status_code == 200

    # Exactly 1 Profile entity
    profiles = db.query(Profile).filter_by(platform=SocialPlatform.INSTAGRAM, username=handle_base.lower()).all()
    assert len(profiles) == 1

    # Exactly 2 CollectionJobs
    jobs = db.query(CollectionJob).filter_by(profile_id=profile_id).all()
    assert len(jobs) == 2


def test_collection_error_handling_and_logging(db, monkeypatch):
    """
    Verify end-to-end failure handling:
    When a target returns a login wall or unavailable fixture, CollectionJob records FAILED status,
    CollectionError is persisted in PostgreSQL, and API returns appropriate HTTP error response.
    """
    uid = uuid.uuid4().hex[:8]
    handle = f"err_e2e_{uid}"

    r_create = client.post("/api/profiles", json={"platform": "instagram", "target": handle})
    profile_id = r_create.json()["id"]

    login_wall_html = load_fixture("instagram", "login_wall.html")
    driver = FixtureBrowserDriver(custom_html=login_wall_html)
    test_reg = create_test_registry(browser_driver=driver)
    monkeypatch.setattr(collection_service, "registry", test_reg)

    # Trigger collection on login wall
    r_coll = client.post(f"/api/profiles/{profile_id}/collect")
    assert r_coll.status_code == 400
    assert "login" in r_coll.json()["detail"].lower()

    # Verify CollectionJob status in DB is FAILED
    job = db.query(CollectionJob).filter_by(profile_id=profile_id).first()
    assert job is not None
    assert job.status == JobStatus.FAILED
    assert "login" in job.error_message.lower()

    # Verify CollectionError persisted
    errors = db.query(CollectionError).filter_by(collection_job_id=job.id).all()
    assert len(errors) == 1
    assert errors[0].error_type == "ContentUnavailableError"


def test_null_metric_rule_preservation(db, monkeypatch):
    """
    Verify the strict NULL metric rule:
    Unavailable metrics in source fixtures MUST remain None/NULL across collector, parser, service, database, and API.
    They must NEVER be converted to 0.
    """
    uid = uuid.uuid4().hex[:8]
    handle = f"null_m_{uid}"

    r_create = client.post("/api/profiles", json={"platform": "instagram", "target": handle})
    profile_id = r_create.json()["id"]

    test_reg = create_test_registry()
    monkeypatch.setattr(collection_service, "registry", test_reg)

    r_coll = client.post(f"/api/profiles/{profile_id}/collect?post_limit=1")
    assert r_coll.status_code == 200

    posts = db.query(Post).filter_by(profile_id=profile_id).all()
    post_snapshot = db.query(PostSnapshot).filter_by(post_id=posts[0].id).first()

    # Verify Instagram shares is strictly None (not 0)
    assert post_snapshot.shares is None
    assert post_snapshot.views is None
    assert post_snapshot.engagement is None


def test_api_database_consistency_check(db, monkeypatch):
    """
    Verify complete consistency between API responses and PostgreSQL database state.
    """
    uid = uuid.uuid4().hex[:8]
    handle = f"consist_{uid}"

    r_create = client.post("/api/profiles", json={"platform": "x", "target": handle})
    profile_id = r_create.json()["id"]

    test_reg = create_test_registry()
    monkeypatch.setattr(collection_service, "registry", test_reg)

    r_coll = client.post(f"/api/profiles/{profile_id}/collect?post_limit=2")
    assert r_coll.status_code == 200
    api_job = r_coll.json()

    db_job = db.query(CollectionJob).filter_by(id=api_job["id"]).first()
    assert db_job is not None
    assert str(db_job.id) == api_job["id"]
    assert str(db_job.profile_id) == api_job["profile_id"]
    assert db_job.platform.value == api_job["platform"]
    assert db_job.records_collected == api_job["records_collected"]
    assert db_job.status.value == api_job["status"]
