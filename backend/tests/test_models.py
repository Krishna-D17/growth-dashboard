import uuid
import pytest
from sqlalchemy.exc import IntegrityError
from app.database.session import SessionLocal
from app.models.enums import SocialPlatform, JobStatus
from app.models.profile import Profile, ProfileSnapshot
from app.models.post import Post, PostSnapshot
from app.models.collection import CollectionJob, CollectionError
from app.models.anomaly import Anomaly


@pytest.fixture
def db():
    """Fixture providing a transactional database session for tests."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def test_profile_creation_and_uniqueness(db):
    uid = uuid.uuid4().hex[:8]
    username = f"tech_insider_{uid}"

    profile = Profile(
        platform=SocialPlatform.INSTAGRAM,
        username=username,
        display_name="Tech Insider",
        profile_url=f"https://instagram.com/{username}",
        verified=True
    )
    db.add(profile)
    db.commit()

    assert profile.id is not None
    assert profile.platform == SocialPlatform.INSTAGRAM
    assert profile.verified is True

    # Test uniqueness constraint (platform + username)
    duplicate_profile = Profile(
        platform=SocialPlatform.INSTAGRAM,
        username=username,
        profile_url=f"https://instagram.com/{username}"
    )
    db.add(duplicate_profile)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_profile_snapshots(db):
    uid = uuid.uuid4().hex[:8]
    username = f"dev_journal_{uid}"

    profile = Profile(
        platform=SocialPlatform.X,
        username=username,
        profile_url=f"https://x.com/{username}"
    )
    db.add(profile)
    db.commit()

    # Create multiple historical snapshots
    s1 = ProfileSnapshot(
        profile_id=profile.id,
        followers=1000,
        following=200,
        post_count=50,
        other_platform_metrics={"likes_count": 5000}
    )
    s2 = ProfileSnapshot(
        profile_id=profile.id,
        followers=1050,
        following=205,
        post_count=52
    )
    db.add_all([s1, s2])
    db.commit()

    db.refresh(profile)
    assert len(profile.snapshots) == 2
    assert profile.snapshots[0].followers in (1000, 1050)
    assert profile.snapshots[0].collected_at is not None


def test_post_creation_and_snapshots(db):
    uid = uuid.uuid4().hex[:8]
    username = f"techbrand_{uid}"

    profile = Profile(
        platform=SocialPlatform.FACEBOOK,
        username=username,
        profile_url=f"https://facebook.com/{username}"
    )
    db.add(profile)
    db.commit()

    post = Post(
        profile_id=profile.id,
        platform_post_id=f"fb_post_{uid}",
        url=f"https://facebook.com/{username}/posts/1001",
        caption="Exciting release today!",
        media_type="video"
    )
    db.add(post)
    db.commit()

    # Test post uniqueness per profile
    dup_post = Post(
        profile_id=profile.id,
        platform_post_id=f"fb_post_{uid}",
        url=f"https://facebook.com/{username}/posts/1001"
    )
    db.add(dup_post)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()

    # Create post snapshots
    ps1 = PostSnapshot(post_id=post.id, likes=150, comments=20, shares=5)
    ps2 = PostSnapshot(post_id=post.id, likes=200, comments=30, shares=10, engagement=4.5)
    db.add_all([ps1, ps2])
    db.commit()

    db.refresh(post)
    assert len(post.snapshots) == 2
    assert post.snapshots[0].likes in (150, 200)


def test_collection_jobs_and_errors(db):
    uid = uuid.uuid4().hex[:8]
    username = f"job_profile_{uid}"

    profile = Profile(
        platform=SocialPlatform.INSTAGRAM,
        username=username,
        profile_url=f"https://instagram.com/{username}"
    )
    db.add(profile)
    db.commit()

    # Verify all job statuses
    for status in JobStatus:
        job = CollectionJob(
            profile_id=profile.id,
            platform=SocialPlatform.INSTAGRAM,
            status=status,
            records_collected=10 if status == JobStatus.SUCCESS else 0
        )
        db.add(job)
    db.commit()

    # Create an unfinished job with errors
    unfinished_job = CollectionJob(
        profile_id=profile.id,
        platform=SocialPlatform.INSTAGRAM,
        status=JobStatus.RUNNING,
        completed_at=None
    )
    db.add(unfinished_job)
    db.commit()
    assert unfinished_job.completed_at is None

    err = CollectionError(
        collection_job_id=unfinished_job.id,
        error_type="RATE_LIMIT",
        message="Rate limit hit on Instagram API",
        details={"retry_after": 60}
    )
    db.add(err)
    db.commit()

    db.refresh(unfinished_job)
    assert len(unfinished_job.errors) == 1
    assert unfinished_job.errors[0].error_type == "RATE_LIMIT"


def test_anomalies(db):
    uid = uuid.uuid4().hex[:8]
    username = f"anomaly_target_{uid}"

    profile = Profile(
        platform=SocialPlatform.X,
        username=username,
        profile_url=f"https://x.com/{username}"
    )
    db.add(profile)
    db.commit()

    anomaly = Anomaly(
        profile_id=profile.id,
        metric="follower_growth_spike",
        baseline={"mean": 10.0, "std_dev": 2.0},
        observed_value=150.0,
        severity="high",
        method="z_score",
        description="Unusual spike of 150 new followers in 1 hour"
    )
    db.add(anomaly)
    db.commit()

    db.refresh(profile)
    assert len(profile.anomalies) == 1
    assert profile.anomalies[0].observed_value == 150.0


def test_cascade_deletion(db):
    uid = uuid.uuid4().hex[:8]
    username = f"cascade_test_{uid}"

    profile = Profile(
        platform=SocialPlatform.INSTAGRAM,
        username=username,
        profile_url=f"https://instagram.com/{username}"
    )
    db.add(profile)
    db.commit()

    snapshot = ProfileSnapshot(profile_id=profile.id, followers=500)
    post = Post(profile_id=profile.id, platform_post_id=f"p1_{uid}", url=f"http://inst.com/p1_{uid}")
    job = CollectionJob(profile_id=profile.id, platform=SocialPlatform.INSTAGRAM, status=JobStatus.SUCCESS)
    anomaly = Anomaly(profile_id=profile.id, metric="spike", observed_value=10.0)

    db.add_all([snapshot, post, job, anomaly])
    db.commit()

    post_snapshot = PostSnapshot(post_id=post.id, likes=50)
    job_error = CollectionError(collection_job_id=job.id, error_type="ERR", message="fail")
    db.add_all([post_snapshot, job_error])
    db.commit()

    # Delete profile and verify cascading deletes
    db.delete(profile)
    db.commit()

    assert db.query(ProfileSnapshot).filter_by(profile_id=profile.id).count() == 0
    assert db.query(Post).filter_by(profile_id=profile.id).count() == 0
    assert db.query(PostSnapshot).filter_by(post_id=post.id).count() == 0
    assert db.query(CollectionJob).filter_by(profile_id=profile.id).count() == 0
    assert db.query(CollectionError).filter_by(collection_job_id=job.id).count() == 0
    assert db.query(Anomaly).filter_by(profile_id=profile.id).count() == 0
