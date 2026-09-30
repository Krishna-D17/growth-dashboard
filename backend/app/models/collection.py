import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import String, Text, Integer, DateTime, Enum, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.database.base import Base
from app.models.enums import SocialPlatform, JobStatus


class CollectionJob(Base):
    __tablename__ = "collection_jobs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    profile_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    platform: Mapped[SocialPlatform] = mapped_column(
        Enum(SocialPlatform, name="social_platform_enum", native_enum=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus, name="job_status_enum", native_enum=False, values_callable=lambda x: [e.value for e in x]),
        default=JobStatus.PENDING,
        nullable=False,
        index=True
    )
    records_collected: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    collector_version: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    # Relationships
    profile: Mapped["Profile"] = relationship("Profile", back_populates="jobs")
    errors: Mapped[List["CollectionError"]] = relationship(
        "CollectionError",
        back_populates="job",
        cascade="all, delete-orphan",
        order_by="CollectionError.timestamp.asc()"
    )


class CollectionError(Base):
    __tablename__ = "collection_errors"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    collection_job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("collection_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    error_type: Mapped[str] = mapped_column(String(128), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    # Relationships
    job: Mapped["CollectionJob"] = relationship("CollectionJob", back_populates="errors")
