from datetime import datetime, timezone
from typing import List
from app.analytics.schemas import ProfileAnalyticsOverview, ProfileComparisonItem, ComparisonResult


def compare_profile_overviews(overviews: List[ProfileAnalyticsOverview]) -> ComparisonResult:
    """
    Assembles a descriptive cross-profile comparison dataset.
    Strictly observational — does NOT declare winners, best accounts, or subjective rankings.
    """
    items: List[ProfileComparisonItem] = []

    for ov in overviews:
        # Extract content type post counts for distribution map
        content_dist = {
            stats.content_type: stats.post_count
            for stats in ov.content.by_content_type
        }

        items.append(
            ProfileComparisonItem(
                profile_id=ov.profile_id,
                platform=ov.platform,
                username=ov.username,
                display_name=None,
                current_followers=ov.growth.current_followers,
                growth_7d=ov.growth.growth_7d,
                growth_percent_7d=ov.growth.growth_percent_7d,
                growth_30d=ov.growth.growth_30d,
                growth_percent_30d=ov.growth.growth_percent_30d,
                growth_velocity=ov.growth.growth_velocity,
                average_engagement=ov.engagement.average_engagement,
                engagement_rate=ov.engagement.engagement_rate,
                posts_per_week=ov.frequency.posts_per_week,
                content_distribution=content_dist
            )
        )

    return ComparisonResult(
        profiles=items,
        generated_at=datetime.now(timezone.utc)
    )
