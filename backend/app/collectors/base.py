from abc import ABC, abstractmethod
from typing import List, Optional
from app.models.enums import SocialPlatform
from app.schemas.collector import (
    CollectorTarget,
    NormalizedProfile,
    NormalizedPost,
    NormalizedPostMetrics,
    CollectionResult,
)
from app.collectors.exceptions import (
    TargetValidationError,
    CollectorExecutionError,
    ContentUnavailableError,
    RateLimitError,
)


class BaseCollector(ABC):
    """
    Abstract Base Collector defining the uniform interface contract
    for all platform-specific collectors (Instagram, X, Facebook).
    """

    platform: SocialPlatform
    collector_version: str = "1.0.0"

    @abstractmethod
    def validate_target(self, target: CollectorTarget) -> bool:
        """
        Validate that the provided target URL/username format is valid
        and supported by this platform collector.
        """
        pass

    @abstractmethod
    def collect_profile(self, target: CollectorTarget) -> NormalizedProfile:
        """
        Collect profile-level information and current metrics.
        """
        pass

    @abstractmethod
    def collect_posts(self, target: CollectorTarget, limit: int = 10) -> List[NormalizedPost]:
        """
        Collect recent public posts and content items for the target profile.
        """
        pass

    @abstractmethod
    def collect_post_metrics(self, post_id: str) -> Optional[NormalizedPostMetrics]:
        """
        Collect engagement metrics for a specific post.
        """
        pass

    def collect(self, target: CollectorTarget, post_limit: int = 10) -> CollectionResult:
        """
        Orchestrates full collection (profile + posts) for a target.
        """
        if not self.validate_target(target):
            raise TargetValidationError(
                f"Target '{target.username}' ({target.profile_url}) is invalid for platform '{self.platform.value}'"
            )

        try:
            profile_data = self.collect_profile(target)
            posts_data = self.collect_posts(target, limit=post_limit)

            return CollectionResult(
                target=target,
                profile=profile_data,
                posts=posts_data,
                collector_version=self.collector_version,
                warnings=[]
            )
        except (TargetValidationError, ContentUnavailableError, RateLimitError):
            raise
        except Exception as e:
            raise CollectorExecutionError(f"Collector execution failed for {target.username}: {str(e)}") from e
