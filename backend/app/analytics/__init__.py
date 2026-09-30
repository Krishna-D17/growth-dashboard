"""
SocialScope Deterministic Analytics Engine
Provides pure mathematical and observational analytics over historical database records.
"""
from app.analytics.growth import compute_growth_analytics, calculate_absolute_growth, calculate_growth_percent
from app.analytics.engagement import compute_engagement_analytics, calculate_engagement_rate
from app.analytics.content import compute_content_analytics, sort_top_posts, normalize_content_type
from app.analytics.frequency import compute_frequency_analytics
from app.analytics.anomalies import detect_follower_anomalies
from app.analytics.comparison import compare_profile_overviews
from app.analytics.schemas import (
    GrowthAnalytics,
    EngagementAnalytics,
    ContentAnalytics,
    FrequencyAnalytics,
    TopPostItem,
    AnomalyResult,
    ProfileComparisonItem,
    ComparisonResult,
    ProfileAnalyticsOverview,
)

__all__ = [
    "compute_growth_analytics",
    "calculate_absolute_growth",
    "calculate_growth_percent",
    "compute_engagement_analytics",
    "calculate_engagement_rate",
    "compute_content_analytics",
    "sort_top_posts",
    "normalize_content_type",
    "compute_frequency_analytics",
    "detect_follower_anomalies",
    "compare_profile_overviews",
    "GrowthAnalytics",
    "EngagementAnalytics",
    "ContentAnalytics",
    "FrequencyAnalytics",
    "TopPostItem",
    "AnomalyResult",
    "ProfileComparisonItem",
    "ComparisonResult",
    "ProfileAnalyticsOverview",
]
