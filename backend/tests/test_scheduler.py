import uuid
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

from app.main import app
from app.database.session import get_db, SessionLocal
from app.models.enums import SocialPlatform, CollectionSchedule, JobStatus
from app.models.profile import Profile
from app.models.collection import CollectionJob, CollectionError
from app.schemas.collector import CollectorTarget
from app.scheduler.scheduler import start_scheduler, shutdown_scheduler, get_scheduler
from app.scheduler.jobs import run_scheduled_collections, is_profile_due, is_retryable_error
from app.collectors.exceptions import (
    CollectorExecutionError,
    TargetValidationError,
    ContentUnavailableError,
    RateLimitError,
)
from app.services.collection_service import CollectionService

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


# ---------------------------------------------------------
# 1. API & Validation Tests
# ---------------------------------------------------------

def test_schedule_validation_and_update(db):
    # Register mock profile
    profile = Profile(
        platform=SocialPlatform.INSTAGRAM,
        username="test_sched_user",
        profile_url="https://mock.com/test_sched_user",
        collection_schedule=CollectionSchedule.MANUAL
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)

    # 1. Verify GET exposes default manual schedule
    resp = client.get(f"/api/profiles/{profile.id}")
    assert resp.status_code == 200
    assert resp.json()["collection_schedule"] == "manual"
    assert resp.json()["last_collected_at"] is None

    # 2. Update schedule to every_6_hours
    patch_resp = client.patch(
        f"/api/profiles/{profile.id}/schedule",
        json={"collection_schedule": "every_6_hours"}
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["collection_schedule"] == "every_6_hours"

    # 3. Update schedule to every_12_hours
    patch_resp = client.patch(
        f"/api/profiles/{profile.id}/schedule",
        json={"collection_schedule": "every_12_hours"}
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["collection_schedule"] == "every_12_hours"

    # 4. Update schedule to daily
    patch_resp = client.patch(
        f"/api/profiles/{profile.id}/schedule",
        json={"collection_schedule": "daily"}
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["collection_schedule"] == "daily"

    # 5. Invalid schedule payload rejected
    invalid_resp = client.patch(
        f"/api/profiles/{profile.id}/schedule",
        json={"collection_schedule": "invalid_frequency_type"}
    )
    assert invalid_resp.status_code == 422


def test_update_nonexistent_profile_schedule():
    fake_id = uuid.uuid4()
    resp = client.patch(
        f"/api/profiles/{fake_id}/schedule",
        json={"collection_schedule": "daily"}
    )
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


# ---------------------------------------------------------
# 2. Schedule Due Logic Tests
# ---------------------------------------------------------

def test_is_profile_due_intervals():
    now = datetime.now(timezone.utc)
    profile = Profile(
        platform=SocialPlatform.INSTAGRAM,
        username="due_user",
        profile_url="https://mock.com/due_user",
        collection_schedule=CollectionSchedule.MANUAL
    )

    # Manual profiles are never due
    assert not is_profile_due(profile, now)

    # Every 6 hours schedule
    profile.collection_schedule = CollectionSchedule.EVERY_6_HOURS
    profile.last_collected_at = None
    assert is_profile_due(profile, now)  # Never collected before -> due

    profile.last_collected_at = now - timedelta(hours=5)
    assert not is_profile_due(profile, now)

    profile.last_collected_at = now - timedelta(hours=6, minutes=1)
    assert is_profile_due(profile, now)

    # Every 12 hours schedule
    profile.collection_schedule = CollectionSchedule.EVERY_12_HOURS
    profile.last_collected_at = now - timedelta(hours=11)
    assert not is_profile_due(profile, now)

    profile.last_collected_at = now - timedelta(hours=12, minutes=1)
    assert is_profile_due(profile, now)

    # Daily schedule
    profile.collection_schedule = CollectionSchedule.DAILY
    profile.last_collected_at = now - timedelta(hours=23)
    assert not is_profile_due(profile, now)

    profile.last_collected_at = now - timedelta(hours=24, minutes=1)
    assert is_profile_due(profile, now)


# ---------------------------------------------------------
# 3. Scheduler Registration & Lifespan
# ---------------------------------------------------------

def test_scheduler_lifecycle():
    sched = start_scheduler()
    assert sched is not None
    assert sched.running

    job = sched.get_job("scheduled_profile_collection_job")
    assert job is not None
    assert job.name == "Scheduled Social Media Profile Collection"

    shutdown_scheduler()
    assert not sched.running


# ---------------------------------------------------------
# 4. Job Execution & CollectionService Integration
# ---------------------------------------------------------

def test_run_scheduled_collections_manual_vs_scheduled(db):
    # Profile 1: Manual
    p_manual = Profile(
        platform=SocialPlatform.INSTAGRAM,
        username="manual_only",
        profile_url="https://mock.com/manual_only",
        collection_schedule=CollectionSchedule.MANUAL
    )
    # Profile 2: Scheduled (every_6_hours, never collected)
    p_scheduled = Profile(
        platform=SocialPlatform.INSTAGRAM,
        username="scheduled_user",
        profile_url="https://mock.com/scheduled_user",
        collection_schedule=CollectionSchedule.EVERY_6_HOURS
    )
    db.add_all([p_manual, p_scheduled])
    db.commit()

    mock_service = MagicMock(spec=CollectionService)

    collected_count = run_scheduled_collections(service=mock_service)

    assert collected_count == 1
    mock_service.execute_collection.assert_called_once()
    target_arg = mock_service.execute_collection.call_args[0][1]
    assert target_arg.username == "scheduled_user"


# ---------------------------------------------------------
# 5. Overlap Protection
# ---------------------------------------------------------

def test_run_scheduled_collections_overlap_protection(db):
    p_running = Profile(
        platform=SocialPlatform.INSTAGRAM,
        username="running_user",
        profile_url="https://mock.com/running_user",
        collection_schedule=CollectionSchedule.EVERY_6_HOURS
    )
    db.add(p_running)
    db.commit()
    db.refresh(p_running)

    # Active running job for this profile
    active_job = CollectionJob(
        profile_id=p_running.id,
        platform=SocialPlatform.INSTAGRAM,
        status=JobStatus.RUNNING,
        started_at=datetime.now(timezone.utc),
        records_collected=0
    )
    db.add(active_job)
    db.commit()

    mock_service = MagicMock(spec=CollectionService)

    collected_count = run_scheduled_collections(service=mock_service)

    assert collected_count == 0
    mock_service.execute_collection.assert_not_called()


# ---------------------------------------------------------
# 6. Failure Isolation
# ---------------------------------------------------------

def test_run_scheduled_collections_failure_isolation(db):
    p1 = Profile(
        platform=SocialPlatform.INSTAGRAM,
        username="failing_user",
        profile_url="https://mock.com/failing_user",
        collection_schedule=CollectionSchedule.EVERY_6_HOURS
    )
    p2 = Profile(
        platform=SocialPlatform.INSTAGRAM,
        username="succeeding_user",
        profile_url="https://mock.com/succeeding_user",
        collection_schedule=CollectionSchedule.EVERY_6_HOURS
    )
    db.add_all([p1, p2])
    db.commit()

    mock_service = MagicMock(spec=CollectionService)

    def side_effect(db, target, post_limit=10):
        if target.username == "failing_user":
            raise CollectorExecutionError("Isolated driver crash")
        return MagicMock()

    mock_service.execute_collection.side_effect = side_effect

    with patch("app.scheduler.jobs.time.sleep") as mock_sleep:
        collected_count = run_scheduled_collections(service=mock_service)

    # p1 fails (with retries), p2 succeeds -> total successful collected_count is 1
    assert collected_count == 1
    assert mock_service.execute_collection.call_count >= 2


# ---------------------------------------------------------
# 7. Bounded Retry Behavior
# ---------------------------------------------------------

def test_run_scheduled_collections_retry_transient_vs_permanent(db):
    # Test transient error classification
    assert is_retryable_error(CollectorExecutionError("timeout"))
    assert is_retryable_error(RateLimitError("rate limited"))
    assert not is_retryable_error(TargetValidationError("invalid format"))
    assert not is_retryable_error(ContentUnavailableError("profile private"))

    p_transient = Profile(
        platform=SocialPlatform.INSTAGRAM,
        username="transient_user",
        profile_url="https://mock.com/transient_user",
        collection_schedule=CollectionSchedule.EVERY_6_HOURS
    )
    db.add(p_transient)
    db.commit()

    mock_service = MagicMock(spec=CollectionService)
    mock_service.execute_collection.side_effect = RateLimitError("Rate limit exceeded")

    with patch("app.scheduler.jobs.settings.max_collection_retries", 2), \
         patch("app.scheduler.jobs.settings.retry_backoff_seconds", 1), \
         patch("app.scheduler.jobs.time.sleep") as mock_sleep:
        collected_count = run_scheduled_collections(service=mock_service)

    assert collected_count == 0
    # Initial attempt + 2 retries = 3 attempts total
    assert mock_service.execute_collection.call_count == 3
    assert mock_sleep.call_count == 2
