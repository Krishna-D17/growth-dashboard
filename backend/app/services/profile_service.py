import uuid
import logging
from typing import Optional
from sqlalchemy.orm import Session
from app.models.profile import Profile

logger = logging.getLogger("socialscope.profile_service")


class ProfileService:
    """
    Service layer for managing social media profile targets and their lifecycle operations,
    including atomic target deletion and cascading historical data removal.
    """

    @staticmethod
    def delete_profile(db: Session, profile_id: uuid.UUID) -> Profile:
        """
        Deletes a monitored social media target by ID.
        Cascades deletion to all dependent historical records (ProfileSnapshots,
        Posts, PostSnapshots, CollectionJobs, CollectionErrors, Anomalies) atomically.
        Raises ValueError if the profile does not exist.
        """
        profile = db.query(Profile).filter(Profile.id == profile_id).first()
        if not profile:
            raise ValueError(f"Profile with ID '{profile_id}' not found.")

        handle = profile.username
        platform = profile.platform.value

        # Delete profile. Database foreign keys and ORM relationships
        # cascade deletion to snapshots, posts, post_snapshots, jobs, errors, and anomalies.
        db.delete(profile)
        db.commit()

        logger.info(f"Target profile '@{handle}' ({platform}, ID: {profile_id}) deleted successfully.")
        return profile


profile_service = ProfileService()
