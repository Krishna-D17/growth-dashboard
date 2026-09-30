import re
import json
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple
from bs4 import BeautifulSoup
from app.models.enums import SocialPlatform
from app.schemas.collector import NormalizedProfile, NormalizedPost, NormalizedPostMetrics
from app.collectors.exceptions import ContentUnavailableError, RateLimitError, CollectorExecutionError


class InstagramParser:
    """
    Parser for converting raw Instagram public page HTML and meta tags
    into normalized profile and post data structures.
    """

    @staticmethod
    def parse_profile(html: str, target_username: str, profile_url: str) -> NormalizedProfile:
        soup = BeautifulSoup(html, "html.parser")

        # 1. Check for login wall, rate limit, or 404 block
        page_title = soup.title.string.strip() if soup.title and soup.title.string else ""
        if "login" in page_title.lower() or "log in" in page_title.lower():
            raise ContentUnavailableError(f"Instagram profile '{target_username}' requires authentication or login")
        if "page not found" in page_title.lower() or "sorry" in page_title.lower():
            raise ContentUnavailableError(f"Instagram profile '{target_username}' not found")
        if "rate limit" in html.lower() or "too many requests" in html.lower():
            raise RateLimitError("Instagram rate limit encountered on public profile fetch")

        # 2. Extract OpenGraph Meta Tags (standard public metadata)
        og_title = soup.find("meta", property="og:title")
        og_desc = soup.find("meta", property="og:description")
        og_image = soup.find("meta", property="og:image")

        title_content = og_title["content"] if og_title and og_title.get("content") else ""
        desc_content = og_desc["content"] if og_desc and og_desc.get("content") else ""
        image_url = og_image["content"] if og_image and og_image.get("content") else None

        # Display name extraction from title (e.g. "Display Name (@username) • Instagram photos")
        display_name = None
        if title_content:
            match_name = re.search(r"^(.*?)\s*\(@", title_content)
            if match_name:
                display_name = match_name.group(1).strip()
            else:
                display_name = title_content.split("•")[0].strip()

        # Metrics extraction from description (e.g. "12.5k Followers, 450 Following, 88 Posts...")
        followers, following, post_count = InstagramParser._parse_description_metrics(desc_content)

        # Bio extraction from description after "-" or ":" if available
        bio = None
        if desc_content and "-" in desc_content:
            parts = desc_content.split("-", 1)
            if len(parts) > 1 and parts[1].strip():
                bio = parts[1].strip()

        # Check for verified badge string in title/meta
        verified = "verified" in title_content.lower() or "verified" in html.lower()

        # Stable platform_profile_id assessment:
        # Check if a numeric user_id is present in page JSON/scripts; fall back to deterministic string ID
        extracted_id = InstagramParser._extract_numeric_user_id(html)
        platform_profile_id = extracted_id if extracted_id else f"ig_{target_username.lower()}"

        return NormalizedProfile(
            platform=SocialPlatform.INSTAGRAM,
            username=target_username.lower(),
            profile_url=profile_url,
            platform_profile_id=platform_profile_id,
            display_name=display_name or target_username,
            bio=bio,
            profile_image_url=image_url,
            verified=verified,
            followers=followers,
            following=following,
            post_count=post_count,
            other_platform_metrics={"source": "public_web_og"}
        )

    @staticmethod
    def _extract_numeric_user_id(html: str) -> Optional[str]:
        """Extract platform numeric profile ID if present in embedded JSON scripts."""
        patterns = [
            r'"profile_id"\s*:\s*"(\d+)"',
            r'"user_id"\s*:\s*"(\d+)"',
            r'"owner"\s*:\s*\{\s*"id"\s*:\s*"(\d+)"'
        ]
        for pattern in patterns:
            match = re.search(pattern, html)
            if match:
                return match.group(1)
        return None

    @staticmethod
    def _parse_description_metrics(desc: str) -> Tuple[Optional[int], Optional[int], Optional[int]]:
        """Extract followers, following, and post_count from description string."""
        if not desc:
            return None, None, None

        followers = None
        following = None
        post_count = None

        # Followers
        match_fol = re.search(r"([\d\.,kKmMbB]+)\s*Followers", desc, re.IGNORECASE)
        if match_fol:
            followers = InstagramParser._parse_number(match_fol.group(1))

        # Following
        match_ing = re.search(r"([\d\.,kKmMbB]+)\s*Following", desc, re.IGNORECASE)
        if match_ing:
            following = InstagramParser._parse_number(match_ing.group(1))

        # Posts
        match_posts = re.search(r"([\d\.,kKmMbB]+)\s*Posts", desc, re.IGNORECASE)
        if match_posts:
            post_count = InstagramParser._parse_number(match_posts.group(1))

        return followers, following, post_count

    @staticmethod
    def _parse_number(val_str: str) -> Optional[int]:
        """Convert metric strings like '12.5K', '1.2M', '1,234' into integers."""
        if not val_str:
            return None
        clean_str = val_str.replace(",", "").strip().lower()
        try:
            if "k" in clean_str:
                return int(float(clean_str.replace("k", "")) * 1000)
            elif "m" in clean_str:
                return int(float(clean_str.replace("m", "")) * 1000000)
            elif "b" in clean_str:
                return int(float(clean_str.replace("b", "")) * 1000000000)
            return int(float(clean_str))
        except ValueError:
            return None

    @staticmethod
    def parse_post_detail(html: str) -> Tuple[Optional[int], Optional[int], Optional[datetime], Optional[str]]:
        """
        Parses individual Instagram post page HTML to extract:
        (likes, comments, posted_at, caption)
        from OpenGraph description meta tags, description tags, and <time> tags.
        Returns None for missing or unavailable fields.
        """
        soup = BeautifulSoup(html, "html.parser")

        desc_content = None
        for meta_attr in [
            {"property": "og:description"},
            {"name": "description"},
            {"name": "twitter:description"},
            {"property": "twitter:description"}
        ]:
            tag = soup.find("meta", attrs=meta_attr)
            if tag and tag.get("content"):
                desc_content = tag["content"]
                break

        likes, comments, posted_at, caption = None, None, None, None

        if desc_content:
            match_likes = re.search(r"([\d\.,kKmMbB]+)\s*likes", desc_content, re.IGNORECASE)
            if match_likes:
                likes = InstagramParser._parse_number(match_likes.group(1))

            match_comments = re.search(r"([\d\.,kKmMbB]+)\s*comments", desc_content, re.IGNORECASE)
            if match_comments:
                comments = InstagramParser._parse_number(match_comments.group(1))

        # Publication timestamp from <time datetime="..."> tag
        time_tag = soup.find("time", datetime=True)
        if time_tag and time_tag.get("datetime"):
            dt_str = time_tag["datetime"]
            try:
                posted_at = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
            except Exception:
                posted_at = None

        og_desc = soup.find("meta", property="og:description")
        if og_desc and og_desc.get("content") and ":" in og_desc["content"]:
            parts = og_desc["content"].split(":", 1)
            if len(parts) > 1 and parts[1].strip():
                caption = parts[1].strip().strip('"')

        return likes, comments, posted_at, caption

    @staticmethod
    def parse_posts(html: str, target_username: str, profile_url: str, limit: int = 10) -> List[NormalizedPost]:
        """Extract public posts from page HTML."""
        soup = BeautifulSoup(html, "html.parser")
        posts: List[NormalizedPost] = []

        # Find post links (/p/POST_ID/ or /reel/REEL_ID/)
        links = soup.find_all("a", href=re.compile(r"/(p|reel)/[\w-]+/"))
        seen_ids = set()

        for a in links:
            href = a["href"]
            match_id = re.search(r"/(p|reel)/([\w-]+)/", href)
            if not match_id:
                continue

            post_type_slug, post_shortcode = match_id.groups()
            if post_shortcode in seen_ids:
                continue
            seen_ids.add(post_shortcode)

            post_url = f"https://www.instagram.com/{post_type_slug}/{post_shortcode}/"
            media_type = "REEL" if post_type_slug == "reel" else "IMAGE"

            # Check for img inside anchor for caption/alt
            img = a.find("img")
            caption = img["alt"] if img and img.get("alt") else None

            posts.append(
                NormalizedPost(
                    platform_post_id=post_shortcode,
                    url=post_url,
                    caption=caption,
                    posted_at=None,  # Nullable when unavailable
                    media_type=media_type,
                    metrics=NormalizedPostMetrics(
                        likes=None,
                        comments=None,
                        shares=None,
                        views=None,
                        engagement=None
                    )
                )
            )

            if len(posts) >= limit:
                break

        return posts
