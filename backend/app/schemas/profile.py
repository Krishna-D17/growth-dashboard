import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from app.models.enums import SocialPlatform, CollectionSchedule


class ProfileCreateRequest(BaseModel):
    """Payload for registering a new social media profile target."""
    platform: SocialPlatform
    target: str = Field(..., min_length=1, description="Username, handle (@username), or profile URL")
    collection_schedule: Optional[CollectionSchedule] = CollectionSchedule.MANUAL


class ProfileScheduleUpdateRequest(BaseModel):
    """Payload for updating a profile's collection schedule frequency."""
    collection_schedule: CollectionSchedule


class ProfileSnapshotResponse(BaseModel):
    """Response schema for profile historical snapshot metrics."""
    id: uuid.UUID
    collected_at: datetime
    followers: Optional[int] = None
    following: Optional[int] = None
    post_count: Optional[int] = None
    other_platform_metrics: Optional[Dict[str, Any]] = None
    collector_version: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ProfileResponse(BaseModel):
    """Response schema for monitored profile summary information."""
    id: uuid.UUID
    platform: SocialPlatform
    platform_profile_id: Optional[str] = None
    username: str
    display_name: Optional[str] = None
    profile_url: str
    bio: Optional[str] = None
    profile_image_url: Optional[str] = None
    verified: bool = False
    collection_schedule: CollectionSchedule = CollectionSchedule.MANUAL
    last_collected_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProfileDetailResponse(ProfileResponse):
    """Detailed profile response including latest historical snapshot."""
    latest_snapshot: Optional[ProfileSnapshotResponse] = None

    model_config = ConfigDict(from_attributes=True)
