import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.collection import CollectionJob
from app.schemas.collection import CollectionJobResponse

router = APIRouter(prefix="/collection-jobs", tags=["collection-jobs"])


@router.get("/{job_id}", response_model=CollectionJobResponse)
def get_collection_job(
    job_id: uuid.UUID,
    db: Session = Depends(get_db)
):
    """
    Retrieve status and metadata for a specific collection job by ID.
    """
    job = db.query(CollectionJob).filter_by(id=job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Collection job with ID '{job_id}' not found."
        )

    return job
