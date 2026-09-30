import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict
from app.models.enums import SocialPlatform, JobStatus


class CollectionJobResponse(BaseModel):
    """Response schema for collection job execution status and audit logs."""
    id: uuid.UUID
    profile_id: uuid.UUID
    platform: SocialPlatform
    started_at: datetime
    completed_at: Optional[datetime] = None
    status: JobStatus
    records_collected: int = 0
    error_message: Optional[str] = None
    collector_version: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
