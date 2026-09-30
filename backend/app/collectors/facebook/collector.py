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
from app.collectors.facebook.parser import FacebookParser
from app.collectors.exceptions import (
    TargetValidationError,
    CollectorExecutionError,
    ContentUnavailableError,
    RateLimitError,
)
from app.config import settings


class FacebookPageCollector(BaseCollector):
    """
    Real platform collector for public Facebook Pages and content metrics.
    SocialScope supports public Facebook Pages only; private personal profiles are excluded.
    Operates strictly on publicly accessible web metadata via BaseBrowserDriver
    without bypassing CAPTCHAs, authentication barriers, or rate limits.
    """

    platform = SocialPlatform.FACEBOOK
    collector_version = "facebook-1.0.0"

    def __init__(self, browser_driver: Optional[BaseBrowserDriver] = None, driver: Optional[BaseBrowserDriver] = None, **kwargs):
        self.browser_driver = browser_driver or driver or SeleniumBrowserDriver()

    def validate_target(self, target: CollectorTarget) -> bool:
        """
        Validate Facebook Page handle and URL format.
        Supports page slugs, www.facebook.com URLs, and facebook.com URLs.
        Rejects non-page routes (/groups, /events, /people, /profile.php) and other platforms.
        """
        if not target:
            return False
        if target.platform != SocialPlatform.FACEBOOK:
            return False

        if not target.username or not target.username.strip():
            return False

        url = target.profile_url.lower().strip()

        # Reject unrelated platform domains
        if "instagram.com" in url or "x.com" in url or "twitter.com" in url:
            return False

        # Reject unsupported Facebook routes (personal profiles, groups, events, system routes)
        unsupported_routes = [
            "/profile.php", "/people/", "/groups/", "/events/", "/marketplace/",
            "/login", "/recover", "/settings", "/privacy"
        ]
        for route in unsupported_routes:
            if route in url:
                return False

        clean_slug = target.username.lstrip("@").strip()
        # Page slug rules: alphanumeric, dots, underscores, hyphens, 1 to 50 characters
        if not re.match(r"^[a-zA-Z0-9._-]{1,50}$", clean_slug):
            return False

        return True

    def _normalize_profile_url(self, target: CollectorTarget) -> str:
        clean_slug = target.username.lstrip("@").strip().lower()
        return f"https://www.facebook.com/{clean_slug}/"

    def collect_profile(self, target: CollectorTarget) -> NormalizedProfile:
        """Collect profile metadata and historical snapshot metrics for a Facebook Page."""
        if not self.validate_target(target):
            raise TargetValidationError(f"Target '{target.username}' ({target.profile_url}) is invalid for Facebook Pages")

        profile_url = self._normalize_profile_url(target)
        clean_slug = target.username.lstrip("@").strip().lower()

        try:
            html_content = self.browser_driver.fetch_page_content(profile_url)
            return FacebookParser.parse_profile(html_content, clean_slug, profile_url)
        except (TargetValidationError, ContentUnavailableError, RateLimitError):
            raise
        except Exception as e:
            raise CollectorExecutionError(f"Failed to collect Facebook Page profile for '{clean_slug}': {str(e)}") from e

    def collect_posts(self, target: CollectorTarget, limit: int = 10) -> List[NormalizedPost]:
        """Collect recent public posts for a Facebook Page up to configured maximum limit."""
        if not self.validate_target(target):
            raise TargetValidationError(f"Target '{target.username}' ({target.profile_url}) is invalid for Facebook Pages")

        profile_url = self._normalize_profile_url(target)
        clean_slug = target.username.lstrip("@").strip().lower()
        max_posts = min(limit, settings.facebook_max_posts)

        try:
            html_content = self.browser_driver.fetch_page_content(profile_url)
            return FacebookParser.parse_posts(html_content, clean_slug, profile_url, limit=max_posts)
        except (TargetValidationError, ContentUnavailableError, RateLimitError):
            raise
        except Exception as e:
            raise CollectorExecutionError(f"Failed to collect Facebook Page posts for '{clean_slug}': {str(e)}") from e

    def collect_post_metrics(self, post_id: str) -> Optional[NormalizedPostMetrics]:
        """
        Collect post-level engagement metrics for a specific post.
        """
        post_url = f"https://www.facebook.com/posts/{post_id}"
        try:
            html_content = self.browser_driver.fetch_page_content(post_url)
            posts = FacebookParser.parse_posts(html_content, "facebook", post_url, limit=1)
            if posts and posts[0].metrics:
                return posts[0].metrics
            return NormalizedPostMetrics(likes=None, comments=None, shares=None, views=None, engagement=None)
        except Exception:
            return NormalizedPostMetrics(likes=None, comments=None, shares=None, views=None, engagement=None)
