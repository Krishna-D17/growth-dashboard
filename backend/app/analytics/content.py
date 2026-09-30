import statistics
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple
import uuid

from app.models.post import Post, PostSnapshot
from app.analytics.schemas import ContentTypeStats, ContentAnalytics, TopPostItem
from app.analytics.engagement import calculate_post_engagement, calculate_engagement_rate

CANONICAL_CONTENT_TYPES = [
    "IMAGE", "VIDEO", "REEL", "CAROUSEL", "TEXT", "LINK", "THREAD", "UNKNOWN"
]


def normalize_content_type(raw_type: Optional[str]) -> str:
    """
    Normalizes platform-specific media type strings into SocialScope's canonical categories:
    IMAGE, VIDEO, REEL, CAROUSEL, TEXT, LINK, THREAD, UNKNOWN.
    """
    if not raw_type:
        return "UNKNOWN"

    raw_clean = raw_type.strip().lower()

    if raw_clean in ("image", "photo", "picture", "static_image"):
        return "IMAGE"
    elif raw_clean in ("video", "clip"):
        return "VIDEO"
    elif raw_clean in ("reel", "reels", "short"):
        return "REEL"
    elif raw_clean in ("carousel", "sidecar", "album", "multi_image"):
        return "CAROUSEL"
    elif raw_clean in ("text", "tweet", "status", "post"):
        return "TEXT"
    elif raw_clean in ("link", "url"):
        return "LINK"
    elif raw_clean in ("thread", "multi_tweet"):
        return "THREAD"
    elif raw_clean.upper() in CANONICAL_CONTENT_TYPES:
        return raw_clean.upper()

    return "UNKNOWN"


def compute_content_analytics(
    posts: List[Post],
    latest_snapshot_map: Dict[uuid.UUID, PostSnapshot]
) -> ContentAnalytics:
    """
    Groups posts by normalized content category and calculates per-category metrics.
    Preserves NULL metrics when data is unavailable.
    """
    if not posts:
        return ContentAnalytics()

    grouped_engagements: Dict[str, List[float]] = {c: [] for c in CANONICAL_CONTENT_TYPES}
    grouped_views: Dict[str, List[int]] = {c: [] for c in CANONICAL_CONTENT_TYPES}
    grouped_counts: Dict[str, int] = {c: 0 for c in CANONICAL_CONTENT_TYPES}
    grouped_dates: Dict[str, List[datetime]] = {c: [] for c in CANONICAL_CONTENT_TYPES}

    for post in posts:
        c_type = normalize_content_type(post.media_type)
        grouped_counts[c_type] += 1

        if post.posted_at:
            dt = post.posted_at if post.posted_at.tzinfo else post.posted_at.replace(tzinfo=timezone.utc)
            grouped_dates[c_type].append(dt)

        snapshot = latest_snapshot_map.get(post.id)
        if snapshot:
            eng = calculate_post_engagement(snapshot)
            if eng is not None:
                grouped_engagements[c_type].append(eng)

            if snapshot.views is not None:
                grouped_views[c_type].append(snapshot.views)

    by_content_type: List[ContentTypeStats] = []

    for c_type in CANONICAL_CONTENT_TYPES:
        count = grouped_counts[c_type]
        if count == 0:
            continue

        eng_list = grouped_engagements[c_type]
        avg_eng = round(statistics.mean(eng_list), 2) if eng_list else None
        med_eng = round(statistics.median(eng_list), 2) if eng_list else None

        views_list = grouped_views[c_type]
        tot_views = sum(views_list) if views_list else None
        avg_views = round(statistics.mean(views_list), 2) if views_list else None

        dates = sorted(grouped_dates[c_type])
        posting_freq = None
        if len(dates) >= 2:
            span_days = (dates[-1] - dates[0]).total_seconds() / 86400.0
            if span_days > 0:
                posting_freq = round(len(dates) / span_days, 2)

        by_content_type.append(
            ContentTypeStats(
                content_type=c_type,
                post_count=count,
                average_engagement=avg_eng,
                median_engagement=med_eng,
                total_views=tot_views,
                average_views=avg_views,
                posting_frequency=posting_freq
            )
        )

    return ContentAnalytics(
        by_content_type=by_content_type,
        total_posts=len(posts)
    )


def sort_top_posts(
    posts: List[Post],
    latest_snapshot_map: Dict[uuid.UUID, PostSnapshot],
    sort_by: str = "engagement",
    limit: int = 10,
    current_followers: Optional[int] = None
) -> List[TopPostItem]:
    """
    Sorts posts deterministically by selected metric (likes, comments, shares, views, engagement, engagement_rate, newest, oldest).
    Places missing/NULL values at the end of ranked queries.
    """
    items: List[Tuple[Post, Optional[PostSnapshot], Optional[float]]] = []

    for post in posts:
        snapshot = latest_snapshot_map.get(post.id)
        metric_val: Optional[float] = None

        if sort_by == "likes":
            metric_val = float(snapshot.likes) if snapshot and snapshot.likes is not None else None
        elif sort_by == "comments":
            metric_val = float(snapshot.comments) if snapshot and snapshot.comments is not None else None
        elif sort_by == "shares":
            metric_val = float(snapshot.shares) if snapshot and snapshot.shares is not None else None
        elif sort_by == "views":
            metric_val = float(snapshot.views) if snapshot and snapshot.views is not None else None
        elif sort_by == "engagement":
            metric_val = calculate_post_engagement(snapshot) if snapshot else None
        elif sort_by == "engagement_rate":
            eng = calculate_post_engagement(snapshot) if snapshot else None
            metric_val = calculate_engagement_rate(eng, current_followers)
        elif sort_by in ("newest", "oldest"):
            if post.posted_at:
                dt = post.posted_at if post.posted_at.tzinfo else post.posted_at.replace(tzinfo=timezone.utc)
                metric_val = dt.timestamp()
            else:
                metric_val = None

        items.append((post, snapshot, metric_val))

    # Sort key logic: (is_none, -value if descending else value, post_date)
    is_ascending = (sort_by == "oldest")

    def sort_key(item: Tuple[Post, Optional[PostSnapshot], Optional[float]]):
        p, snap, val = item
        if val is None:
            return (1, 0, 0)
        if is_ascending:
            return (0, val, p.id.hex)
        return (0, -val, p.id.hex)

    items.sort(key=sort_key)
    top_items = items[:limit]

    results: List[TopPostItem] = []
    for post, snapshot, val in top_items:
        eng = calculate_post_engagement(snapshot) if snapshot else None
        eng_rate = calculate_engagement_rate(eng, current_followers)

        results.append(
            TopPostItem(
                post_id=post.id,
                platform_post_id=post.platform_post_id,
                url=post.url,
                caption=post.caption,
                posted_at=post.posted_at,
                media_type=normalize_content_type(post.media_type),
                metric_name=sort_by,
                metric_value=val,
                likes=snapshot.likes if snapshot else None,
                comments=snapshot.comments if snapshot else None,
                shares=snapshot.shares if snapshot else None,
                views=snapshot.views if snapshot else None,
                engagement=eng,
                engagement_rate=eng_rate
            )
        )

    return results
