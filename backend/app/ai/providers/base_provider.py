from abc import ABC, abstractmethod
from app.ai.schemas import AIAnalyticsContext, AIInsight


class BaseAIProvider(ABC):
    """Abstract interface for LLM Insight Providers."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Returns the provider name identifier."""
        pass

    @abstractmethod
    def is_configured(self) -> bool:
        """Returns True if provider has valid credentials/configuration, False otherwise."""
        pass

    @abstractmethod
    def generate_insight(self, context: AIAnalyticsContext) -> AIInsight:
        """
        Generates a structured AIInsight from structured analytics context.
        Raises ValueError or RuntimeError if generation fails or output is invalid.
        """
        pass
