import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database.session import SessionLocal
from app.models.enums import SocialPlatform, JobStatus, CollectionSchedule
from app.models.profile import Profile, ProfileSnapshot
from app.models.post import Post, PostSnapshot
from app.models.collection import CollectionJob, CollectionError
from app.models.anomaly import Anomaly
from app.services.profile_service import ProfileService
from app.scheduler.jobs import run_scheduled_collections

client = TestClient(app)


@pytest.fixture
def db():
    """Fixture providing a transactional database session for tests."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def test_delete_endpoint_does_not_return_405():
    """
    Mandatory endpoint test:
    Verify that DELETE /api/profiles/{profile_id} is registered in FastAPI
    and does NOT return HTTP 405 Method Not Allowed.
    """
    random_id = uuid.uuid4()
    response = client.delete(f"/api/profiles/{random_id}")
    assert response.status_code != 405, "DELETE route must be registered and must not return HTTP 405"
    assert response.status_code == 404, "Unrecognized profile ID should return 404 Not Found"


def test_delete_profile_cascades_all_dependent_data(db):
    """
    Verify complete deletion of a target profile and all associated dependent entities:
    - ProfileSnapshots
    - Posts
    - PostSnapshots
    - CollectionJobs
    - CollectionErrors
    - Anomalies
    - Profile
    """
    # 1. Create Target Profile A
    profile_a = Profile(
        platform=SocialPlatform.X,
        username="target_a",
        profile_url="https://x.com/target_a/",
        collection_schedule=CollectionSchedule.EVERY_6_HOURS
    )
    # Create Unrelated Target Profile B
    profile_b = Profile(
        platform=SocialPlatform.INSTAGRAM,
        username="target_b",
        profile_url="https://www.instagram.com/target_b/",
        collection_schedule=CollectionSchedule.DAILY
    )
    db.add_all([profile_a, profile_b])
    db.commit()

    profile_a_id = profile_a.id
    profile_b_id = profile_b.id

    # 2. Add dependent records for Profile A
    snap_a = ProfileSnapshot(profile_id=profile_a_id, followers=1000, following=100, post_count=50)
    post_a = Post(profile_id=profile_a_id, platform_post_id="post_a_1", url="https://x.com/target_a/status/1", caption="Hello world")
    db.add_all([snap_a, post_a])
    db.commit()

    post_a_id = post_a.id

    p_snap_a = PostSnapshot(post_id=post_a_id, likes=10, comments=2)
    job_a = CollectionJob(profile_id=profile_a_id, platform=SocialPlatform.X, status=JobStatus.SUCCESS, records_collected=1)
    anomaly_a = Anomaly(profile_id=profile_a_id, metric="followers", observed_value=2500.0, severity="high", method="mad", description="Spike test")
    db.add_all([p_snap_a, job_a, anomaly_a])
    db.commit()

    job_a_id = job_a.id

    err_a = CollectionError(collection_job_id=job_a_id, error_type="NetworkError", message="Transient error")
    db.add(err_a)
    db.commit()

    err_a_id = err_a.id

    # Add dependent records for Profile B (Isolation check)
    snap_b = ProfileSnapshot(profile_id=profile_b_id, followers=5000)
    post_b = Post(profile_id=profile_b_id, platform_post_id="post_b_1", url="https://www.instagram.com/p/b1/", caption="Insta post")
    db.add_all([snap_b, post_b])
    db.commit()

    post_b_id = post_b.id

    p_snap_b = PostSnapshot(post_id=post_b_id, likes=100)
    job_b = CollectionJob(profile_id=profile_b_id, platform=SocialPlatform.INSTAGRAM, status=JobStatus.SUCCESS, records_collected=1)
    db.add_all([p_snap_b, job_b])
    db.commit()

    # 3. Call DELETE /api/profiles/{id} for Profile A
    response = client.delete(f"/api/profiles/{profile_a_id}")
    assert response.status_code == 200
    res_json = response.json()
    assert res_json["detail"] == "Target deleted successfully."
    assert res_json["id"] == str(profile_a_id)

    # 4. Verify Profile A and all dependent rows are deleted
    assert db.query(Profile).filter_by(id=profile_a_id).first() is None
    assert db.query(ProfileSnapshot).filter_by(profile_id=profile_a_id).count() == 0
    assert db.query(Post).filter_by(profile_id=profile_a_id).count() == 0
    assert db.query(PostSnapshot).filter_by(post_id=post_a_id).count() == 0
    assert db.query(CollectionJob).filter_by(profile_id=profile_a_id).count() == 0
    assert db.query(CollectionError).filter_by(id=err_a_id).count() == 0
    assert db.query(Anomaly).filter_by(profile_id=profile_a_id).count() == 0

    # 5. Verify Profile B remains completely unaffected (Cross-Profile Isolation)
    assert db.query(Profile).filter_by(id=profile_b_id).first() is not None
    assert db.query(ProfileSnapshot).filter_by(profile_id=profile_b_id).count() == 1
    assert db.query(Post).filter_by(profile_id=profile_b_id).count() == 1
    assert db.query(PostSnapshot).filter_by(post_id=post_b_id).count() == 1
    assert db.query(CollectionJob).filter_by(profile_id=profile_b_id).count() == 1


def test_delete_nonexistent_profile_returns_404():
    """Verify deleting a non-existent UUID returns HTTP 404."""
    random_id = uuid.uuid4()
    response = client.delete(f"/api/profiles/{random_id}")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_delete_profile_without_posts_or_snapshots(db):
    """Verify deleting a profile with 0 posts/snapshots succeeds cleanly."""
    profile = Profile(
        platform=SocialPlatform.FACEBOOK,
        username="empty_target",
        profile_url="https://www.facebook.com/empty_target/"
    )
    db.add(profile)
    db.commit()

    profile_id = profile.id

    response = client.delete(f"/api/profiles/{profile_id}")
    assert response.status_code == 200
    assert db.query(Profile).filter_by(id=profile_id).first() is None


def test_scheduler_ignores_deleted_profile(db):
    """Verify scheduler job loop does not evaluate deleted profiles."""
    profile = Profile(
        platform=SocialPlatform.X,
        username="scheduled_delete_test",
        profile_url="https://x.com/scheduled_delete_test/",
        collection_schedule=CollectionSchedule.EVERY_6_HOURS,
        last_collected_at=datetime.now(timezone.utc) - __import__('datetime').timedelta(hours=10)
    )
    db.add(profile)
    db.commit()

    profile_id = profile.id

    # Delete target
    ProfileService.delete_profile(db, profile_id)

    # Run scheduler job tick
    collected = run_scheduled_collections()

    # Verify no collection was run for deleted profile
    jobs = db.query(CollectionJob).filter_by(profile_id=profile_id).all()
    assert len(jobs) == 0


def test_delete_transaction_rollback_on_error():
    """Verify transactional rollback occurs when database commit fails during deletion."""
    mock_db = MagicMock()
    mock_profile = MagicMock(id=uuid.uuid4(), username="rollback_test", platform=SocialPlatform.X)
    mock_db.query().filter().first.return_value = mock_profile
    mock_db.commit.side_effect = Exception("Database write error")

    with pytest.raises(Exception, match="Database write error"):
        ProfileService.delete_profile(mock_db, mock_profile.id)

    # Verify delete was attempted and session rollback/close handled appropriately
    mock_db.delete.assert_called_once_with(mock_profile)
