import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import String, Text, BigInteger, Boolean, DateTime, Enum, UniqueConstraint, Index, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.database.base import Base
from app.models.enums import SocialPlatform, CollectionSchedule


class Profile(Base):
    __tablename__ = "profiles"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    platform: Mapped[SocialPlatform] = mapped_column(
        Enum(SocialPlatform, name="social_platform_enum", native_enum=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        index=True
    )
    platform_profile_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    username: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    display_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    profile_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    bio: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    profile_image_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    collection_schedule: Mapped[CollectionSchedule] = mapped_column(
        Enum(CollectionSchedule, name="collection_schedule_enum", native_enum=False, values_callable=lambda x: [e.value for e in x]),
        default=CollectionSchedule.MANUAL,
        server_default="manual",
        nullable=False,
        index=True
    )
    last_collected_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )

    # Relationships
    snapshots: Mapped[List["ProfileSnapshot"]] = relationship(
        "ProfileSnapshot",
        back_populates="profile",
        cascade="all, delete-orphan",
        order_by="ProfileSnapshot.collected_at.desc()"
    )
    posts: Mapped[List["Post"]] = relationship(
        "Post",
        back_populates="profile",
        cascade="all, delete-orphan"
    )
    jobs: Mapped[List["CollectionJob"]] = relationship(
        "CollectionJob",
        back_populates="profile",
        cascade="all, delete-orphan"
    )
    anomalies: Mapped[List["Anomaly"]] = relationship(
        "Anomaly",
        back_populates="profile",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("platform", "username", name="uq_profile_platform_username"),
    )


class ProfileSnapshot(Base):
    __tablename__ = "profile_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    profile_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    collected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True
    )
    followers: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    following: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    post_count: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    other_platform_metrics: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    collector_version: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    # Relationships
    profile: Mapped["Profile"] = relationship("Profile", back_populates="snapshots")
