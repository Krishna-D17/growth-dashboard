import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Optional

from app.config import settings
from app.database.session import SessionLocal
from app.models.enums import CollectionSchedule, JobStatus
from app.models.profile import Profile
from app.models.collection import CollectionJob
from app.schemas.collector import CollectorTarget
from app.services.collection_service import collection_service, CollectionService
from app.collectors.exceptions import (
    CollectorExecutionError,
    RateLimitError,
    TargetValidationError,
    ContentUnavailableError,
)

logger = logging.getLogger("socialscope.scheduler")


def is_profile_due(profile: Profile, now: datetime) -> bool:
    """
    Evaluates whether a profile is due for collection based on its schedule
    frequency and last_collected_at timestamp.
    """
    if profile.collection_schedule == CollectionSchedule.MANUAL:
        return False

    if not profile.last_collected_at:
        return True

    last_collected = profile.last_collected_at
    if last_collected.tzinfo is None:
        last_collected = last_collected.replace(tzinfo=timezone.utc)

    elapsed = now - last_collected

    if profile.collection_schedule == CollectionSchedule.EVERY_6_HOURS:
        return elapsed >= timedelta(hours=6)
    elif profile.collection_schedule == CollectionSchedule.EVERY_12_HOURS:
        return elapsed >= timedelta(hours=12)
    elif profile.collection_schedule == CollectionSchedule.DAILY:
        return elapsed >= timedelta(hours=24)

    return False


def is_retryable_error(exc: Exception) -> bool:
    """
    Determines if a collection error is transient and appropriate for bounded retry.
    Permanent errors (invalid target, content missing, unauthorized) are not retried.
    """
    if isinstance(exc, (TargetValidationError, ContentUnavailableError)):
        return False
    if isinstance(exc, (CollectorExecutionError, RateLimitError)):
        return True
    # Default: non-fatal runtime errors can be retried up to max limit
    return True


def run_scheduled_collections(service: Optional[CollectionService] = None) -> int:
    """
    Scheduler job entrypoint.
    Queries monitored profiles, filters those due for collection, protects against overlapping runs,
    invokes CollectionService, isolates per-profile failures, and performs bounded retries.
    """
    service = service or collection_service
    db = SessionLocal()
    collected_count = 0

    try:
        now = datetime.now(timezone.utc)
        scheduled_profiles = db.query(Profile).filter(
            Profile.collection_schedule != CollectionSchedule.MANUAL
        ).all()

        logger.info(f"Scheduler tick: evaluated {len(scheduled_profiles)} scheduled profiles")

        for profile in scheduled_profiles:
            if not is_profile_due(profile, now):
                continue

            # Overlap Protection: Check if a job is currently RUNNING for this profile
            running_job = db.query(CollectionJob).filter_by(
                profile_id=profile.id,
                status=JobStatus.RUNNING
            ).first()

            if running_job:
                logger.info(f"Skipping scheduled collection for profile '{profile.username}' ({profile.platform.value}): CollectionJob '{running_job.id}' is already RUNNING")
                continue

            target = CollectorTarget(
                platform=profile.platform,
                username=profile.username,
                profile_url=profile.profile_url,
                platform_profile_id=profile.platform_profile_id
            )

            # Execution loop with bounded retry logic
            max_retries = settings.max_collection_retries
            backoff_sec = settings.retry_backoff_seconds
            attempt = 0

            while attempt <= max_retries:
                attempt += 1
                try:
                    logger.info(f"Executing scheduled collection for '{profile.username}' ({profile.platform.value}), attempt {attempt}/{max_retries + 1}")
                    service.execute_collection(db, target, post_limit=10)
                    collected_count += 1
                    break  # Success
                except Exception as exc:
                    logger.warning(
                        f"Collection failed for '{profile.username}' ({profile.platform.value}) on attempt {attempt}: {type(exc).__name__} - {str(exc)}"
                    )
                    if attempt <= max_retries and is_retryable_error(exc):
                        sleep_time = backoff_sec * (2 ** (attempt - 1))
                        logger.info(f"Retrying '{profile.username}' in {sleep_time} seconds...")
                        time.sleep(sleep_time)
                    else:
                        logger.error(
                            f"Collection for '{profile.username}' ({profile.platform.value}) failed after {attempt} attempts. Isolated error."
                        )
                        break  # Bounded retries exhausted or non-retryable error, move to next profile

    except Exception as top_exc:
        logger.error(f"Global scheduler job tick error: {type(top_exc).__name__} - {str(top_exc)}")
    finally:
        db.close()

    return collected_count
