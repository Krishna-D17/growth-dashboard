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
from app.collectors.instagram.parser import InstagramParser
from app.collectors.exceptions import (
    TargetValidationError,
    CollectorExecutionError,
    ContentUnavailableError,
    RateLimitError,
)
from app.config import settings


class InstagramCollector(BaseCollector):
    """
    Real platform collector for public Instagram profiles and content metrics.
    Operates strictly on publicly accessible web metadata without bypassing CAPTCHAs,
    authentication barriers, or rate limits.
    """

    platform = SocialPlatform.INSTAGRAM
    collector_version = "instagram-1.0.0"

    def __init__(self, browser_driver: Optional[BaseBrowserDriver] = None, driver: Optional[BaseBrowserDriver] = None, **kwargs):
        self.browser_driver = browser_driver or driver or SeleniumBrowserDriver()

    def validate_target(self, target: CollectorTarget) -> bool:
        """
        Validate Instagram handle and URL format.
        Rejects targets designated for other platforms.
        """
        if not target:
            return False
        if target.platform != SocialPlatform.INSTAGRAM:
            return False

        url = target.profile_url.lower()
        if "x.com" in url or "twitter.com" in url or "facebook.com" in url:
            return False

        if not target.username or not target.username.strip():
            return False

        # Handle formatting (alphanumeric, dots, underscores, 1-30 chars)
        clean_handle = target.username.lstrip("@").strip()
        if not re.match(r"^[a-zA-Z0-9._]{1,30}$", clean_handle):
            return False

        return True

    def _normalize_profile_url(self, target: CollectorTarget) -> str:
        clean_handle = target.username.lstrip("@").strip().lower()
        return f"https://www.instagram.com/{clean_handle}/"

    def collect_profile(self, target: CollectorTarget) -> NormalizedProfile:
        """Collect profile metadata and historical snapshot metrics."""
        if not self.validate_target(target):
            raise TargetValidationError(f"Target '{target.username}' is not a valid Instagram target")

        profile_url = self._normalize_profile_url(target)
        clean_handle = target.username.lstrip("@").strip().lower()

        try:
            html_content = self.browser_driver.fetch_page_content(profile_url)
            return InstagramParser.parse_profile(html_content, clean_handle, profile_url)
        except (TargetValidationError, ContentUnavailableError, RateLimitError):
            raise
        except Exception as e:
            raise CollectorExecutionError(f"Failed to collect Instagram profile for '{clean_handle}': {str(e)}") from e

    def collect_posts(self, target: CollectorTarget, limit: int = 10) -> List[NormalizedPost]:
        """Collect recent public posts up to configured maximum limit."""
        if not self.validate_target(target):
            raise TargetValidationError(f"Target '{target.username}' is not a valid Instagram target")

        profile_url = self._normalize_profile_url(target)
        clean_handle = target.username.lstrip("@").strip().lower()
        max_posts = min(limit, settings.instagram_max_posts)

        try:
            html_content = self.browser_driver.fetch_page_content(profile_url)
            posts = InstagramParser.parse_posts(html_content, clean_handle, profile_url, limit=max_posts)

            # Navigate to individual public post pages to extract post-level metrics & timestamps
            for post in posts:
                try:
                    post_html = self.browser_driver.fetch_page_content(post.url)
                    likes, comments, posted_at, caption = InstagramParser.parse_post_detail(post_html)
                    if likes is not None or comments is not None:
                        post.metrics.likes = likes
                        post.metrics.comments = comments
                        post.metrics.engagement = float((likes or 0) + (comments or 0))
                    if posted_at:
                        post.posted_at = posted_at
                    if caption and not post.caption:
                        post.caption = caption
                except Exception:
                    # Gracefully retain default null metrics if individual post navigation fails
                    pass

            return posts
        except (TargetValidationError, ContentUnavailableError, RateLimitError):
            raise
        except Exception as e:
            raise CollectorExecutionError(f"Failed to collect Instagram posts for '{clean_handle}': {str(e)}") from e

    def collect_post_metrics(self, post_id: str) -> Optional[NormalizedPostMetrics]:
        """
        Collect post-level engagement metrics for a specific post by URL navigation.
        """
        post_url = f"https://www.instagram.com/p/{post_id}/"
        try:
            html_content = self.browser_driver.fetch_page_content(post_url)
            likes, comments, _, _ = InstagramParser.parse_post_detail(html_content)
            eng = float((likes or 0) + (comments or 0)) if (likes is not None or comments is not None) else None
            return NormalizedPostMetrics(
                likes=likes,
                comments=comments,
                shares=None,
                views=None,
                engagement=eng
            )
        except Exception:
            return NormalizedPostMetrics(
                likes=None,
                comments=None,
                shares=None,
                views=None,
                engagement=None
            )
