import uuid
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

from app.main import app
from app.database.session import SessionLocal
from app.models.enums import SocialPlatform
from app.models.profile import Profile, ProfileSnapshot
from app.models.post import Post, PostSnapshot
from app.models.anomaly import Anomaly
from app.models.collection import CollectionJob, CollectionError
from app.ai.schemas import AIAnalyticsContext, AIInsight, AIObservation
from app.ai.providers import MockAIProvider, OpenAIProvider
from app.ai.service import ai_service

client = TestClient(app)


def _clean_db(session):
    test_profiles = session.query(Profile).filter(
        (Profile.username.like("%user%")) | (Profile.username.like("%ai_%"))
    ).all()
    for p in test_profiles:
        session.delete(p)


@pytest.fixture
def db():
    session = SessionLocal()
    _clean_db(session)
    session.commit()
    try:
        yield session
    finally:
        session.rollback()
        _clean_db(session)
        session.commit()
        session.close()


def create_ai_test_data(db, username="ai_test_user"):
    now = datetime.now(timezone.utc)
    profile = Profile(
        platform=SocialPlatform.INSTAGRAM,
        username=username,
        display_name="AI Test User",
        profile_url=f"https://instagram.com/{username}",
        verified=True
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)

    # Snapshots
    s1 = ProfileSnapshot(
        profile_id=profile.id,
        collected_at=now - timedelta(days=14),
        followers=5000,
        following=300,
        post_count=20
    )
    s2 = ProfileSnapshot(
        profile_id=profile.id,
        collected_at=now - timedelta(days=6),
        followers=5400,
        following=310,
        post_count=22
    )
    db.add_all([s1, s2])

    p1 = Post(
        profile_id=profile.id,
        platform_post_id="post_ai_1",
        url="https://instagram.com/p/post_ai_1",
        posted_at=now - timedelta(days=3),
        media_type="IMAGE"
    )
    db.add(p1)
    db.commit()
    db.refresh(p1)

    ps1 = PostSnapshot(
        post_id=p1.id,
        collected_at=now - timedelta(days=3),
        likes=250,
        comments=30,
        shares=None,
        views=None,
        engagement=280.0
    )
    db.add(ps1)
    db.commit()

    return profile


def test_ai_endpoint_returns_valid_structured_insight(db):
    profile = create_ai_test_data(db, "valid_ai_user")
    res = client.get(f"/api/profiles/{profile.id}/ai-insights")
    assert res.status_code == 200
    data = res.json()
    assert "title" in data
    assert "summary" in data
    assert "observations" in data
    assert isinstance(data["observations"], list)
    assert len(data["observations"]) > 0
    assert "data_points" in data
    assert data["provider"] == "mock"


def test_ai_provider_receives_structured_analytics_context(db):
    profile = create_ai_test_data(db, "context_user")
    context = ai_service.build_context(db, profile.id, days=7)
    
    assert context.profile["username"] == "context_user"
    assert context.profile["platform"] == "instagram"
    assert context.growth["current_followers"] == 5400
    assert context.engagement["average_engagement"] == 280.0
    assert "cookie" not in str(context.model_dump()).lower()
    assert "password" not in str(context.model_dump()).lower()
    assert "secret" not in str(context.model_dump()).lower()


def test_null_analytics_remain_null_in_ai_context(db):
    profile = create_ai_test_data(db, "null_ai_user")
    context = ai_service.build_context(db, profile.id)
    assert context.engagement["total_shares"] is None
    assert context.engagement["total_views"] is None


def test_unconfigured_openai_provider_raises_error():
    provider = OpenAIProvider(api_key="")
    assert provider.is_configured() is False
    with pytest.raises(RuntimeError) as exc:
        provider.generate_insight(MagicMock())
    assert "missing" in str(exc.value).lower()


def test_unconfigured_ai_service_returns_503(db):
    profile = create_ai_test_data(db, "unconfig_user")
    mock_unconfig_provider = MagicMock()
    mock_unconfig_provider.is_configured.return_value = False

    with patch.object(ai_service, "get_provider", return_value=mock_unconfig_provider):
        res = client.get(f"/api/profiles/{profile.id}/ai-insights")
        assert res.status_code == 503
        assert "not configured" in res.json()["detail"].lower()


def test_nonexistent_profile_ai_insights_returns_404(db):
    fake_id = uuid.uuid4()
    res = client.get(f"/api/profiles/{fake_id}/ai-insights")
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()


