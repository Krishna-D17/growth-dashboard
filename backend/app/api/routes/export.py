import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Response
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.services.export_service import export_service, ExportFormat

router = APIRouter(tags=["export"])


def create_export_response(content: bytes, media_type: str, filename: str) -> Response:
    """Helper to construct streaming/file download Response with Content-Disposition header."""
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@router.get("/profiles/{profile_id}/export/profile")
def export_profile_endpoint(
    profile_id: uuid.UUID,
    format: ExportFormat = Query(ExportFormat.CSV, description="Export format: csv, json, or xlsx"),
    db: Session = Depends(get_db)
):
    """Export profile metadata in requested format (CSV, JSON, or XLSX)."""
    try:
        content, media_type, filename = export_service.export_profile(db, profile_id, format)
        return create_export_response(content, media_type, filename)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Export generation failed.")


@router.get("/profiles/{profile_id}/export/snapshots")
def export_snapshots_endpoint(
    profile_id: uuid.UUID,
    format: ExportFormat = Query(ExportFormat.CSV, description="Export format: csv, json, or xlsx"),
    db: Session = Depends(get_db)
):
    """Export profile snapshots history in requested format (CSV, JSON, or XLSX)."""
    try:
        content, media_type, filename = export_service.export_snapshots(db, profile_id, format)
        return create_export_response(content, media_type, filename)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Export generation failed.")


@router.get("/profiles/{profile_id}/export/posts")
def export_posts_endpoint(
    profile_id: uuid.UUID,
    format: ExportFormat = Query(ExportFormat.CSV, description="Export format: csv, json, or xlsx"),
    db: Session = Depends(get_db)
):
    """Export profile posts and metric snapshots in requested format (CSV, JSON, or XLSX)."""
    try:
        content, media_type, filename = export_service.export_posts(db, profile_id, format)
        return create_export_response(content, media_type, filename)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Export generation failed.")


@router.get("/profiles/{profile_id}/export/jobs")
def export_jobs_endpoint(
    profile_id: uuid.UUID,
    format: ExportFormat = Query(ExportFormat.CSV, description="Export format: csv, json, or xlsx"),
    db: Session = Depends(get_db)
):
    """Export collection job history in requested format (CSV, JSON, or XLSX)."""
    try:
        content, media_type, filename = export_service.export_jobs(db, profile_id, format)
        return create_export_response(content, media_type, filename)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Export generation failed.")


@router.get("/profiles/{profile_id}/export/analytics")
def export_analytics_endpoint(
    profile_id: uuid.UUID,
    format: ExportFormat = Query(ExportFormat.CSV, description="Export format: csv, json, or xlsx"),
    days: Optional[int] = Query(None, ge=1, le=3650, description="Optional time window in days"),
    db: Session = Depends(get_db)
):
    """Export deterministic analytics summary in requested format (CSV, JSON, or XLSX)."""
    try:
        content, media_type, filename = export_service.export_analytics(db, profile_id, format, days=days)
        return create_export_response(content, media_type, filename)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Export generation failed.")


@router.get("/profiles/{profile_id}/export/report")
def export_complete_report_endpoint(
    profile_id: uuid.UUID,
    format: ExportFormat = Query(ExportFormat.XLSX, description="Export format: csv, json, or xlsx"),
    days: Optional[int] = Query(None, ge=1, le=3650, description="Optional time window in days"),
    db: Session = Depends(get_db)
):
    """Export complete multi-dataset report (Profile, Snapshots, Posts, Jobs, Analytics) in requested format."""
    try:
        content, media_type, filename = export_service.export_complete_report(db, profile_id, format, days=days)
        return create_export_response(content, media_type, filename)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Export generation failed.")
