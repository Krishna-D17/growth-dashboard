from datetime import datetime, timezone, timedelta
from typing import Optional, List, Sequence
from app.models.profile import ProfileSnapshot
from app.analytics.schemas import GrowthAnalytics


def calculate_absolute_growth(current: Optional[int], previous: Optional[int]) -> Optional[int]:
    """
    Calculates absolute follower growth: current - previous.
    Returns None if either observation is unavailable.
    """
    if current is None or previous is None:
        return None
    return current - previous


def calculate_growth_percent(current: Optional[int], previous: Optional[int]) -> Optional[float]:
    """
    Calculates percentage follower growth: ((current - previous) / previous) * 100.
    Returns None if previous is missing, zero, or current is missing.
    """
    if current is None or previous is None or previous == 0:
        return None
    percent = ((current - previous) / previous) * 100.0
    return round(percent, 2)


def select_latest_snapshot_at_or_before(
    snapshots: Sequence[ProfileSnapshot],
    target_time: datetime
) -> Optional[ProfileSnapshot]:
    """
    Deterministic historical snapshot selection rule:
    Selects the latest snapshot with non-null followers collected_at <= target_time.
    Returns None if no suitable observation exists at or before target_time.
    """
    valid_candidates = [
        s for s in snapshots
        if s.followers is not None and s.collected_at <= target_time
    ]
    if not valid_candidates:
        return None
    return max(valid_candidates, key=lambda s: s.collected_at)


def calculate_growth_velocity(
    start_followers: Optional[int],
    start_time: datetime,
    end_followers: Optional[int],
    end_time: datetime
) -> Optional[float]:
    """
    Calculates follower growth velocity per unit time (followers per 24-hour day).
    Uses actual timestamps rather than assuming uniform collection intervals.
    """
    if start_followers is None or end_followers is None:
        return None

    if start_time.tzinfo is None:
        start_time = start_time.replace(tzinfo=timezone.utc)
    if end_time.tzinfo is None:
        end_time = end_time.replace(tzinfo=timezone.utc)

    elapsed_seconds = (end_time - start_time).total_seconds()
    if elapsed_seconds <= 0:
        return None

    elapsed_days = elapsed_seconds / 86400.0
    follower_change = end_followers - start_followers
    velocity = follower_change / elapsed_days
    return round(velocity, 2)


def calculate_growth_acceleration(
    velocity_recent: Optional[float],
    velocity_earlier: Optional[float],
    period_days: float = 7.0
) -> Optional[float]:
    """
    Calculates follower growth acceleration between two equal consecutive periods.
    acceleration = (velocity_recent - velocity_earlier) / period_days (followers/day^2).
    """
    if velocity_recent is None or velocity_earlier is None or period_days <= 0:
        return None
    acceleration = (velocity_recent - velocity_earlier) / period_days
    return round(acceleration, 2)


def compute_growth_analytics(snapshots: List[ProfileSnapshot]) -> GrowthAnalytics:
    """
    Computes complete GrowthAnalytics metrics from a time-sorted list of historical ProfileSnapshots.
    Preserves NULL semantics when data is incomplete or unavailable.
    """
    valid_snapshots = [s for s in snapshots if s.followers is not None]
    if not valid_snapshots:
        return GrowthAnalytics()

    # Ensure chronological order (oldest to newest)
    sorted_snapshots = sorted(valid_snapshots, key=lambda s: s.collected_at)

    latest = sorted_snapshots[-1]
    current_followers = latest.followers
    end_date = latest.collected_at

    previous = sorted_snapshots[-2] if len(sorted_snapshots) > 1 else None
    previous_followers = previous.followers if previous else None
    start_date = sorted_snapshots[0].collected_at

    absolute_growth = calculate_absolute_growth(current_followers, previous_followers)
    growth_percent = calculate_growth_percent(current_followers, previous_followers)

    # 7-day growth
    target_7d = latest.collected_at - timedelta(days=7)
    past_7d_snapshot = select_latest_snapshot_at_or_before(sorted_snapshots[:-1], target_7d)
    growth_7d = calculate_absolute_growth(current_followers, past_7d_snapshot.followers if past_7d_snapshot else None)
    growth_percent_7d = calculate_growth_percent(current_followers, past_7d_snapshot.followers if past_7d_snapshot else None)

    # 30-day growth
    target_30d = latest.collected_at - timedelta(days=30)
    past_30d_snapshot = select_latest_snapshot_at_or_before(sorted_snapshots[:-1], target_30d)
    growth_30d = calculate_absolute_growth(current_followers, past_30d_snapshot.followers if past_30d_snapshot else None)
    growth_percent_30d = calculate_growth_percent(current_followers, past_30d_snapshot.followers if past_30d_snapshot else None)

    # Growth velocity across total span
    first = sorted_snapshots[0]
    growth_velocity = calculate_growth_velocity(
        first.followers, first.collected_at,
        latest.followers, latest.collected_at
    )

    # Growth acceleration (compare recent 7D velocity with prior 7D velocity)
    v_recent = calculate_growth_velocity(
        past_7d_snapshot.followers if past_7d_snapshot else None,
        past_7d_snapshot.collected_at if past_7d_snapshot else latest.collected_at,
        latest.followers,
        latest.collected_at
    )
    target_14d = latest.collected_at - timedelta(days=14)
    past_14d_snapshot = select_latest_snapshot_at_or_before(sorted_snapshots, target_14d)
    v_earlier = calculate_growth_velocity(
        past_14d_snapshot.followers if past_14d_snapshot else None,
        past_14d_snapshot.collected_at if past_14d_snapshot else latest.collected_at,
        past_7d_snapshot.followers if past_7d_snapshot else None,
        past_7d_snapshot.collected_at if past_7d_snapshot else latest.collected_at
    ) if past_7d_snapshot and past_14d_snapshot else None

    growth_acceleration = calculate_growth_acceleration(v_recent, v_earlier, period_days=7.0)

    return GrowthAnalytics(
        current_followers=current_followers,
        previous_followers=previous_followers,
        absolute_growth=absolute_growth,
        growth_percent=growth_percent,
        growth_7d=growth_7d,
        growth_percent_7d=growth_percent_7d,
        growth_30d=growth_30d,
        growth_percent_30d=growth_percent_30d,
        growth_velocity=growth_velocity,
        growth_acceleration=growth_acceleration,
        start_date=start_date,
        end_date=end_date
    )
