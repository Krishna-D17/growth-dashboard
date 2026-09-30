import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.database.session import SessionLocal, get_db
from app.models.enums import SocialPlatform, JobStatus
from app.models.profile import Profile, ProfileSnapshot
from app.models.collection import CollectionJob
from app.schemas.collector import CollectorTarget
from app.collectors.mock import MockCollector
from app.collectors.registry import registry, CollectorRegistry
from app.collectors.exceptions import RateLimitError
from app.services.collection_service import collection_service, CollectionService

client = TestClient(app)


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def test_health_check_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "socialscope-backend"}


def test_create_valid_instagram_profile(db):
    uid = uuid.uuid4().hex[:8]
    handle = f"api_ig_{uid}"

    payload = {
        "platform": "instagram",
        "target": handle
    }
    response = client.post("/api/profiles", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == handle
    assert data["platform"] == "instagram"
    assert data["profile_url"] == f"https://www.instagram.com/{handle}/"
    assert "id" in data


def test_create_valid_x_profile(db):
    uid = uuid.uuid4().hex[:8]
    handle = f"api_x_{uid}"

    payload = {
        "platform": "x",
        "target": f"@{handle}"
    }
    response = client.post("/api/profiles", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == handle
    assert data["platform"] == "x"
    assert data["profile_url"] == f"https://x.com/{handle}/"


def test_create_valid_facebook_page_profile(db):
    uid = uuid.uuid4().hex[:8]
    slug = f"api_fb_{uid}"

    payload = {
        "platform": "facebook",
        "target": f"https://www.facebook.com/{slug}"
    }
    response = client.post("/api/profiles", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == slug
    assert data["platform"] == "facebook"
    assert data["profile_url"] == f"https://www.facebook.com/{slug}/"


def test_create_profile_unsupported_platform():
    payload = {
        "platform": "linkedin",
        "target": "user"
    }
    response = client.post("/api/profiles", json=payload)
    assert response.status_code == 422


def test_create_profile_invalid_target():
    payload = {
        "platform": "x",
        "target": "https://x.com/home"
    }
    response = client.post("/api/profiles", json=payload)
    assert response.status_code == 400
    assert "invalid for platform" in response.json()["detail"]


def test_create_facebook_personal_profile_rejected():
    payload = {
        "platform": "facebook",
        "target": "https://www.facebook.com/profile.php?id=123"
    }
    response = client.post("/api/profiles", json=payload)
    assert response.status_code == 400


def test_create_duplicate_profile_rejected(db):
    uid = uuid.uuid4().hex[:8]
    handle = f"dup_api_{uid}"

    payload = {
        "platform": "instagram",
        "target": handle
    }
    r1 = client.post("/api/profiles", json=payload)
    assert r1.status_code == 201

    r2 = client.post("/api/profiles", json=payload)
    assert r2.status_code == 409
    assert "already monitored" in r2.json()["detail"]


def test_list_profiles_and_filtering(db):
    uid = uuid.uuid4().hex[:8]
    ig_handle = f"list_ig_{uid}"
    x_handle = f"list_x_{uid}"

    client.post("/api/profiles", json={"platform": "instagram", "target": ig_handle})
    client.post("/api/profiles", json={"platform": "x", "target": x_handle})

    # List all
    r_all = client.get("/api/profiles")
    assert r_all.status_code == 200
    profiles = r_all.json()
    assert len(profiles) >= 2

    # Filter by platform
    r_ig = client.get("/api/profiles?platform=instagram")
    assert r_ig.status_code == 200
    ig_profiles = r_ig.json()
    assert all(p["platform"] == "instagram" for p in ig_profiles)


def test_get_profile_by_id(db):
    uid = uuid.uuid4().hex[:8]
    handle = f"get_id_{uid}"

    r_create = client.post("/api/profiles", json={"platform": "instagram", "target": handle})
    profile_id = r_create.json()["id"]

    r_get = client.get(f"/api/profiles/{profile_id}")
    assert r_get.status_code == 200
    data = r_get.json()
    assert data["id"] == profile_id
    assert data["username"] == handle


def test_get_nonexistent_profile_returns_404():
    random_id = str(uuid.uuid4())
    r = client.get(f"/api/profiles/{random_id}")
    assert r.status_code == 404


def test_manual_collection_success_and_history(db, monkeypatch):
    uid = uuid.uuid4().hex[:8]
    handle = f"manual_coll_{uid}"

    r_create = client.post("/api/profiles", json={"platform": "instagram", "target": handle})
    profile_id = r_create.json()["id"]

    # Register MockCollector on collection_service registry for test determinism
    test_registry = CollectorRegistry()
    test_registry.register(SocialPlatform.INSTAGRAM, MockCollector(platform=SocialPlatform.INSTAGRAM))
    monkeypatch.setattr(collection_service, "registry", test_registry)

    # Trigger manual collection
    r_coll = client.post(f"/api/profiles/{profile_id}/collect?post_limit=2")
    assert r_coll.status_code == 200
    job_data = r_coll.json()
    assert job_data["profile_id"] == profile_id
    assert job_data["status"] == "success"
    assert job_data["records_collected"] == 2
    job_id = job_data["id"]

    # Get collection job by ID
    r_job = client.get(f"/api/collection-jobs/{job_id}")
    assert r_job.status_code == 200
    assert r_job.json()["id"] == job_id

    # Get collection job history for profile
    r_hist = client.get(f"/api/profiles/{profile_id}/collection-jobs")
    assert r_hist.status_code == 200
    hist = r_hist.json()
    assert len(hist) == 1
    assert hist[0]["id"] == job_id


def test_manual_collection_nonexistent_profile_returns_404():
    random_id = str(uuid.uuid4())
    r = client.post(f"/api/profiles/{random_id}/collect")
    assert r.status_code == 404


def test_get_nonexistent_collection_job_returns_404():
    random_id = str(uuid.uuid4())
    r = client.get(f"/api/collection-jobs/{random_id}")
    assert r.status_code == 404


def test_get_collection_history_nonexistent_profile_returns_404():
    random_id = str(uuid.uuid4())
    r = client.get(f"/api/profiles/{random_id}/collection-jobs")
    assert r.status_code == 404


def test_manual_collection_rate_limit_error(db, monkeypatch):
    uid = uuid.uuid4().hex[:8]
    handle = f"rl_api_{uid}"

    r_create = client.post("/api/profiles", json={"platform": "x", "target": handle})
    profile_id = r_create.json()["id"]

    class FailingCollector(MockCollector):
        def collect(self, target, post_limit=10):
            raise RateLimitError("Rate limit exceeded on test platform")

    test_registry = CollectorRegistry()
    test_registry.register(SocialPlatform.X, FailingCollector(platform=SocialPlatform.X))
    monkeypatch.setattr(collection_service, "registry", test_registry)

    r_coll = client.post(f"/api/profiles/{profile_id}/collect")
    assert r_coll.status_code == 429
    assert "Rate limit exceeded" in r_coll.json()["detail"]
