import uuid
from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Text, BigInteger, Float, DateTime, UniqueConstraint, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.database.base import Base


class Post(Base):
    __tablename__ = "posts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    profile_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    platform_post_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    url: Mapped[str] = mapped_column(String(1024), nullable=False)
    caption: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    posted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    media_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

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
    profile: Mapped["Profile"] = relationship("Profile", back_populates="posts")
    snapshots: Mapped[List["PostSnapshot"]] = relationship(
        "PostSnapshot",
        back_populates="post",
        cascade="all, delete-orphan",
        order_by="PostSnapshot.collected_at.desc()"
    )

    __table_args__ = (
        UniqueConstraint("profile_id", "platform_post_id", name="uq_post_profile_platform_post_id"),
    )


class PostSnapshot(Base):
    __tablename__ = "post_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    post_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("posts.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    collected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True
    )
    likes: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    comments: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    shares: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    views: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    engagement: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Relationships
    post: Mapped["Post"] = relationship("Post", back_populates="snapshots")
