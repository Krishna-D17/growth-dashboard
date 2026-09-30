from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session
from app.models.enums import JobStatus
from app.models.profile import Profile, ProfileSnapshot
from app.models.post import Post, PostSnapshot
from app.models.collection import CollectionJob, CollectionError
from app.schemas.collector import CollectorTarget
from app.collectors.registry import registry as default_registry, CollectorRegistry
from app.collectors.exceptions import CollectorError


class CollectionService:
    """
    Orchestrates platform collection runs, converting normalized collector payloads
    into historical database snapshots, posts, post snapshots, and collection job audit logs.
    """

    def __init__(self, registry: Optional[CollectorRegistry] = None):
        self.registry = registry or default_registry

    def execute_collection(
        self,
        db: Session,
        target: CollectorTarget,
        post_limit: int = 10
    ) -> CollectionJob:
        """
        Executes end-to-end collection workflow for a target.
        Normalizes target handle formatting to prevent duplicate profile creation.
        """
        clean_username = target.username.lstrip("@").strip().lower()

        # 1. Fetch or create Profile record with normalized username
        profile = db.query(Profile).filter_by(
            platform=target.platform,
            username=clean_username
        ).first()

        if not profile:
            profile = Profile(
                platform=target.platform,
                username=clean_username,
                profile_url=target.profile_url,
                platform_profile_id=target.platform_profile_id
            )
            db.add(profile)
            db.flush()

        # 2. Create CollectionJob record
        job = CollectionJob(
            profile_id=profile.id,
            platform=target.platform,
            status=JobStatus.PENDING,
            started_at=datetime.now(timezone.utc),
            records_collected=0
        )
        db.add(job)
        db.commit()

        # 3. Transition status to RUNNING
        job.status = JobStatus.RUNNING
        db.commit()

        try:
            # 4. Get collector from registry and execute collection
            collector = self.registry.get_collector(target.platform)
            result = collector.collect(target, post_limit=post_limit)

            # 5. Update Profile metadata
            profile.display_name = result.profile.display_name or profile.display_name
            profile.bio = result.profile.bio or profile.bio
            profile.profile_image_url = result.profile.profile_image_url or profile.profile_image_url
            profile.verified = result.profile.verified
            profile.last_collected_at = datetime.now(timezone.utc)
            if result.profile.platform_profile_id:
                profile.platform_profile_id = result.profile.platform_profile_id

            # 6. Add ProfileSnapshot record (Historical preservation)
            profile_snapshot = ProfileSnapshot(
                profile_id=profile.id,
                collected_at=datetime.now(timezone.utc),
                followers=result.profile.followers,
                following=result.profile.following,
                post_count=result.profile.post_count,
                other_platform_metrics=result.profile.other_platform_metrics,
                collector_version=result.collector_version
            )
            db.add(profile_snapshot)

            # 7. Upsert Posts and PostSnapshots
            collected_posts_count = 0
            for post_item in result.posts:
                post = db.query(Post).filter_by(
                    profile_id=profile.id,
                    platform_post_id=post_item.platform_post_id
                ).first()

                if not post:
                    post = Post(
                        profile_id=profile.id,
                        platform_post_id=post_item.platform_post_id,
                        url=post_item.url,
                        caption=post_item.caption,
                        posted_at=post_item.posted_at,
                        media_type=post_item.media_type
                    )
                    db.add(post)
                    db.flush()
                else:
                    post.url = post_item.url
                    post.caption = post_item.caption or post.caption
                    post.media_type = post_item.media_type or post.media_type
                    if post_item.posted_at:
                        post.posted_at = post_item.posted_at

                if post_item.metrics:
                    post_snapshot = PostSnapshot(
                        post_id=post.id,
                        collected_at=datetime.now(timezone.utc),
                        likes=post_item.metrics.likes,
                        comments=post_item.metrics.comments,
                        shares=post_item.metrics.shares,
                        views=post_item.metrics.views,
                        engagement=post_item.metrics.engagement
                    )
                    db.add(post_snapshot)

                collected_posts_count += 1

            # 8. Mark job as SUCCESS
            job.status = JobStatus.SUCCESS
            job.records_collected = collected_posts_count
            job.collector_version = result.collector_version
            job.completed_at = datetime.now(timezone.utc)

            db.commit()
            return job

        except Exception as e:
            db.rollback()

            # Ensure job is attached to active session after rollback
            job = db.query(CollectionJob).filter_by(id=job.id).first()
            if job:
                job.status = JobStatus.FAILED
                job.error_message = str(e)
                job.completed_at = datetime.now(timezone.utc)

                error_log = CollectionError(
                    collection_job_id=job.id,
                    timestamp=datetime.now(timezone.utc),
                    error_type=type(e).__name__,
                    message=str(e),
                    details={"target_username": clean_username, "platform": target.platform.value}
                )
                db.add(error_log)
                db.commit()

            raise


collection_service = CollectionService()
