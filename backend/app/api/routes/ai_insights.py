import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.ai.schemas import AIInsight
from app.ai.service import ai_service

router = APIRouter(tags=["ai-insights"])


@router.get("/profiles/{profile_id}/ai-insights", response_model=AIInsight)
def get_profile_ai_insights_endpoint(
    profile_id: uuid.UUID,
    days: Optional[int] = Query(None, ge=1, le=3650, description="Optional time window in days"),
    db: Session = Depends(get_db)
):
    """
    Generates concise, human-readable structured AI insights explaining deterministic profile analytics.
    Does NOT recalculate metrics or query external social media platforms.
    """
    try:
        return ai_service.generate_profile_insight(db, profile_id, days=days)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e) or "AI insights are not configured or temporarily unavailable."
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="AI insight generation failed."
        )
