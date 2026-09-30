import uuid
from typing import List, Optional
from urllib.parse import urlparse
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.enums import SocialPlatform, CollectionSchedule
from app.models.profile import Profile
from app.models.collection import CollectionJob
from app.schemas.collector import CollectorTarget
from app.schemas.profile import (
    ProfileCreateRequest,
    ProfileScheduleUpdateRequest,
    ProfileResponse,
    ProfileDetailResponse,
    ProfileSnapshotResponse,
)
from app.schemas.collection import CollectionJobResponse
from app.collectors.registry import registry as default_registry, CollectorRegistry
from app.collectors.exceptions import (
    TargetValidationError,
    ContentUnavailableError,
    RateLimitError,
    CollectorExecutionError,
    PlatformNotSupportedError,
)
from app.services.collection_service import collection_service
from app.services.profile_service import profile_service

router = APIRouter(prefix="/profiles", tags=["profiles"])


def parse_and_validate_target(
    platform: SocialPlatform,
    raw_target: str,
    collector_registry: CollectorRegistry = default_registry
) -> tuple[str, str, CollectorTarget]:
    """
    Normalizes target handle/URL and validates it against the platform collector.
    Rejects malformed, unsupported, or cross-platform targets.
    """
    clean_raw = raw_target.strip()
    if not clean_raw:
        raise ValueError("Target string cannot be empty")

    if clean_raw.startswith("http://") or clean_raw.startswith("https://"):
        parsed = urlparse(clean_raw)
        path = parsed.path.strip("/")
        if not path:
            raise ValueError(f"Invalid profile URL '{raw_target}'")
        candidate_username = path.split("/")[0].lstrip("@").strip()
    else:
        candidate_username = clean_raw.lstrip("@").strip()

    candidate_handle = candidate_username.lower()

    if platform == SocialPlatform.INSTAGRAM:
        profile_url = f"https://www.instagram.com/{candidate_handle}/"
    elif platform == SocialPlatform.X:
        profile_url = f"https://x.com/{candidate_handle}/"
    elif platform == SocialPlatform.FACEBOOK:
        profile_url = f"https://www.facebook.com/{candidate_handle}/"
    else:
        profile_url = f"https://{platform.value}.com/{candidate_handle}/"

    target_obj = CollectorTarget(
        platform=platform,
        username=candidate_handle,
        profile_url=profile_url
    )

    try:
        collector = collector_registry.get_collector(platform)
    except PlatformNotSupportedError as e:
        raise ValueError(str(e)) from e

    if not collector.validate_target(target_obj):
        raise ValueError(f"Target '{raw_target}' is invalid for platform '{platform.value}'")

    return candidate_handle, profile_url, target_obj


@router.post("", response_model=ProfileResponse, status_code=status.HTTP_201_CREATED)
def create_profile(
    payload: ProfileCreateRequest,
    db: Session = Depends(get_db)
):
    """
    Add/register a social-media profile target to SocialScope.
    Validates target formatting via platform collectors and prevents duplicate creation.
    """
    try:
        clean_username, profile_url, target_obj = parse_and_validate_target(
            platform=payload.platform,
            raw_target=payload.target
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    # Check uniqueness
    existing = db.query(Profile).filter_by(
        platform=payload.platform,
        username=clean_username
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Profile '{clean_username}' on platform '{payload.platform.value}' is already monitored."
        )

    profile = Profile(
        platform=payload.platform,
        username=clean_username,
        profile_url=profile_url,
        collection_schedule=payload.collection_schedule or CollectionSchedule.MANUAL
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


@router.patch("/{profile_id}/schedule", response_model=ProfileResponse)
def update_profile_schedule(
    profile_id: uuid.UUID,
    payload: ProfileScheduleUpdateRequest,
    db: Session = Depends(get_db)
):
    """
    Update the collection schedule frequency for a monitored profile.
    """
    profile = db.query(Profile).filter_by(id=profile_id).first()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Profile with ID '{profile_id}' not found."
        )

    profile.collection_schedule = payload.collection_schedule
    db.commit()
    db.refresh(profile)
    return profile


@router.get("", response_model=List[ProfileResponse])
def list_profiles(
    platform: Optional[SocialPlatform] = Query(None, description="Filter profiles by platform"),
    db: Session = Depends(get_db)
):
    """
    Retrieve all monitored social media profiles, optionally filtered by platform.
    """
    query = db.query(Profile)
    if platform:
        query = query.filter_by(platform=platform)
    return query.order_by(Profile.created_at.desc()).all()


@router.get("/{profile_id}", response_model=ProfileDetailResponse)
def get_profile(
    profile_id: uuid.UUID,
    db: Session = Depends(get_db)
):
    """
    Retrieve details for a monitored profile by ID, including its latest historical snapshot.
    """
    profile = db.query(Profile).filter_by(id=profile_id).first()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Profile with ID '{profile_id}' not found."
        )

    latest_snapshot = None
    if profile.snapshots:
        latest_snapshot = ProfileSnapshotResponse.model_validate(profile.snapshots[0])

    response_data = ProfileDetailResponse.model_validate(profile)
    response_data.latest_snapshot = latest_snapshot
    return response_data


@router.post("/{profile_id}/collect", response_model=CollectionJobResponse)
def trigger_manual_collection(
    profile_id: uuid.UUID,
    post_limit: int = Query(10, ge=1, le=100, description="Maximum posts to collect"),
    db: Session = Depends(get_db)
):
    """
    Manually trigger a collection job for a monitored profile.
    Orchestrates execution through CollectionService and the Collector Registry.
    """
    profile = db.query(Profile).filter_by(id=profile_id).first()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Profile with ID '{profile_id}' not found."
        )

    target = CollectorTarget(
        platform=profile.platform,
        username=profile.username,
        profile_url=profile.profile_url,
        platform_profile_id=profile.platform_profile_id
    )

    try:
        job = collection_service.execute_collection(db, target, post_limit=post_limit)
        return job
    except TargetValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except ContentUnavailableError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except RateLimitError as e:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(e))
    except CollectorExecutionError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Collection execution failed: {str(e)}")


@router.get("/{profile_id}/collection-jobs", response_model=List[CollectionJobResponse])
def get_profile_collection_history(
    profile_id: uuid.UUID,
    limit: int = Query(20, ge=1, le=100, description="Maximum collection jobs to return"),
    db: Session = Depends(get_db)
):
    """
    Retrieve historical collection jobs belonging to a profile, ordered newest-first.
    """
    profile = db.query(Profile).filter_by(id=profile_id).first()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Profile with ID '{profile_id}' not found."
        )

    jobs = db.query(CollectionJob).filter_by(
        profile_id=profile_id
    ).order_by(CollectionJob.started_at.desc()).limit(limit).all()

    return jobs


@router.delete("/{profile_id}", status_code=status.HTTP_200_OK)
def delete_profile(
    profile_id: uuid.UUID,
    db: Session = Depends(get_db)
):
    """
    Delete a monitored social media target and all its associated historical data.
    Validates existence (HTTP 404 if not found), cascades deletion to dependent
    snapshots, posts, jobs, errors, anomalies, and deletes the profile atomically.
    """
    try:
        deleted_profile = profile_service.delete_profile(db, profile_id)
        return {
            "detail": "Target deleted successfully.",
            "id": str(profile_id),
            "username": deleted_profile.username,
            "platform": deleted_profile.platform.value
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )

