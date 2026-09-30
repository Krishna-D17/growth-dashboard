import uuid
from datetime import datetime, timezone
from typing import List, Optional
from app.models.enums import SocialPlatform
from app.schemas.collector import (
    CollectorTarget,
    NormalizedProfile,
    NormalizedPost,
    NormalizedPostMetrics,
)
from app.collectors.base import BaseCollector
from app.collectors.exceptions import CollectorExecutionError, RateLimitError


class MockCollector(BaseCollector):
    """
    Mock Collector implementation used for pipeline orchestration testing,
    integration tests, and end-to-end database persistence verification.
    """

    def __init__(
        self,
        platform: SocialPlatform = SocialPlatform.INSTAGRAM,
        should_fail: bool = False,
        should_rate_limit: bool = False,
        simulate_null_metrics: bool = False,
        collector_version: str = "mock-1.0.0"
    ):
        self.platform = platform
        self.should_fail = should_fail
        self.should_rate_limit = should_rate_limit
        self.simulate_null_metrics = simulate_null_metrics
        self.collector_version = collector_version

    def validate_target(self, target: CollectorTarget) -> bool:
        if not target.username or not target.profile_url:
            return False
        if "invalid" in target.username.lower():
            return False
        return True

    def collect_profile(self, target: CollectorTarget) -> NormalizedProfile:
        if self.should_rate_limit:
            raise RateLimitError("Mock collector rate limit exceeded on profile fetch")
        if self.should_fail:
            raise CollectorExecutionError("Mock collector execution failed as requested")

        if self.simulate_null_metrics:
            # Verified nullable contract: None, not 0
            return NormalizedProfile(
                platform=target.platform,
                username=target.username,
                profile_url=target.profile_url,
                platform_profile_id=target.platform_profile_id or f"mock_pid_{target.username}",
                display_name=f"Mock {target.username.capitalize()}",
                bio="Mock bio description",
                verified=True,
                followers=None,
                following=None,
                post_count=None,
                other_platform_metrics={"is_mock": True}
            )

        return NormalizedProfile(
            platform=target.platform,
            username=target.username,
            profile_url=target.profile_url,
            platform_profile_id=target.platform_profile_id or f"mock_pid_{target.username}",
            display_name=f"Mock {target.username.capitalize()}",
            bio="Mock bio description",
            profile_image_url=f"https://mock.cdn/{target.username}.jpg",
            verified=True,
            followers=12500,
            following=450,
            post_count=88,
            other_platform_metrics={"highlights_count": 5}
        )

    def collect_posts(self, target: CollectorTarget, limit: int = 10) -> List[NormalizedPost]:
        if self.should_fail:
            raise CollectorExecutionError("Mock collector failed on post fetch")

        posts: List[NormalizedPost] = []
        count = min(limit, 3)

        for i in range(1, count + 1):
            post_id = f"mock_post_{target.username}_{i}"
            post_url = f"{target.profile_url.rstrip('/')}/p/{post_id}"

            metrics = None
            if not self.simulate_null_metrics:
                metrics = NormalizedPostMetrics(
                    likes=100 * i,
                    comments=10 * i,
                    shares=5 * i,
                    views=1000 * i if target.platform == SocialPlatform.INSTAGRAM else None,
                    engagement=3.5 * i
                )
            else:
                metrics = NormalizedPostMetrics(
                    likes=None,
                    comments=None,
                    shares=None,
                    views=None,
                    engagement=None
                )

            posts.append(
                NormalizedPost(
                    platform_post_id=post_id,
                    url=post_url,
                    caption=f"Mock post #{i} caption content for {target.username}",
                    posted_at=datetime.now(timezone.utc),
                    media_type="image" if i % 2 == 1 else "video",
                    metrics=metrics
                )
            )

        return posts

    def collect_post_metrics(self, post_id: str) -> Optional[NormalizedPostMetrics]:
        if self.simulate_null_metrics:
            return NormalizedPostMetrics(likes=None, comments=None, shares=None, views=None)
        return NormalizedPostMetrics(likes=250, comments=25, shares=10, views=1200, engagement=4.2)
