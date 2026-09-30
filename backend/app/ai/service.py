import uuid
import logging
from typing import Optional
from sqlalchemy.orm import Session

from app.config import settings
from app.services.analytics_service import analytics_service
from app.ai.schemas import AIAnalyticsContext, AIInsight
from app.ai.providers import BaseAIProvider, MockAIProvider, OpenAIProvider

logger = logging.getLogger("socialscope.ai.service")


class AIInsightService:
    """
    Orchestrates AI insight generation by building compact, structured analytics context
    from deterministic AnalyticsService outputs and forwarding to the configured AIProvider.
    """

    def get_provider(self, provider_name: Optional[str] = None) -> BaseAIProvider:
        """
        Instantiates provider according to configured settings.
        - "mock" (or empty/omitted): Returns MockAIProvider.
        - "openai": Returns OpenAIProvider.
        - Unsupported provider: Raises ValueError.
        """
        raw_name = provider_name if provider_name is not None else settings.ai_provider
        p_type = (raw_name or "mock").strip().lower()

        if p_type in ("mock", ""):
            return MockAIProvider()
        elif p_type == "openai":
            return OpenAIProvider(
                api_key=settings.ai_api_key,
                model_name=settings.ai_model_name
            )
        else:
            raise ValueError(
                f"Unsupported AI provider '{p_type}'. Supported providers are: 'mock', 'openai'."
            )

    def is_ai_configured(self) -> bool:
        """Returns True if the current AI provider is active and configured with credentials."""
        try:
            provider = self.get_provider()
            return provider.is_configured()
        except ValueError:
            return False

    def build_context(
        self,
        db: Session,
        profile_id: uuid.UUID,
        days: Optional[int] = None
    ) -> AIAnalyticsContext:
        """
        Fetches deterministic analytics overview and constructs sanitized AI analytics context.
        Contains NO raw browser data, NO cookies, NO raw captions, and NO internal system secrets.
        """
        overview = analytics_service.get_profile_analytics_overview(db, profile_id, days=days)
        ov_dict = overview.model_dump()

        context = AIAnalyticsContext(
            profile={
                "id": str(ov_dict["profile_id"]),
                "platform": ov_dict["platform"],
                "username": ov_dict["username"],
            },
            growth=ov_dict["growth"],
            engagement=ov_dict["engagement"],
            content=ov_dict["content"],
            frequency=ov_dict["frequency"],
            anomalies=ov_dict["anomalies"],
            days=days
        )
        return context

    def generate_profile_insight(
        self,
        db: Session,
        profile_id: uuid.UUID,
        days: Optional[int] = None,
        override_provider: Optional[BaseAIProvider] = None
    ) -> AIInsight:
        """
        Generates structured AIInsight for a target profile.
        Raises ValueError if profile is not found or provider is unsupported.
        Raises RuntimeError if provider credentials are missing.
        """
        try:
            provider = override_provider or self.get_provider()
        except ValueError as e:
            raise RuntimeError(str(e))

        if not provider.is_configured():
            raise RuntimeError("AI Provider is not configured. Missing API key.")

        context = self.build_context(db, profile_id, days=days)
        insight = provider.generate_insight(context)
        return insight


ai_service = AIInsightService()