def test_ai_insights_days_parameter(db):
    profile = create_ai_test_data(db, "days_user")
    res7 = client.get(f"/api/profiles/{profile.id}/ai-insights?days=7")
    assert res7.status_code == 200

    res30 = client.get(f"/api/profiles/{profile.id}/ai-insights?days=30")
    assert res30.status_code == 200


def test_ai_failure_does_not_affect_deterministic_analytics(db):
    profile = create_ai_test_data(db, "robust_user")
    
    # Mock AI failure
    mock_failing_provider = MagicMock()
    mock_failing_provider.is_configured.return_value = True
    mock_failing_provider.generate_insight.side_effect = RuntimeError("LLM output validation error.")

    with patch.object(ai_service, "get_provider", return_value=mock_failing_provider):
        # AI endpoint fails with 503
        ai_res = client.get(f"/api/profiles/{profile.id}/ai-insights")
        assert ai_res.status_code == 503

        # Deterministic analytics endpoint remains 100% functional
        det_res = client.get(f"/api/profiles/{profile.id}/analytics/overview")
        assert det_res.status_code == 200
        assert det_res.json()["growth"]["current_followers"] == 5400


def test_malformed_llm_json_response_rejected():
    provider = OpenAIProvider(api_key="sk-test-fake")

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "INVALID_NON_JSON_CONTENT"}}]
    }

    with patch("httpx.Client.post", return_value=mock_response):
        with pytest.raises(RuntimeError) as exc:
            provider.generate_insight(MagicMock())
        assert "validation error" in str(exc.value).lower()


# Configuration Behavior Verification Tests

def test_default_configuration_uses_mock_provider(db):
    """Omitting AI_PROVIDER or setting it to empty string defaults to mock provider."""
    profile = create_ai_test_data(db, "default_config_user")
    with patch("app.config.settings.ai_provider", "mock"), patch("app.config.settings.ai_api_key", ""):
        res = client.get(f"/api/profiles/{profile.id}/ai-insights")
        assert res.status_code == 200
        assert res.json()["provider"] == "mock"


def test_explicit_mock_provider_works_without_api_key(db):
    """AI_PROVIDER=mock works deterministically without requiring AI_API_KEY."""
    profile = create_ai_test_data(db, "explicit_mock_user")
    with patch("app.config.settings.ai_provider", "mock"), patch("app.config.settings.ai_api_key", ""):
        res = client.get(f"/api/profiles/{profile.id}/ai-insights")
        assert res.status_code == 200
        assert res.json()["provider"] == "mock"


def test_openai_provider_without_api_key_returns_503(db):
    """AI_PROVIDER=openai with missing AI_API_KEY returns 503 and NEVER silently falls back to mock."""
    profile = create_ai_test_data(db, "openai_nokey_user")
    with patch("app.config.settings.ai_provider", "openai"), patch("app.config.settings.ai_api_key", ""):
        res = client.get(f"/api/profiles/{profile.id}/ai-insights")
        assert res.status_code == 503
        assert "not configured" in res.json()["detail"].lower() or "missing" in res.json()["detail"].lower()


def test_openai_provider_with_configured_credentials_uses_openai_provider(db):
    """AI_PROVIDER=openai with configured credentials uses OpenAIProvider (mocked network response)."""
    profile = create_ai_test_data(db, "openai_withkey_user")

    mock_llm_json = """{
      "title": "OpenAI Generated Summary",
      "summary": "Generated summary from OpenAI mock network call.",
      "observations": [
        {"category": "growth", "statement": "Growth pattern observed.", "supporting_metrics": ["Followers: 5400"]}
      ],
      "data_points": ["Followers: 5,400"],
      "limitations": null,
      "provider": "openai",
      "generated_at": "2026-09-27T16:00:00Z"
    }"""

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": mock_llm_json}}]
    }

    with patch("app.config.settings.ai_provider", "openai"), \
         patch("app.config.settings.ai_api_key", "sk-test-valid-key"), \
         patch("httpx.Client.post", return_value=mock_response):

        res = client.get(f"/api/profiles/{profile.id}/ai-insights")
        assert res.status_code == 200
        assert "openai" in res.json()["provider"].lower()
        assert res.json()["title"] == "OpenAI Generated Summary"


def test_unsupported_provider_fails_safely_503(db):
    """AI_PROVIDER with an unsupported value returns 503 error and DOES NOT silently pick mock or openai."""
    profile = create_ai_test_data(db, "unsupported_provider_user")
    with patch("app.config.settings.ai_provider", "unsupported_llm_vendor"):
        res = client.get(f"/api/profiles/{profile.id}/ai-insights")
        assert res.status_code == 503
        assert "unsupported ai provider" in res.json()["detail"].lower()

