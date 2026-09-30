import io
import uuid
import pytest
import openpyxl
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.database.session import SessionLocal
from app.models.enums import SocialPlatform, CollectionSchedule, JobStatus
from app.models.profile import Profile, ProfileSnapshot
from app.models.post import Post, PostSnapshot
from app.models.collection import CollectionJob, CollectionError
from app.models.anomaly import Anomaly
from app.services.collection_service import collection_service
from app.collectors.registry import registry as collector_registry
from app.collectors.instagram import InstagramCollector
from app.collectors.browser.base import MockBrowserDriver
from app.collectors.exceptions import ContentUnavailableError, CollectorExecutionError
from app.scheduler.jobs import run_scheduled_collections
from app.ai.service import ai_service

client = TestClient(app)


@pytest.fixture
def db():
    session = SessionLocal()
    session.query(CollectionError).delete()
    session.query(CollectionJob).delete()
    session.query(PostSnapshot).delete()
    session.query(Post).delete()
    session.query(ProfileSnapshot).delete()
    session.query(Anomaly).delete()
    session.query(Profile).delete()
    session.commit()
    try:
        yield session
    finally:
        session.rollback()
        session.query(CollectionError).delete()
        session.query(CollectionJob).delete()
        session.query(PostSnapshot).delete()
        session.query(Post).delete()
        session.query(ProfileSnapshot).delete()
        session.query(Anomaly).delete()
        session.query(Profile).delete()
        session.commit()
        session.close()


def generate_mock_instagram_html(username="e2e_target", followers=15000, post_count=3):
    posts_html = ""
    for i in range(1, post_count + 1):
        posts_html += f"""
        <div class="post">
            <a href="/p/POST_E2E_{i}/">
                <img alt="E2E Post caption {i} #testing" />
            </a>
            <span>{100 * i} likes</span>
            <span>{10 * i} comments</span>
        </div>
        """

    return f"""
    <html>
        <head>
            <title>{username} (@{username}) • Instagram photos and videos</title>
            <meta property="og:title" content="{username} (@{username}) • Instagram photos" />
            <meta property="og:description" content="{followers:,} Followers, 450 Following, 100 Posts - See Instagram photos and videos from {username}" />
            <meta property="og:image" content="https://instagram.com/avatar.jpg" />
        </head>
        <body>
            <h1>{username}</h1>
            <span class="followers-count">{followers}</span>
            <div class="posts-grid">
                {posts_html}
            </div>
        </body>
    </html>
    """


# ==============================================================================
# 1. FULL END-TO-END PIPELINE TEST
# ==============================================================================
def test_full_e2e_collection_analytics_export_ai_flow(db):
    """
    Complete End-to-End integration test covering:
    Profile API -> CollectionService -> Registry -> Mock Driver -> Persistence -> Analytics -> Export -> AI Insights.
    """
    # 1. Create Profile via API
    create_res = client.post(
        "/api/profiles",
        json={
            "platform": "instagram",
            "target": "e2e_target_account",
            "collection_schedule": "daily"
        }
    )
    assert create_res.status_code == 201
    prof_data = create_res.json()
    profile_id = prof_data["id"]
    assert prof_data["username"] == "e2e_target_account"
    assert prof_data["collection_schedule"] == "daily"

    # 2. Trigger Collection using Mock Driver
    mock_html = generate_mock_instagram_html("e2e_target_account", followers=12000, post_count=2)
    mock_driver = MockBrowserDriver(simulated_html=mock_html)
    mock_collector = InstagramCollector(driver=mock_driver)

    with patch.object(collector_registry, "get_collector", return_value=mock_collector):
        job_res = client.post(f"/api/profiles/{profile_id}/collect?post_limit=10")
        assert job_res.status_code == 200
        job_data = job_res.json()
        assert job_data["status"] == "success"
        assert job_data["records_collected"] == 2

    # 3. Database Persistence Verification
    profile_db = db.query(Profile).filter_by(id=uuid.UUID(profile_id)).first()
    assert profile_db is not None
    assert len(profile_db.snapshots) == 1
    assert profile_db.snapshots[0].followers == 12000
    assert len(profile_db.posts) == 2
    assert len(profile_db.jobs) == 1

    # 4. Analytics Verification
    ov_res = client.get(f"/api/profiles/{profile_id}/analytics/overview")
    assert ov_res.status_code == 200
    ov_data = ov_res.json()
    assert ov_data["growth"]["current_followers"] == 12000
    assert ov_data["content"]["total_posts"] == len(profile_db.posts)

    # 5. Export Verification
    csv_res = client.get(f"/api/profiles/{profile_id}/export/profile?format=csv")
    assert csv_res.status_code == 200
    assert "text/csv" in csv_res.headers["content-type"]
    assert "e2e_target_account" in csv_res.text

    xlsx_res = client.get(f"/api/profiles/{profile_id}/export/report?format=xlsx")
    assert xlsx_res.status_code == 200
    wb = openpyxl.load_workbook(io.BytesIO(xlsx_res.content))
    assert "Profile" in wb.sheetnames
    assert wb["Profile"].cell(row=2, column=4).value == "e2e_target_account"

    # 6. AI Insights Verification
    ai_res = client.get(f"/api/profiles/{profile_id}/ai-insights")
    assert ai_res.status_code == 200
    ai_data = ai_res.json()
    assert "title" in ai_data
    assert "summary" in ai_data


