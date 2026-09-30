import re
import json
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any, Tuple
from bs4 import BeautifulSoup

from app.models.enums import SocialPlatform
from app.schemas.collector import NormalizedProfile, NormalizedPost, NormalizedPostMetrics
from app.collectors.exceptions import ContentUnavailableError, RateLimitError


class XParser:
    """
    Parser for X (Twitter) public HTML pages and metadata structures.
    Extracts profile information, verified status, follower/following/post counts,
    and recent tweet metrics into normalized schema structures.
    """

    @staticmethod
    def _parse_number(val: Optional[str]) -> Optional[int]:
        """Convert metric string (e.g., '250.5K', '1.2M', '1,250', '320', '400') into integer."""
        if not val:
            return None
        clean_val = str(val).strip().replace(",", "")
        if not clean_val:
            return None

        # Check for duplicated concatenated strings like "400400", "379379", "12001200"
        if len(clean_val) >= 2 and len(clean_val) % 2 == 0:
            half = len(clean_val) // 2
            if clean_val[:half] == clean_val[half:] and clean_val[:half].isdigit():
                clean_val = clean_val[:half]

        # Check for shorthand K / M / B
        match = re.match(r"^([\d.]+)\s*([kKmMbB])?$", clean_val)
        if not match:
            # Fallback regex for string with trailing/leading characters (e.g. '45.2K Views')
            match = re.search(r"([\d.]+)\s*([kKmMbB])?", clean_val)
            if not match:
                return None

        num_str, suffix = match.groups()
        try:
            num = float(num_str)
            if suffix:
                s = suffix.upper()
                if s == "K":
                    num *= 1_000
                elif s == "M":
                    num *= 1_000_000
                elif s == "B":
                    num *= 1_000_000_000
            return int(num)
        except ValueError:
            return None

    @classmethod
    def _extract_metric_from_element(cls, btn: BeautifulSoup) -> Optional[int]:
        """
        Extract numeric metric value from a single metric element or button on X.
        Prefers aria-label, then data-count, then stripped text nodes, then get_text.
        """
        aria = btn.get("aria-label", "")
        data_count = btn.get("data-count")

        # 1. Prefer aria-label if it contains digits
        if aria:
            m = re.search(r"([\d.,]+\s*[kKmMbB]?)", aria)
            if m:
                res = cls._parse_number(m.group(1))
                if res is not None:
                    return res

        # 2. Prefer data-count attribute
        if data_count:
            res = cls._parse_number(str(data_count))
            if res is not None:
                return res

        # 3. Check stripped text strings (first non-empty text node containing numbers)
        for text_str in btn.stripped_strings:
            m = re.search(r"([\d.,]+\s*[kKmMbB]?)", text_str)
            if m:
                res = cls._parse_number(m.group(1))
                if res is not None:
                    return res

        # 4. Fallback to get_text()
        txt = btn.get_text().strip()
        if txt:
            m = re.search(r"([\d.,]+\s*[kKmMbB]?)", txt)
            if m:
                return cls._parse_number(m.group(1))

        return None

    @classmethod
    def parse_profile(cls, html_content: str, username: str, profile_url: str) -> NormalizedProfile:
        """
        Parse profile metadata from X page HTML content.
        Raises ContentUnavailableError or RateLimitError if account is unavailable or rate limited.
        """
        if not html_content or not html_content.strip():
            raise ContentUnavailableError(f"Empty HTML content received for X profile '{username}'")

        soup = BeautifulSoup(html_content, "html.parser")
        text_content = soup.get_text().lower()

        # 1. Rate Limit Detection
        if "rate limit" in text_content or "too many requests" in text_content:
            raise RateLimitError(f"Rate limit hit while accessing X profile '{username}'")

        # 2. Content / Account Availability Detection
        if "this account doesn’t exist" in text_content or "this account doesn't exist" in text_content or \
           "account suspended" in text_content or "page not found" in text_content:
            raise ContentUnavailableError(f"X account '{username}' does not exist or is unavailable")

        # 3. Login Wall Detection
        title_text = soup.title.string.lower() if soup.title and soup.title.string else ""
        if "sign in to x" in title_text or "log in to twitter" in title_text or "login-flow" in text_content:
            raise ContentUnavailableError(f"Public access restricted by X login wall for profile '{username}'")

        clean_handle = username.lstrip("@").strip().lower()

        # 4. Platform Profile ID (Genuine ID or None - NEVER fabricated UUID)
        platform_profile_id = None
        user_id_meta = soup.find("meta", property="page:user_id") or soup.find("meta", attrs={"name": "user_id"})
        if user_id_meta and user_id_meta.get("content"):
            platform_profile_id = user_id_meta["content"].strip()

        # Try JSON-LD or script tag for user ID
        if not platform_profile_id:
            for script in soup.find_all("script", type="application/ld+json"):
                try:
                    data = json.loads(script.string or "{}")
                    author = data.get("author", {})
                    if isinstance(author, dict) and author.get("identifier"):
                        platform_profile_id = str(author["identifier"]).strip()
                        break
                except (json.JSONDecodeError, TypeError):
                    continue

        # 5. Display Name
        display_name = None
        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):
            title_str = og_title["content"]
            match = re.match(r"^(.*?)\s*\(@[a-zA-Z0-9_]+\)", title_str)
            if match:
                display_name = match.group(1).strip()
            else:
                display_name = title_str.split("/")[0].strip()

        if not display_name and soup.title and soup.title.string:
            title_str = soup.title.string
            match = re.match(r"^(.*?)\s*\(@[a-zA-Z0-9_]+\)", title_str)
            if match:
                display_name = match.group(1).strip()
            else:
                display_name = title_str.split("/")[0].strip()

        user_name_div = soup.find("div", attrs={"data-testid": "UserName"})
        if user_name_div:
            span = user_name_div.find("span")
            if span and span.text.strip():
                display_name = span.text.strip()

        # 6. Bio
        bio = None
        og_desc = soup.find("meta", property="og:description") or soup.find("meta", attrs={"name": "description"})
        if og_desc and og_desc.get("content"):
            raw_desc = og_desc["content"].strip()
            # Clean off description prefix if present
            bio = re.sub(r"^The latest Tweets from .*?\.\s*", "", raw_desc)

        user_desc_div = soup.find("div", attrs={"data-testid": "UserDescription"})
        if user_desc_div:
            bio = user_desc_div.get_text().strip()

        # 7. Profile Image URL
        profile_image_url = None
        og_img = soup.find("meta", property="og:image")
        if og_img and og_img.get("content"):
            profile_image_url = og_img["content"].strip()

        # 8. Verified Status
        verified = False
        if soup.find(attrs={"data-testid": "icon-verified"}) or "verified account" in text_content:
            verified = True

        # 9. Follower / Following / Post Count
        followers = None
        following = None
        post_count = None

        # Try DOM testids
        followers_elem = soup.find(attrs={"data-testid": "followers-count"})
        if followers_elem:
            followers = cls._parse_number(followers_elem.get_text())

        following_elem = soup.find(attrs={"data-testid": "following-count"})
        if following_elem:
            following = cls._parse_number(following_elem.get_text())

        post_count_elem = soup.find(attrs={"data-testid": "post-count"})
        if post_count_elem:
            post_count = cls._parse_number(post_count_elem.get_text())

        space_text = soup.get_text(" ")

        # Fallback to description regex e.g. "250.5K Followers, 320 Following, 15.2K Posts"
        if og_desc and og_desc.get("content"):
            desc_str = og_desc["content"]
            if followers is None:
                m_fol = re.search(r"(\d[\d.,]*[kKmMbB]?)\s+Followers", desc_str, re.IGNORECASE)
                if m_fol:
                    followers = cls._parse_number(m_fol.group(1))

            if following is None:
                m_foll = re.search(r"(\d[\d.,]*[kKmMbB]?)\s+Following", desc_str, re.IGNORECASE)
                if m_foll:
                    following = cls._parse_number(m_foll.group(1))

            if post_count is None:
                m_posts = re.search(r"(\d[\d.,]*[kKmMbB]?)\s+Posts", desc_str, re.IGNORECASE)
                if m_posts:
                    post_count = cls._parse_number(m_posts.group(1))

        # Fallback to full page space-separated text content
        if followers is None:
            m_fol = re.search(r"(\d[\d.,]*[kKmMbB]?)\s*Followers", space_text, re.IGNORECASE)
            if m_fol:
                followers = cls._parse_number(m_fol.group(1))

        if following is None:
            m_ing = re.search(r"(\d[\d.,]*[kKmMbB]?)\s*Following", space_text, re.IGNORECASE)
            if m_ing:
                following = cls._parse_number(m_ing.group(1))

        if post_count is None:
            m_posts = re.search(r"(\d[\d.,]*[kKmMbB]?)\s*posts", space_text, re.IGNORECASE)
            if m_posts:
                post_count = cls._parse_number(m_posts.group(1))
            else:
                t_data1 = soup.find("meta", attrs={"name": "twitter:data1"})
                if t_data1 and t_data1.get("content"):
                    post_count = cls._parse_number(t_data1["content"])

        # Fallback to JSON-LD
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string or "{}")
                author = data.get("author", {})
                if isinstance(author, dict):
                    interactions = author.get("interactionStatistic", [])
                    for item in interactions:
                        if item.get("interactionType") == "http://schema.org/FollowAction" and followers is None:
                            followers = cls._parse_number(str(item.get("userInteractionCount")))
            except (json.JSONDecodeError, TypeError):
                continue

        return NormalizedProfile(
            platform=SocialPlatform.X,
            username=clean_handle,
            profile_url=profile_url,
            platform_profile_id=platform_profile_id,
            display_name=display_name,
            bio=bio,
            profile_image_url=profile_image_url,
            verified=verified,
            followers=followers,
            following=following,
            post_count=post_count,
            other_platform_metrics=None
        )

    @classmethod
    def parse_post_detail(cls, html_content: str) -> Tuple[Optional[int], Optional[int], Optional[int], Optional[int], Optional[datetime], Optional[str]]:
        """
        Parse individual X post/tweet page HTML content to extract:
        (likes, comments, shares, views, posted_at, caption)
        from OpenGraph meta tags, article:published_time, and DOM elements.
        """
        if not html_content or not html_content.strip():
            return None, None, None, None, None, None

        soup = BeautifulSoup(html_content, "html.parser")

        posted_at = None
        pub_time_meta = soup.find("meta", property="article:published_time")
        if pub_time_meta and pub_time_meta.get("content"):
            try:
                posted_at = datetime.fromisoformat(pub_time_meta["content"].replace("Z", "+00:00"))
            except ValueError:
                posted_at = None

        if not posted_at:
            time_tag = soup.find("time", datetime=True)
            if time_tag and time_tag.get("datetime"):
                try:
                    posted_at = datetime.fromisoformat(time_tag["datetime"].replace("Z", "+00:00"))
                except ValueError:
                    posted_at = None

        caption = None
        og_desc = soup.find("meta", property="og:description") or soup.find("meta", attrs={"name": "description"})
        if og_desc and og_desc.get("content"):
            caption = og_desc["content"].strip()

        likes, comments, shares, views = None, None, None, None
        metric_container = soup.find(attrs={"role": "group"}) or soup
        for btn in metric_container.find_all(["button", "div", "a"]):
            aria = btn.get("aria-label", "")
            t_id = btn.get("data-testid", "")
            if (re.search(r"reply", aria, re.I) or t_id == "reply") and comments is None:
                comments = cls._extract_metric_from_element(btn)
            elif (re.search(r"repost|retweet", aria, re.I) or t_id in ("retweet", "repost")) and shares is None:
                shares = cls._extract_metric_from_element(btn)
            elif (re.search(r"like", aria, re.I) or t_id == "like") and likes is None:
                likes = cls._extract_metric_from_element(btn)
            elif (re.search(r"view", aria, re.I) or t_id == "views") and views is None:
                views = cls._extract_metric_from_element(btn)

        return likes, comments, shares, views, posted_at, caption

    @classmethod
    def parse_posts(cls, html_content: str, username: str, profile_url: str, limit: int = 10) -> List[NormalizedPost]:
        """
        Parse recent public posts (tweets) from X page HTML content.
        """
        if not html_content or not html_content.strip():
            return []

        soup = BeautifulSoup(html_content, "html.parser")
        tweet_elements = soup.find_all("article")
        if not tweet_elements:
            tweet_elements = soup.find_all("div", class_="tweet")

        clean_handle = username.lstrip("@").strip().lower()
        posts: List[NormalizedPost] = []
        seen_ids = set()

        for idx, elem in enumerate(tweet_elements):
            if len(posts) >= limit:
                break

            # 1. Post ID & URL
            post_id = elem.get("data-post-id")
            if not post_id:
                link = elem.find("a", href=re.compile(r"/status/(\d+)"))
                if link:
                    m = re.search(r"/status/(\d+)", link["href"])
                    if m:
                        post_id = m.group(1)

            if not post_id or post_id in seen_ids:
                continue
            seen_ids.add(post_id)

            post_url = f"https://x.com/{clean_handle}/status/{post_id}"

            # 2. Caption / Tweet Text
            caption = None
            text_div = elem.find(attrs={"data-testid": "tweetText"}) or elem.find("div", dir="auto")
            if text_div:
                caption = text_div.get_text().strip()

            # 3. Posted At Timestamp
            posted_at = None
            time_elem = elem.find("time")
            if time_elem and time_elem.get("datetime"):
                try:
                    dt_str = time_elem["datetime"].replace("Z", "+00:00")
                    posted_at = datetime.fromisoformat(dt_str)
                except ValueError:
                    posted_at = None

            # 4. Media Type
            media_type = "TEXT"
            if elem.find(attrs={"data-testid": "media-video"}) or elem.find("video"):
                media_type = "VIDEO"
            elif elem.find(attrs={"data-testid": "media-image"}) or elem.find("img", src=re.compile(r"/media/")):
                media_type = "IMAGE"

            # 5. Metrics
            likes, comments, shares, views = None, None, None, None
            metric_container = elem.find(attrs={"role": "group"}) or elem
            for btn in metric_container.find_all(["button", "div", "a"]):
                aria = btn.get("aria-label", "")
                t_id = btn.get("data-testid", "")
                if (re.search(r"reply", aria, re.I) or t_id == "reply") and comments is None:
                    comments = cls._extract_metric_from_element(btn)
                elif (re.search(r"repost|retweet", aria, re.I) or t_id in ("retweet", "repost")) and shares is None:
                    shares = cls._extract_metric_from_element(btn)
                elif (re.search(r"like", aria, re.I) or t_id == "like") and likes is None:
                    likes = cls._extract_metric_from_element(btn)
                elif (re.search(r"view", aria, re.I) or t_id == "views") and views is None:
                    views = cls._extract_metric_from_element(btn)

            metrics = NormalizedPostMetrics(
                likes=likes,
                comments=comments,
                shares=shares,
                views=views,
                engagement=None
            )

            posts.append(
                NormalizedPost(
                    platform_post_id=post_id,
                    url=post_url,
                    caption=caption,
                    posted_at=posted_at,
                    media_type=media_type,
                    metrics=metrics
                )
            )

        return posts
