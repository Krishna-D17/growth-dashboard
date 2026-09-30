import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.services.analytics_service import analytics_service
from app.analytics.schemas import (
    GrowthAnalytics,
    EngagementAnalytics,
    ContentAnalytics,
    FrequencyAnalytics,
    TopPostItem,
    AnomalyResult,
    ComparisonResult,
    ProfileAnalyticsOverview,
)

router = APIRouter(tags=["analytics"])

ALLOWED_SORT_METRICS = {
    "likes", "comments", "shares", "views",
    "engagement", "engagement_rate", "newest", "oldest"
}


@router.get("/profiles/{profile_id}/analytics/overview", response_model=ProfileAnalyticsOverview)
def get_profile_analytics_overview_endpoint(
    profile_id: uuid.UUID,
    days: Optional[int] = Query(None, ge=1, le=3650, description="Optional time window in days"),
    db: Session = Depends(get_db)
):
    """
    Retrieve consolidated analytics overview for a monitored profile.
    Combines growth, engagement, content performance, posting frequency, and detected anomalies.
    """
    try:
        return analytics_service.get_profile_analytics_overview(db, profile_id, days=days)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Analytics execution failed.")


@router.get("/profiles/{profile_id}/analytics/growth", response_model=GrowthAnalytics)
def get_profile_growth_analytics_endpoint(
    profile_id: uuid.UUID,
    days: Optional[int] = Query(None, ge=1, le=3650, description="Optional time window in days"),
    db: Session = Depends(get_db)
):
    """
    Retrieve follower growth metrics for a monitored profile.
    Exposes absolute growth, growth percentage, 7-day and 30-day historical comparisons, velocity, and acceleration.
    """
    try:
        return analytics_service.get_profile_growth(db, profile_id, days=days)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Growth analytics execution failed.")


@router.get("/profiles/{profile_id}/analytics/engagement", response_model=EngagementAnalytics)
def get_profile_engagement_analytics_endpoint(
    profile_id: uuid.UUID,
    days: Optional[int] = Query(None, ge=1, le=3650, description="Optional time window in days"),
    db: Session = Depends(get_db)
):
    """
    Retrieve content engagement metrics for a monitored profile.
    Exposes total, average, and median engagement, engagement rate, and available metric component breakdowns.
    """
    try:
        return analytics_service.get_profile_engagement(db, profile_id, days=days)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Engagement analytics execution failed.")


@router.get("/profiles/{profile_id}/analytics/content", response_model=ContentAnalytics)
def get_profile_content_analytics_endpoint(
    profile_id: uuid.UUID,
    days: Optional[int] = Query(None, ge=1, le=3650, description="Optional time window in days"),
    db: Session = Depends(get_db)
):
    """
    Retrieve content performance statistics grouped by canonical categories.
    Categories: IMAGE, VIDEO, REEL, CAROUSEL, TEXT, LINK, THREAD, UNKNOWN.
    """
    try:
        return analytics_service.get_profile_content(db, profile_id, days=days)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Content analytics execution failed.")


@router.get("/profiles/{profile_id}/analytics/frequency", response_model=FrequencyAnalytics)
def get_profile_frequency_analytics_endpoint(
    profile_id: uuid.UUID,
    days: Optional[int] = Query(None, ge=1, le=3650, description="Optional time window in days"),
    db: Session = Depends(get_db)
):
    """
    Retrieve descriptive posting frequency metrics, weekday and hourly distributions, and posting intervals.
    Observational only — does not infer causation.
    """
    try:
        return analytics_service.get_profile_frequency(db, profile_id, days=days)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Frequency analytics execution failed.")


@router.get("/profiles/{profile_id}/analytics/top-posts", response_model=List[TopPostItem])
def get_profile_top_posts_endpoint(
    profile_id: uuid.UUID,
    sort_by: str = Query("engagement", description="Sort metric: likes, comments, shares, views, engagement, engagement_rate, newest, oldest"),
    limit: int = Query(10, ge=1, le=100, description="Maximum posts to return"),
    db: Session = Depends(get_db)
):
    """
    Retrieve top posts for a monitored profile ordered deterministically by selected metric.
    Missing metrics are ordered last.
    """
    clean_sort = sort_by.strip().lower()
    if clean_sort not in ALLOWED_SORT_METRICS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid sort_by metric '{sort_by}'. Allowed values: {sorted(list(ALLOWED_SORT_METRICS))}"
        )

    try:
        return analytics_service.get_top_posts(db, profile_id, sort_by=clean_sort, limit=limit)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Top posts execution failed.")


@router.get("/profiles/{profile_id}/analytics/anomalies", response_model=List[AnomalyResult])
def get_profile_anomalies_endpoint(
    profile_id: uuid.UUID,
    db: Session = Depends(get_db)
):
    """
    Retrieve detected follower growth anomalies for a monitored profile using Rolling Median and MAD.
    """
    try:
        return analytics_service.get_profile_anomalies(db, profile_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Anomaly detection execution failed.")


@router.get("/comparison", response_model=ComparisonResult)
def get_profile_comparison_endpoint(
    profile_ids: str = Query(..., description="Comma-separated profile UUIDs (e.g. ?profile_ids=uuid1,uuid2)"),
    db: Session = Depends(get_db)
):
    """
    Retrieve side-by-side descriptive metrics comparing multiple monitored profiles.
    Observational only — does NOT declare winning accounts or produce subjective rankings.
    """
    if not profile_ids or not profile_ids.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Parameter 'profile_ids' cannot be empty."
        )

    raw_tokens = [t.strip() for t in profile_ids.split(",") if t.strip()]
    if not raw_tokens:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Parameter 'profile_ids' must contain at least one valid profile UUID."
        )

    parsed_uuids: List[uuid.UUID] = []
    for token in raw_tokens:
        try:
            parsed_uuids.append(uuid.UUID(token))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid UUID string format '{token}' in profile_ids."
            )

    try:
        return analytics_service.compare_profiles(db, parsed_uuids)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Comparison execution failed.")
