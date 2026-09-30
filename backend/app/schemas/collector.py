from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, HttpUrl
from app.models.enums import SocialPlatform


class CollectorTarget(BaseModel):
    """Normalized input target for a collection operation."""
    platform: SocialPlatform
    username: str = Field(..., min_length=1, description="Social media profile handle/username")
    profile_url: str = Field(..., description="Full canonical profile URL")
    platform_profile_id: Optional[str] = Field(None, description="Platform-native numeric/string profile ID if known")


class NormalizedProfile(BaseModel):
    """Normalized profile metadata collected from a social platform."""
    platform: SocialPlatform
    username: str
    profile_url: str
    platform_profile_id: Optional[str] = None
    display_name: Optional[str] = None
    bio: Optional[str] = None
    profile_image_url: Optional[str] = None
    verified: bool = False

    # Historical metrics (MUST be None/nullable when unavailable, NOT 0)
    followers: Optional[int] = None
    following: Optional[int] = None
    post_count: Optional[int] = None
    other_platform_metrics: Optional[Dict[str, Any]] = None


class NormalizedPostMetrics(BaseModel):
    """Normalized post engagement metrics at a point in time (all nullable)."""
    likes: Optional[int] = None
    comments: Optional[int] = None
    shares: Optional[int] = None
    views: Optional[int] = None
    engagement: Optional[float] = None


class NormalizedPost(BaseModel):
    """Normalized social media post/content item."""
    platform_post_id: str
    url: str
    caption: Optional[str] = None
    posted_at: Optional[datetime] = None
    media_type: Optional[str] = None
    metrics: Optional[NormalizedPostMetrics] = None


class CollectionResult(BaseModel):
    """Normalized payload returned by a platform collector execution."""
    target: CollectorTarget
    profile: NormalizedProfile
    posts: List[NormalizedPost] = Field(default_factory=list)
    collector_version: str = "1.0.0"
    warnings: List[str] = Field(default_factory=list)