# ==============================================================================
# 2. HISTORICAL COLLECTION & DUPLICATE PREVENTION
# ==============================================================================
def test_historical_collection_and_duplicate_prevention(db):
    """
    Executes collection twice for the same profile target.
    Verifies:
    - Profile entity is reused
    - Posts are reused (no duplicate post rows created)
    - New profile snapshots are appended (snapshot history preserved)
    - Collection jobs remain distinct
    """
    create_res = client.post(
        "/api/profiles",
        json={"platform": "instagram", "target": "duplicate_check_user"}
    )
    profile_id = create_res.json()["id"]

    # Run 1: 10,000 followers, 2 posts
    html1 = generate_mock_instagram_html("duplicate_check_user", followers=10000, post_count=2)
    c1 = InstagramCollector(driver=MockBrowserDriver(simulated_html=html1))
    with patch.object(collector_registry, "get_collector", return_value=c1):
        client.post(f"/api/profiles/{profile_id}/collect")

    # Run 2: 10,500 followers, same posts
    html2 = generate_mock_instagram_html("duplicate_check_user", followers=10500, post_count=2)
    c2 = InstagramCollector(driver=MockBrowserDriver(simulated_html=html2))
    with patch.object(collector_registry, "get_collector", return_value=c2):
        client.post(f"/api/profiles/{profile_id}/collect")

    profile_db = db.query(Profile).filter_by(id=uuid.UUID(profile_id)).first()
    assert profile_db is not None
    # Profile entity reused
    assert db.query(Profile).filter_by(username="duplicate_check_user").count() == 1
    # 2 distinct snapshot records
    assert len(profile_db.snapshots) == 2
    assert profile_db.snapshots[0].followers in [10000, 10500]
    # Duplicate post prevention: exact same 2 post entities reused
    assert len(profile_db.posts) == 2
    # Distinct collection jobs
    assert len(profile_db.jobs) == 2


# ==============================================================================
# 3. FAILURE PATH & ERROR PERSISTENCE
# ==============================================================================
def test_failure_path_isolation(db):
    """
    Simulates a login wall / scraping error during collection.
    Verifies:
    - CollectionJob marked as FAILED in database
    - CollectionError record persisted
    - API returns safe error status code
    - Application & database remain healthy
    """
    create_res = client.post(
        "/api/profiles",
        json={"platform": "instagram", "target": "failing_account"}
    )
    profile_id = create_res.json()["id"]

    # Mock failing collector raising ContentUnavailableError
    failing_collector = MagicMock()
    failing_collector.collect.side_effect = ContentUnavailableError("Login wall encountered.")

    with patch.object(collector_registry, "get_collector", return_value=failing_collector):
        res = client.post(f"/api/profiles/{profile_id}/collect")
        assert res.status_code in (400, 500)
        assert "login wall" in res.json()["detail"].lower()

    # Check database persistence of error
    job_db = db.query(CollectionJob).filter_by(profile_id=uuid.UUID(profile_id)).first()
    assert job_db is not None
    assert job_db.status == JobStatus.FAILED
    assert len(job_db.errors) > 0
    assert "login wall" in job_db.errors[0].message.lower()


# ==============================================================================
# 4. SCHEDULER INTEGRATION & OVERLAP PROTECTION
# ==============================================================================
def test_scheduler_overlap_protection_and_configs(db):
    """
    Verifies scheduler schedule updates and overlap protection.
    """
    p_res = client.post(
        "/api/profiles",
        json={"platform": "instagram", "target": "sched_user"}
    )
    profile_id = p_res.json()["id"]

    # Test schedule update
    sched_res = client.patch(
        f"/api/profiles/{profile_id}/schedule",
        json={"collection_schedule": "every_6_hours"}
    )
    assert sched_res.status_code == 200
    assert sched_res.json()["collection_schedule"] == "every_6_hours"

    # Test overlap protection: if job is already in RUNNING state, second trigger is skipped
    running_job = CollectionJob(
        profile_id=uuid.UUID(profile_id),
        platform=SocialPlatform.INSTAGRAM,
        started_at=datetime.now(timezone.utc),
        status=JobStatus.RUNNING,
        records_collected=0
    )
    db.add(running_job)
    db.commit()

    # Execute scheduled job run - should skip execution due to overlap guard
    run_scheduled_collections()

    # Verify no second running job was created
    jobs = db.query(CollectionJob).filter_by(profile_id=uuid.UUID(profile_id)).all()
    assert len(jobs) == 1


# ==============================================================================
# 5. API ERROR HANDLING & VALIDATION
# ==============================================================================
def test_api_error_handling_and_validations(db):
    """
    Verifies HTTP error responses for invalid inputs without stack trace exposure.
    """
    # Nonexistent profile 404
    fake_id = uuid.uuid4()
    assert client.get(f"/api/profiles/{fake_id}").status_code == 404
    assert client.get(f"/api/profiles/{fake_id}/analytics/overview").status_code == 404
    assert client.get(f"/api/profiles/{fake_id}/export/profile").status_code == 404
    assert client.get(f"/api/profiles/{fake_id}/ai-insights").status_code == 404

    # Invalid export format 422
    p = client.post("/api/profiles", json={"platform": "x", "target": "err_test"}).json()
    assert client.get(f"/api/profiles/{p['id']}/export/profile?format=invalid_fmt").status_code == 422

    # Invalid comparison profile request 422
    assert client.get("/api/profiles/invalid-uuid-str/analytics/growth").status_code == 422
