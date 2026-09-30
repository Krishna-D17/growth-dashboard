import statistics
from typing import Optional, List, Dict
from app.models.post import PostSnapshot
from app.analytics.schemas import EngagementAnalytics


def calculate_post_engagement(
    snapshot: PostSnapshot,
    weights: Optional[Dict[str, float]] = None
) -> Optional[float]:
    """
    Calculates post engagement from a PostSnapshot.
    Uses pre-stored snapshot.engagement if available, or calculates from available non-null components.
    Returns None if all engagement metrics are missing.
    """
    if snapshot.engagement is not None:
        return float(snapshot.engagement)

    default_weights = {"likes": 1.0, "comments": 1.0, "shares": 1.0, "views": 0.0}
    active_weights = weights or default_weights

    available_values = []
    if snapshot.likes is not None:
        available_values.append(snapshot.likes * active_weights.get("likes", 1.0))
    if snapshot.comments is not None:
        available_values.append(snapshot.comments * active_weights.get("comments", 1.0))
    if snapshot.shares is not None:
        available_values.append(snapshot.shares * active_weights.get("shares", 1.0))
    if snapshot.views is not None and active_weights.get("views", 0.0) > 0:
        available_values.append(snapshot.views * active_weights.get("views", 0.0))

    if not available_values:
        return None

    return float(sum(available_values))


def calculate_engagement_rate(
    total_engagement: Optional[float],
    followers: Optional[int]
) -> Optional[float]:
    """
    Calculates engagement rate: (total_engagement / followers) * 100.
    Returns None if total_engagement or followers is missing or followers <= 0.
    """
    if total_engagement is None or followers is None or followers <= 0:
        return None
    rate = (total_engagement / followers) * 100.0
    return round(rate, 4)


def compute_engagement_analytics(
    snapshots: List[PostSnapshot],
    current_followers: Optional[int] = None,
    weights: Optional[Dict[str, float]] = None
) -> EngagementAnalytics:
    """
    Computes aggregated EngagementAnalytics from a collection of PostSnapshots.
    Respects NULL metrics and identifies available metric components.
    """
    if not snapshots:
        return EngagementAnalytics()

    available_metrics_set = set()
    post_engagements: List[float] = []
    total_likes = 0
    has_likes = False
    total_comments = 0
    has_comments = False
    total_shares = 0
    has_shares = False
    total_views = 0
    has_views = False

    for s in snapshots:
        if s.likes is not None:
            total_likes += s.likes
            has_likes = True
            available_metrics_set.add("likes")
        if s.comments is not None:
            total_comments += s.comments
            has_comments = True
            available_metrics_set.add("comments")
        if s.shares is not None:
            total_shares += s.shares
            has_shares = True
            available_metrics_set.add("shares")
        if s.views is not None:
            total_views += s.views
            has_views = True
            available_metrics_set.add("views")

        eng = calculate_post_engagement(s, weights=weights)
        if eng is not None:
            post_engagements.append(eng)

    total_engagement = sum(post_engagements) if post_engagements else None
    avg_engagement = round(statistics.mean(post_engagements), 2) if post_engagements else None
    med_engagement = round(statistics.median(post_engagements), 2) if post_engagements else None

    eng_rate = calculate_engagement_rate(total_engagement, current_followers)

    return EngagementAnalytics(
        total_engagement=total_engagement,
        average_engagement=avg_engagement,
        median_engagement=med_engagement,
        engagement_rate=eng_rate,
        available_metrics=sorted(list(available_metrics_set)),
        total_likes=total_likes if has_likes else None,
        total_comments=total_comments if has_comments else None,
        total_shares=total_shares if has_shares else None,
        total_views=total_views if has_views else None,
        sample_post_count=len(snapshots)
    )
