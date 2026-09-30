import re
from typing import List, Optional
from app.models.enums import SocialPlatform
from app.schemas.collector import (
    CollectorTarget,
    NormalizedProfile,
    NormalizedPost,
    NormalizedPostMetrics,
)
from app.collectors.base import BaseCollector
from app.collectors.browser.base import BaseBrowserDriver
from app.collectors.browser.selenium_driver import SeleniumBrowserDriver
from app.collectors.x.parser import XParser
from app.collectors.exceptions import (
    TargetValidationError,
    CollectorExecutionError,
    ContentUnavailableError,
    RateLimitError,
)
from app.config import settings


class XCollector(BaseCollector):
    """
    Real platform collector for public X (Twitter) profiles and content metrics.
    Operates strictly on publicly accessible web metadata without bypassing CAPTCHAs,
    authentication barriers, or rate limits.
    Communicates via the BaseBrowserDriver interface abstraction.
    """

    platform = SocialPlatform.X
    collector_version = "x-1.0.0"

    def __init__(self, browser_driver: Optional[BaseBrowserDriver] = None, driver: Optional[BaseBrowserDriver] = None, **kwargs):
        self.browser_driver = browser_driver or driver or SeleniumBrowserDriver()

    def validate_target(self, target: CollectorTarget) -> bool:
        """
        Validate X handle and URL format.
        Supports bare usernames, @usernames, x.com URLs, and twitter.com URLs.
        Rejects invalid routes (/home, /explore, etc.) and other domains.
        """
        if not target:
            return False
        if target.platform != SocialPlatform.X:
            return False

        if not target.username or not target.username.strip():
            return False

        url = target.profile_url.lower().strip()

        # Reject unrelated platform domains
        if "instagram.com" in url or "facebook.com" in url:
            return False

        # Reject non-profile X routes
        invalid_routes = ["/home", "/explore", "/search", "/i/", "/settings", "/notifications", "/messages", "/tos", "/privacy"]
        for route in invalid_routes:
            if route in url:
                return False

        clean_handle = target.username.lstrip("@").strip()
        # X handle rules: alphanumeric + underscore, 1 to 30 characters
        if not re.match(r"^[a-zA-Z0-9_]{1,30}$", clean_handle):
            return False

        return True

    def _normalize_profile_url(self, target: CollectorTarget) -> str:
        clean_handle = target.username.lstrip("@").strip().lower()
        return f"https://x.com/{clean_handle}/"

    def collect_profile(self, target: CollectorTarget) -> NormalizedProfile:
        """Collect profile metadata and historical snapshot metrics."""
        if not self.validate_target(target):
            raise TargetValidationError(f"Target '{target.username}' ({target.profile_url}) is invalid for X (Twitter)")

        profile_url = self._normalize_profile_url(target)
        clean_handle = target.username.lstrip("@").strip().lower()

        try:
            html_content = self.browser_driver.fetch_page_content(profile_url)
            return XParser.parse_profile(html_content, clean_handle, profile_url)
        except (TargetValidationError, ContentUnavailableError, RateLimitError):
            raise
        except Exception as e:
            raise CollectorExecutionError(f"Failed to collect X profile for '{clean_handle}': {str(e)}") from e

    def collect_posts(self, target: CollectorTarget, limit: int = 10) -> List[NormalizedPost]:
        """Collect recent public posts up to configured maximum limit."""
        if not self.validate_target(target):
            raise TargetValidationError(f"Target '{target.username}' ({target.profile_url}) is invalid for X (Twitter)")

        profile_url = self._normalize_profile_url(target)
        clean_handle = target.username.lstrip("@").strip().lower()
        max_posts = min(limit, settings.x_max_posts)

        try:
            html_content = self.browser_driver.fetch_page_content(profile_url)
            posts = XParser.parse_posts(html_content, clean_handle, profile_url, limit=max_posts)

            # Navigate to individual post URLs if posted_at timestamp or metrics are missing
            for post in posts:
                if post.posted_at is None or post.metrics.likes is None:
                    try:
                        post_html = self.browser_driver.fetch_page_content(post.url)
                        likes, comments, shares, views, posted_at, caption = XParser.parse_post_detail(post_html)
                        if likes is not None:
                            post.metrics.likes = likes
                        if comments is not None:
                            post.metrics.comments = comments
                        if shares is not None:
                            post.metrics.shares = shares
                        if views is not None:
                            post.metrics.views = views
                        if posted_at:
                            post.posted_at = posted_at
                        if caption and not post.caption:
                            post.caption = caption
                        eng_vals = [m for m in [post.metrics.likes, post.metrics.comments, post.metrics.shares] if m is not None]
                        if eng_vals:
                            post.metrics.engagement = float(sum(eng_vals))
                    except Exception:
                        pass

            return posts
        except (TargetValidationError, ContentUnavailableError, RateLimitError):
            raise
        except Exception as e:
            raise CollectorExecutionError(f"Failed to collect X posts for '{clean_handle}': {str(e)}") from e

    def collect_post_metrics(self, post_id: str) -> Optional[NormalizedPostMetrics]:
        """
        Collect post-level engagement metrics for a specific post by URL navigation.
        """
        post_url = f"https://x.com/x/status/{post_id}"
        try:
            html_content = self.browser_driver.fetch_page_content(post_url)
            likes, comments, shares, views, _, _ = XParser.parse_post_detail(html_content)
            eng_vals = [m for m in [likes, comments, shares] if m is not None]
            eng = float(sum(eng_vals)) if eng_vals else None
            return NormalizedPostMetrics(
                likes=likes,
                comments=comments,
                shares=shares,
                views=views,
                engagement=eng
            )
        except Exception:
            return NormalizedPostMetrics(likes=None, comments=None, shares=None, views=None, engagement=None)
