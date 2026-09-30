from datetime import datetime, timezone
from app.ai.providers.base_provider import BaseAIProvider
from app.ai.schemas import AIAnalyticsContext, AIInsight, AIObservation


class MockAIProvider(BaseAIProvider):
    """Deterministic mock provider generating structured insights for testing and local dev."""

    @property
    def provider_name(self) -> str:
        return "mock"

    def is_configured(self) -> bool:
        return True

    def generate_insight(self, context: AIAnalyticsContext) -> AIInsight:
        now_str = datetime.now(timezone.utc).isoformat()
        username = context.profile.get("username", "unknown")
        platform = context.profile.get("platform", "unknown").upper()
        current_followers = context.growth.get("current_followers")
        growth_7d = context.growth.get("growth_7d")
        avg_eng = context.engagement.get("average_engagement")
        total_posts = context.content.get("total_posts", 0)
        anom_count = len(context.anomalies)

        title = f"{platform} Profile @{username} Analytics Summary"

        observations = []
        data_points = []

        # Growth observation
        if current_followers is not None:
            data_points.append(f"Followers: {current_followers:,}")
            obs_stmt = f"Profile @{username} currently has {current_followers:,} recorded followers."
            if growth_7d is not None:
                obs_stmt += f" 7-day follower change is {growth_7d:+,} followers."
                data_points.append(f"7D Growth: {growth_7d:+,}")
            observations.append(
                AIObservation(
                    category="growth",
                    statement=obs_stmt,
                    supporting_metrics=[f"Current Followers: {current_followers}", f"7D Growth: {growth_7d}"]
                )
            )
        else:
            observations.append(
                AIObservation(
                    category="growth",
                    statement="Follower snapshot metrics are unavailable or not yet collected.",
                    supporting_metrics=[]
                )
            )

        # Engagement observation
        if avg_eng is not None:
            data_points.append(f"Avg Engagement: {avg_eng:.1f}")
            observations.append(
                AIObservation(
                    category="engagement",
                    statement=f"Observed average interaction volume across tracked posts is {avg_eng:.1f} per post.",
                    supporting_metrics=[f"Average Engagement: {avg_eng}"]
                )
            )

        # Content observation
        data_points.append(f"Tracked Posts: {total_posts}")
        observations.append(
            AIObservation(
                category="content",
                statement=f"A total of {total_posts} published posts have been observed and categorized.",
                supporting_metrics=[f"Total Posts: {total_posts}"]
            )
        )

        # Anomaly observation
        if anom_count > 0:
            observations.append(
                AIObservation(
                    category="anomaly",
                    statement=f"Detected {anom_count} mathematical growth deviation spike(s) using MAD baseline bounds.",
                    supporting_metrics=[f"Detected Anomalies: {anom_count}"]
                )
            )

        summary = (
            f"Based on SocialScope database observations for @{username} on {platform}, "
            f"the profile has {current_followers if current_followers is not None else 'N/A'} followers "
            f"and {total_posts} tracked posts. Engagement and growth rates remain within recorded snapshot baselines."
        )

        limitations = (
            "Observation window is bounded by stored database snapshots. "
            "Metrics reflect deterministic historical snapshot points only."
        )

        return AIInsight(
            title=title,
            summary=summary,
            observations=observations,
            data_points=data_points,
            limitations=limitations,
            provider="mock",
            generated_at=now_str
        )
