import statistics
from datetime import datetime, timezone
from typing import List, Dict, Optional

from app.models.post import Post
from app.analytics.schemas import FrequencyAnalytics

WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def compute_frequency_analytics(posts: List[Post]) -> FrequencyAnalytics:
    """
    Calculates descriptive posting statistics (posts/day, posts/week, weekday & hourly distributions, posting intervals).
    Purely observational — makes no causal performance claims.
    """
    if not posts:
        return FrequencyAnalytics(
            posts_per_day=0.0,
            posts_per_week=0.0,
            posts_per_month=0.0,
            weekday_distribution={day: 0 for day in WEEKDAYS},
            hourly_distribution={h: 0 for h in range(24)}
        )

    valid_dates: List[datetime] = []
    for p in posts:
        if p.posted_at:
            dt = p.posted_at if p.posted_at.tzinfo else p.posted_at.replace(tzinfo=timezone.utc)
            valid_dates.append(dt)

    if not valid_dates:
        return FrequencyAnalytics(
            posts_per_day=None,
            posts_per_week=None,
            posts_per_month=None,
            weekday_distribution={day: 0 for day in WEEKDAYS},
            hourly_distribution={h: 0 for h in range(24)}
        )

    # Sort chronological
    sorted_dates = sorted(valid_dates)

    # Calculate overall span
    first_date = sorted_dates[0]
    last_date = sorted_dates[-1]
    span_seconds = (last_date - first_date).total_seconds()
    span_days = max(span_seconds / 86400.0, 1.0)  # Default to 1 day span for single post / zero elapsed time

    total_posts = len(sorted_dates)
    posts_per_day = round(total_posts / span_days, 2)
    posts_per_week = round(posts_per_day * 7.0, 2)
    posts_per_month = round(posts_per_day * 30.0, 2)

    # Weekday distribution
    weekday_counts: Dict[str, int] = {day: 0 for day in WEEKDAYS}
    # Hourly distribution
    hourly_counts: Dict[int, int] = {h: 0 for h in range(24)}

    for dt in sorted_dates:
        w_name = WEEKDAYS[dt.weekday()]
        weekday_counts[w_name] += 1
        hourly_counts[dt.hour] += 1

    # Consecutive posting intervals (in hours)
    intervals_hours: List[float] = []
    for i in range(len(sorted_dates) - 1):
        diff_sec = (sorted_dates[i + 1] - sorted_dates[i]).total_seconds()
        diff_hrs = diff_sec / 3600.0
        if diff_hrs >= 0:
            intervals_hours.append(diff_hrs)

    avg_interval = round(statistics.mean(intervals_hours), 2) if intervals_hours else None
    med_interval = round(statistics.median(intervals_hours), 2) if intervals_hours else None
    min_interval = round(min(intervals_hours), 2) if intervals_hours else None
    max_interval = round(max(intervals_hours), 2) if intervals_hours else None

    return FrequencyAnalytics(
        posts_per_day=posts_per_day,
        posts_per_week=posts_per_week,
        posts_per_month=posts_per_month,
        weekday_distribution=weekday_counts,
        hourly_distribution=hourly_counts,
        avg_posting_interval_hours=avg_interval,
        median_posting_interval_hours=med_interval,
        min_posting_interval_hours=min_interval,
        max_posting_interval_hours=max_interval
    )
