import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict
from sqlalchemy.orm import Session, joinedload

from app.models.profile import Profile, ProfileSnapshot
from app.models.post import Post, PostSnapshot
from app.models.anomaly import Anomaly
from app.analytics import (
    compute_growth_analytics,
    compute_engagement_analytics,
    compute_content_analytics,
    compute_frequency_analytics,
    detect_follower_anomalies,
    compare_profile_overviews,
    sort_top_posts,
    GrowthAnalytics,
    EngagementAnalytics,
    ContentAnalytics,
    FrequencyAnalytics,
    ProfileAnalyticsOverview,
    TopPostItem,
    ComparisonResult,
    AnomalyResult,
)

logger = logging.getLogger("socialscope.analytics")


class AnalyticsService:
    """
    Orchestrates data retrieval from PostgreSQL and passes structured historical observations
    to the deterministic analytics engine.
    Handles anomaly persistence with deduplication guards.
    """

    def get_profile_analytics_overview(
        self,
        db: Session,
        profile_id: uuid.UUID,
        days: Optional[int] = None
    ) -> ProfileAnalyticsOverview:
        """
        Retrieves historical snapshots and posts for a profile and calculates complete analytics overview.
        """
        profile = db.query(Profile).filter_by(id=profile_id).first()
        if not profile:
            raise ValueError(f"Profile with ID '{profile_id}' not found.")

        # Filter by time window if specified
        now = datetime.now(timezone.utc)
        cutoff = (now - timedelta(days=days)) if days else None

        # 1. Fetch ProfileSnapshots
        snapshots_query = db.query(ProfileSnapshot).filter_by(profile_id=profile_id)
        if cutoff:
            snapshots_query = snapshots_query.filter(ProfileSnapshot.collected_at >= cutoff)
        snapshots = snapshots_query.order_by(ProfileSnapshot.collected_at.asc()).all()

        # 2. Fetch Posts with snapshots loaded efficiently
        posts_query = db.query(Post).options(
            joinedload(Post.snapshots)
        ).filter_by(profile_id=profile_id)
        if cutoff:
            posts_query = posts_query.filter(Post.posted_at >= cutoff)
        posts = posts_query.all()

        # Build latest snapshot map per post
        latest_post_snapshot_map: Dict[uuid.UUID, PostSnapshot] = {}
        all_post_snapshots: List[PostSnapshot] = []

        for p in posts:
            if p.snapshots:
                # Snapshots relationship ordered by collected_at desc
                latest_snap = p.snapshots[0]
                latest_post_snapshot_map[p.id] = latest_snap
                all_post_snapshots.extend(p.snapshots)

        # 3. Perform Analytics Calculations
        growth_res = compute_growth_analytics(snapshots)
        eng_res = compute_engagement_analytics(
            list(latest_post_snapshot_map.values()),
            current_followers=growth_res.current_followers
        )
        content_res = compute_content_analytics(posts, latest_post_snapshot_map)
        freq_res = compute_frequency_analytics(posts)

        # 4. Detect Anomalies
        detected_anomalies = detect_follower_anomalies(profile_id, snapshots)

        return ProfileAnalyticsOverview(
            profile_id=profile.id,
            platform=profile.platform.value if hasattr(profile.platform, "value") else str(profile.platform),
            username=profile.username,
            growth=growth_res,
            engagement=eng_res,
            content=content_res,
            frequency=freq_res,
            anomalies=detected_anomalies
        )

    def get_top_posts(
        self,
        db: Session,
        profile_id: uuid.UUID,
        sort_by: str = "engagement",
        limit: int = 10
    ) -> List[TopPostItem]:
        """
        Retrieves top posts for a profile ordered deterministically by selected metric.
        """
        profile = db.query(Profile).filter_by(id=profile_id).first()
        if not profile:
            raise ValueError(f"Profile with ID '{profile_id}' not found.")

        latest_snapshot = profile.snapshots[0] if profile.snapshots else None
        current_followers = latest_snapshot.followers if latest_snapshot else None

        posts = db.query(Post).options(joinedload(Post.snapshots)).filter_by(profile_id=profile_id).all()
        latest_map = {p.id: p.snapshots[0] for p in posts if p.snapshots}

        return sort_top_posts(
            posts=posts,
            latest_snapshot_map=latest_map,
            sort_by=sort_by,
            limit=limit,
            current_followers=current_followers
        )

    def detect_and_persist_anomalies(self, db: Session, profile_id: uuid.UUID) -> List[Anomaly]:
        """
        Detects growth anomalies and persists newly identified anomalies to the PostgreSQL database.
        Includes deduplication guard based on (profile_id, metric, detected_at).
        """
        snapshots = db.query(ProfileSnapshot).filter_by(
            profile_id=profile_id
        ).order_by(ProfileSnapshot.collected_at.asc()).all()

        detected = detect_follower_anomalies(profile_id, snapshots)
        persisted_records: List[Anomaly] = []

        for item in detected:
            # Deduplication check: check if anomaly already exists for same profile, metric & timestamp
            existing = db.query(Anomaly).filter_by(
                profile_id=profile_id,
                metric=item.metric,
                detected_at=item.detected_at
            ).first()

            if not existing:
                anomaly_db = Anomaly(
                    profile_id=profile_id,
                    detected_at=item.detected_at,
                    metric=item.metric,
                    baseline=item.baseline,
                    observed_value=item.observed_value,
                    severity=item.severity,
                    method=item.method,
                    description=item.description
                )
                db.add(anomaly_db)
                persisted_records.append(anomaly_db)

        if persisted_records:
            db.commit()
            logger.info(f"Persisted {len(persisted_records)} new anomalies for profile '{profile_id}'.")

        return db.query(Anomaly).filter_by(profile_id=profile_id).all()

    def get_profile_growth(
        self,
        db: Session,
        profile_id: uuid.UUID,
        days: Optional[int] = None
    ) -> GrowthAnalytics:
        """Retrieves growth analytics for a profile."""
        overview = self.get_profile_analytics_overview(db, profile_id, days=days)
        return overview.growth

    def get_profile_engagement(
        self,
        db: Session,
        profile_id: uuid.UUID,
        days: Optional[int] = None
    ) -> EngagementAnalytics:
        """Retrieves engagement analytics for a profile."""
        overview = self.get_profile_analytics_overview(db, profile_id, days=days)
        return overview.engagement

    def get_profile_content(
        self,
        db: Session,
        profile_id: uuid.UUID,
        days: Optional[int] = None
    ) -> ContentAnalytics:
        """Retrieves content analytics for a profile."""
        overview = self.get_profile_analytics_overview(db, profile_id, days=days)
        return overview.content

    def get_profile_frequency(
        self,
        db: Session,
        profile_id: uuid.UUID,
        days: Optional[int] = None
    ) -> FrequencyAnalytics:
        """Retrieves posting frequency analytics for a profile."""
        overview = self.get_profile_analytics_overview(db, profile_id, days=days)
        return overview.frequency

    def get_profile_anomalies(
        self,
        db: Session,
        profile_id: uuid.UUID
    ) -> List[AnomalyResult]:
        """Detects, persists deduplicated anomalies, and returns structured AnomalyResult list."""
        profile = db.query(Profile).filter_by(id=profile_id).first()
        if not profile:
            raise ValueError(f"Profile with ID '{profile_id}' not found.")

        persisted = self.detect_and_persist_anomalies(db, profile_id)
        results: List[AnomalyResult] = []
        for a in persisted:
            results.append(
                AnomalyResult(
                    id=a.id,
                    profile_id=a.profile_id,
                    metric=a.metric,
                    baseline=a.baseline or {},
                    observed_value=a.observed_value,
                    severity=a.severity,
                    method=a.method or "rolling_median_mad",
                    description=a.description or "",
                    detected_at=a.detected_at
                )
            )
        return results

    def compare_profiles(
        self,
        db: Session,
        profile_ids: List[uuid.UUID]
    ) -> ComparisonResult:
        """
        Retrieves analytics overviews for multiple profiles and returns structured descriptive comparison.
        Does NOT generate subjective rankings or declare winning accounts.
        """
        overviews: List[ProfileAnalyticsOverview] = []
        for p_id in profile_ids:
            try:
                ov = self.get_profile_analytics_overview(db, p_id)
                overviews.append(ov)
            except ValueError:
                continue

        return compare_profile_overviews(overviews)


analytics_service = AnalyticsService()
