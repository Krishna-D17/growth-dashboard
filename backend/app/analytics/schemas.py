import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict


class GrowthAnalytics(BaseModel):
    """Pydantic model representing profile follower growth metrics."""
    current_followers: Optional[int] = None
    previous_followers: Optional[int] = None
    absolute_growth: Optional[int] = None
    growth_percent: Optional[float] = None
    growth_7d: Optional[int] = None
    growth_percent_7d: Optional[float] = None
    growth_30d: Optional[int] = None
    growth_percent_30d: Optional[float] = None
    growth_velocity: Optional[float] = None  # followers / day
    growth_acceleration: Optional[float] = None  # change in velocity / day
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class EngagementAnalytics(BaseModel):
    """Pydantic model representing profile content engagement metrics."""
    total_engagement: Optional[float] = None
    average_engagement: Optional[float] = None
    median_engagement: Optional[float] = None
    engagement_rate: Optional[float] = None
    available_metrics: List[str] = []
    total_likes: Optional[int] = None
    total_comments: Optional[int] = None
    total_shares: Optional[int] = None
    total_views: Optional[int] = None
    sample_post_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class ContentTypeStats(BaseModel):
    """Metrics breakdown per normalized content category."""
    content_type: str
    post_count: int = 0
    average_engagement: Optional[float] = None
    median_engagement: Optional[float] = None
    total_views: Optional[int] = None
    average_views: Optional[float] = None
    posting_frequency: Optional[float] = None  # posts / day for this category

    model_config = ConfigDict(from_attributes=True)


class ContentAnalytics(BaseModel):
    """Aggregated metrics across normalized content categories."""
    by_content_type: List[ContentTypeStats] = []
    total_posts: int = 0

    model_config = ConfigDict(from_attributes=True)


class FrequencyAnalytics(BaseModel):
    """Descriptive posting frequency and timing behavior statistics."""
    posts_per_day: Optional[float] = None
    posts_per_week: Optional[float] = None
    posts_per_month: Optional[float] = None
    weekday_distribution: Dict[str, int] = {}
    hourly_distribution: Dict[int, int] = {}
    avg_posting_interval_hours: Optional[float] = None
    median_posting_interval_hours: Optional[float] = None
    min_posting_interval_hours: Optional[float] = None
    max_posting_interval_hours: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)


class TopPostItem(BaseModel):
    """Single post representation in top content rankings."""
    post_id: uuid.UUID
    platform_post_id: str
    url: str
    caption: Optional[str] = None
    posted_at: Optional[datetime] = None
    media_type: Optional[str] = None
    metric_name: str
    metric_value: Optional[float] = None
    likes: Optional[int] = None
    comments: Optional[int] = None
    shares: Optional[int] = None
    views: Optional[int] = None
    engagement: Optional[float] = None
    engagement_rate: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)


class AnomalyResult(BaseModel):
    """Detected mathematical anomaly event."""
    id: Optional[uuid.UUID] = None
    profile_id: uuid.UUID
    metric: str
    baseline: Dict[str, Any]
    observed_value: float
    severity: str
    method: str
    description: str
    detected_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProfileComparisonItem(BaseModel):
    """Descriptive comparison item for a single profile."""
    profile_id: uuid.UUID
    platform: str
    username: str
    display_name: Optional[str] = None
    current_followers: Optional[int] = None
    growth_7d: Optional[int] = None
    growth_percent_7d: Optional[float] = None
    growth_30d: Optional[int] = None
    growth_percent_30d: Optional[float] = None
    growth_velocity: Optional[float] = None
    average_engagement: Optional[float] = None
    engagement_rate: Optional[float] = None
    posts_per_week: Optional[float] = None
    content_distribution: Dict[str, int] = {}

    model_config = ConfigDict(from_attributes=True)


class ComparisonResult(BaseModel):
    """Structured descriptive comparison across multiple profiles."""
    profiles: List[ProfileComparisonItem] = []
    generated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProfileAnalyticsOverview(BaseModel):
    """Complete aggregated analytics overview for a profile."""
    profile_id: uuid.UUID
    platform: str
    username: str
    growth: GrowthAnalytics
    engagement: EngagementAnalytics
    content: ContentAnalytics
    frequency: FrequencyAnalytics
    anomalies: List[AnomalyResult] = []

    model_config = ConfigDict(from_attributes=True)
