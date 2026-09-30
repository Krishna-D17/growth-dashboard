import re
import json
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from bs4 import BeautifulSoup

from app.models.enums import SocialPlatform
from app.schemas.collector import NormalizedProfile, NormalizedPost, NormalizedPostMetrics
from app.collectors.exceptions import ContentUnavailableError, RateLimitError, TargetValidationError


class FacebookParser:
    """
    Parser for public Facebook Page HTML pages and metadata structures.
    Extracts Page metadata, verified status, follower/like counts,
    and public posts into normalized schema structures.
    Does NOT support private or personal Facebook profiles.
    """

    @staticmethod
    def _parse_number(val: Optional[str]) -> Optional[int]:
        """Convert metric string (e.g., '450,000', '520K', '1.2M', '3.2K') into integer."""
        if not val:
            return None
        clean_val = str(val).strip().replace(",", "")
        if not clean_val:
            return None

        # Extract number part
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
    def parse_profile(cls, html_content: str, username: str, profile_url: str) -> NormalizedProfile:
        """
        Parse profile metadata from Facebook Page HTML content.
        Raises ContentUnavailableError or RateLimitError if account is unavailable or rate limited.
        Raises TargetValidationError if target is an unsupported personal profile.
        """
        if not html_content or not html_content.strip():
            raise ContentUnavailableError(f"Empty HTML content received for Facebook Page '{username}'")

        soup = BeautifulSoup(html_content, "html.parser")
        text_content = soup.get_text().lower()

        # 1. Rate Limit Detection
        if "rate limit" in text_content or "too many requests" in text_content:
            raise RateLimitError(f"Rate limit hit while accessing Facebook Page '{username}'")

        # 2. Page Availability Detection
        if "this page isn't available" in text_content or "page not found" in text_content or \
           "content not found" in text_content or "page removed" in text_content:
            raise ContentUnavailableError(f"Facebook Page '{username}' does not exist or is unavailable")

        # 3. Login Wall Detection
        title_text = soup.title.string.lower() if soup.title and soup.title.string else ""
        if "log into facebook" in title_text or "log in to facebook" in title_text or \
           "you must log in to continue" in text_content:
            raise ContentUnavailableError(f"Public access restricted by Facebook login wall for Page '{username}'")

        # 4. Personal Profile Rejection (SocialScope supports Facebook Pages only)
        og_type_tag = soup.find("meta", property="og:type")
        og_type_str = og_type_tag["content"].lower() if (og_type_tag and og_type_tag.get("content")) else ""
        if "personal profile" in text_content or "this target is a personal profile" in text_content or og_type_str == "profile":
            raise TargetValidationError(f"Target '{username}' is a personal profile. SocialScope supports Facebook Pages only.")

        clean_slug = username.strip().lower()

        # 5. Platform Profile ID (Genuine ID or None - NEVER fabricated UUID)
        platform_profile_id = None
        page_id_meta = soup.find("meta", property="page:id") or soup.find("meta", attrs={"name": "page_id"})
        if page_id_meta and page_id_meta.get("content"):
            platform_profile_id = page_id_meta["content"].strip()

        if not platform_profile_id:
            al_url = soup.find("meta", property="al:android:url") or soup.find("meta", property="al:ios:url")
            if al_url and al_url.get("content"):
                m = re.search(r"fb://(?:page|profile)/(\d+)", al_url["content"])
                if m:
                    platform_profile_id = m.group(1)

        if not platform_profile_id:
            for script in soup.find_all("script", type="application/ld+json"):
                try:
                    data = json.loads(script.string or "{}")
                    if isinstance(data, dict) and data.get("identifier"):
                        platform_profile_id = str(data["identifier"]).strip()
                        break
                except (json.JSONDecodeError, TypeError):
                    continue

        # 6. Display Name
        display_name = None
        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):
            title_str = og_title["content"]
            display_name = re.sub(r"\s*-\s*Home\s*\|\s*Facebook$", "", title_str, flags=re.IGNORECASE).strip()

        if not display_name and soup.title and soup.title.string:
            title_str = soup.title.string
            display_name = re.sub(r"\s*-\s*Home\s*\|\s*Facebook$", "", title_str, flags=re.IGNORECASE).strip()

        page_name_h1 = soup.find(class_="page_name") or soup.find("h1")
        if page_name_h1 and page_name_h1.text.strip():
            display_name = page_name_h1.text.strip()

        # 7. Description / Bio
        bio = None
        og_desc = soup.find("meta", property="og:description") or soup.find("meta", attrs={"name": "description"})
        if og_desc and og_desc.get("content"):
            bio = og_desc["content"].strip()

        bio_div = soup.find(class_="page_bio")
        if bio_div:
            bio = bio_div.get_text().strip()

        # 8. Profile Image URL
        profile_image_url = None
        og_img = soup.find("meta", property="og:image")
        if og_img and og_img.get("content"):
            profile_image_url = og_img["content"].strip()

        # 9. Verified Status
        verified = False
        if soup.find(class_="verified_badge") or soup.find(attrs={"aria-label": "Verified Page"}) or "verified page" in text_content:
            verified = True

        # 10. Followers, Page Likes, Post Count
        followers = None
        page_likes = None
        post_count = None

        followers_elem = soup.find(attrs={"data-testid": "page-followers"})
        if followers_elem:
            followers = cls._parse_number(followers_elem.get_text())

        likes_elem = soup.find(attrs={"data-testid": "page-likes"})
        if likes_elem:
            page_likes = cls._parse_number(likes_elem.get_text())

        # Fallback to description regex e.g. "450,000 likes · 520,000 followers"
        if og_desc and og_desc.get("content"):
            desc_str = og_desc["content"]
            if followers is None:
                m_fol = re.search(r"([\d.,]+[kKmMbB]?)\s+followers", desc_str, re.IGNORECASE)
                if m_fol:
                    followers = cls._parse_number(m_fol.group(1))

            if page_likes is None:
                m_likes = re.search(r"([\d.,]+[kKmMbB]?)\s+likes", desc_str, re.IGNORECASE)
                if m_likes:
                    page_likes = cls._parse_number(m_likes.group(1))

        # Fallback to JSON-LD
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string or "{}")
                if isinstance(data, dict):
                    interactions = data.get("interactionStatistic", [])
                    for item in interactions:
                        if item.get("interactionType") == "http://schema.org/FollowAction" and followers is None:
                            followers = cls._parse_number(str(item.get("userInteractionCount")))
                        elif item.get("interactionType") == "http://schema.org/LikeAction" and page_likes is None:
                            page_likes = cls._parse_number(str(item.get("userInteractionCount")))
            except (json.JSONDecodeError, TypeError):
                continue

        other_metrics = {}
        if page_likes is not None:
            other_metrics["page_likes"] = page_likes

        return NormalizedProfile(
            platform=SocialPlatform.FACEBOOK,
            username=clean_slug,
            profile_url=profile_url,
            platform_profile_id=platform_profile_id,
            display_name=display_name,
            bio=bio,
            profile_image_url=profile_image_url,
            verified=verified,
            followers=followers,
            following=None,  # Facebook Pages do not have a following count concept
            post_count=post_count,
            other_platform_metrics=other_metrics if other_metrics else None
        )

    @classmethod
    def _extract_post_metrics_from_scripts(cls, html_content: str, post_id: str) -> Dict[str, Optional[int]]:
        """
        Extract post interaction metrics (likes/reactions, comments, shares, views) from embedded Facebook script payloads.
        Maps total reactions count to likes field as documented in the SocialScope data model.
        Returns a dict of optional metric integers.
        """
        import base64
        likes = None
        comments = None
        shares = None
        views = None

        targets = [post_id]
        if post_id.startswith("fbid_"):
            targets.append(post_id.replace("fbid_", ""))
        try:
            b64_fb = base64.b64encode(f"feedback:{post_id}".encode()).decode()
            targets.append(b64_fb)
        except Exception:
            pass

        for target in targets:
            for m in re.finditer(re.escape(target), html_content):
                w_start = max(0, m.start() - 500)
                w_end = min(len(html_content), m.end() + 2500)
                window = html_content[w_start:w_end]

                # 1. Reactions / Likes (Total Reaction Count mapped to likes field)
                if likes is None:
                    m_rc = re.search(r'"reaction_count"\s*:\s*\{\s*"count"\s*:\s*(\d+)', window)
                    if m_rc:
                        likes = int(m_rc.group(1))
                    else:
                        m_rc2 = re.search(r'"reaction_count"\s*:\s*(\d+)', window)
                        if m_rc2:
                            likes = int(m_rc2.group(1))
                        else:
                            m_i18n = re.search(r'"i18n_reaction_count"\s*:\s*"([^"]+)"', window)
                            if m_i18n:
                                likes = cls._parse_number(m_i18n.group(1))

                # 2. Comments
                if comments is None:
                    m_cm = re.search(r'"comments"\s*:\s*\{\s*"total_count"\s*:\s*(\d+)', window)
                    if m_cm:
                        comments = int(m_cm.group(1))
                    else:
                        m_cm2 = re.search(r'"comment_count"\s*:\s*\{\s*"total_count"\s*:\s*(\d+)', window)
                        if m_cm2:
                            comments = int(m_cm2.group(1))
                        else:
                            m_i18n_cm = re.search(r'"i18n_comment_count"\s*:\s*"([^"]+)"', window)
                            if m_i18n_cm:
                                comments = cls._parse_number(m_i18n_cm.group(1))

                # 3. Shares
                if shares is None:
                    m_sh = re.search(r'"share_count"\s*:\s*\{\s*"count"\s*:\s*(\d+)', window)
                    if m_sh:
                        shares = int(m_sh.group(1))
                    else:
                        m_i18n_sh = re.search(r'"i18n_share_count"\s*:\s*"([^"]+)"', window)
                        if m_i18n_sh:
                            shares = cls._parse_number(m_i18n_sh.group(1))

                # 4. Views (video view count)
                if views is None:
                    m_vw = re.search(r'"video_view_count"\s*:\s*(\d+)', window)
                    if m_vw:
                        views = int(m_vw.group(1))

        return {
            "likes": likes,
            "comments": comments,
            "shares": shares,
            "views": views
        }

    @classmethod
    def parse_posts(cls, html_content: str, username: str, profile_url: str, limit: int = 10) -> List[NormalizedPost]:
        """
        Parse recent public posts from Facebook Page HTML content.
        Supports modern Facebook React/Relay DOM structures, script payloads,
        photo/video permalinks, as well as legacy userContentWrapper structures.
        Enriches post metrics from embedded script payloads.
        """
        if not html_content or not html_content.strip():
            return []

        clean_slug = username.strip().lower()
        soup = BeautifulSoup(html_content, "html.parser")
        posts_dict: Dict[str, NormalizedPost] = {}

        # Strategy 1: Legacy / Explicit DOM Post Elements (userContentWrapper, data-post-id)
        post_elements = soup.find_all("div", class_="userContentWrapper") or soup.find_all("div", attrs={"data-post-id": True})
        for idx, elem in enumerate(post_elements):
            if len(posts_dict) >= limit:
                break

            post_id = elem.get("data-post-id")
            if not post_id:
                link = elem.find("a", href=re.compile(r"/posts/([^/]+)"))
                if link:
                    m = re.search(r"/posts/([^/]+)", link["href"])
                    if m:
                        post_id = m.group(1)

            if not post_id:
                post_id = f"fb_post_{clean_slug}_{idx + 1}"

            post_url = f"https://www.facebook.com/{clean_slug}/posts/{post_id}" if not post_id.startswith("http") else post_id

            caption = None
            text_div = elem.find(class_="userContent") or elem.find(attrs={"data-testid": "post_message"})
            if text_div:
                caption = text_div.get_text().strip()

            posted_at = None
            time_elem = elem.find("abbr", class_="timestamp") or elem.find("abbr") or elem.find("time")
            if time_elem and time_elem.get("data-utime"):
                try:
                    epoch = int(time_elem["data-utime"])
                    posted_at = datetime.fromtimestamp(epoch, tz=timezone.utc)
                except ValueError:
                    pass

            media_type = "TEXT"
            if elem.find(class_="post_media") or elem.find("video") or elem.find("img"):
                if elem.find("video"):
                    media_type = "VIDEO"
                elif elem.find("img"):
                    media_type = "IMAGE"

            likes = None
            comments = None
            shares = None

            like_elem = elem.find(attrs={"data-testid": "like-count"})
            if like_elem:
                likes = cls._parse_number(like_elem.get_text())

            comment_elem = elem.find(attrs={"data-testid": "comment-count"})
            if comment_elem:
                comments = cls._parse_number(comment_elem.get_text())

            share_elem = elem.find(attrs={"data-testid": "share-count"})
            if share_elem:
                shares = cls._parse_number(share_elem.get_text())

            metrics = NormalizedPostMetrics(
                likes=likes,
                comments=comments,
                shares=shares,
                views=None,
                engagement=None
            )

            posts_dict[post_id] = NormalizedPost(
                platform_post_id=post_id,
                url=post_url,
                caption=caption,
                posted_at=posted_at,
                media_type=media_type,
                metrics=metrics
            )

        # Strategy 2: Anchor Permalinks in DOM (pfbid, photo, video, posts)
        if len(posts_dict) < limit:
            for a in soup.find_all("a", href=True):
                if len(posts_dict) >= limit:
                    break
                href = a["href"]

                m_pfbid = re.search(r"pfbid[A-Za-z0-9]+", href)
                m_fbid = re.search(r"[?&]fbid=(\d+)", href)
                m_post = re.search(r"/posts/(\d+)", href)

                pid = None
                if m_pfbid:
                    pid = m_pfbid.group(0)
                elif m_fbid:
                    pid = f"fbid_{m_fbid.group(1)}"
                elif m_post:
                    pid = m_post.group(1)

                if pid and pid not in posts_dict:
                    full_url = href if href.startswith("http") else f"https://www.facebook.com{href}"
                    aria = a.get("aria-label") or ""
                    text = a.get_text(strip=True)
                    caption = aria if aria else (text if len(text) > 10 else None)
                    mtype = "IMAGE" if "/photo" in href else ("VIDEO" if "/video" in href or "/watch" in href else "TEXT")

                    posts_dict[pid] = NormalizedPost(
                        platform_post_id=pid,
                        url=full_url,
                        caption=caption,
                        posted_at=None,
                        media_type=mtype,
                        metrics=NormalizedPostMetrics(likes=None, comments=None, shares=None, views=None, engagement=None)
                    )

        # Strategy 3: Embedded JSON Script Payloads (React/Relay Post Objects)
        if len(posts_dict) < limit:
            scripts = soup.find_all("script")
            for s in scripts:
                if len(posts_dict) >= limit:
                    break
                stext = s.string or s.text or ""
                if not stext or ("pfbid" not in stext and "post_id" not in stext and "creation_time" not in stext and "publish_time" not in stext):
                    continue

                # 3a. Extract pfbid post nodes
                for m_pf in re.finditer(r"(pfbid[A-Za-z0-9]+)", stext):
                    if len(posts_dict) >= limit:
                        break
                    pf_id = m_pf.group(1)
                    if pf_id in posts_dict:
                        continue

                    window = stext[max(0, m_pf.start() - 500): min(len(stext), m_pf.end() + 1000)]
                    
                    # Message / Caption
                    msg_match = re.search(r'"message":\s*\{\s*"text":\s*"((?:[^"\\]|\\.)*)"', window)
                    caption = None
                    if msg_match:
                        try:
                            caption = msg_match.group(1).encode("utf-8").decode("unicode_escape", errors="ignore").replace("\\n", "\n")
                        except Exception:
                            caption = msg_match.group(1)

                    # Timestamp
                    time_match = re.search(r'"(?:publish_time|creation_time)":\s*(\d{9,10})', window)
                    posted_at = None
                    if time_match:
                        try:
                            epoch = int(time_match.group(1))
                            posted_at = datetime.fromtimestamp(epoch, tz=timezone.utc)
                        except ValueError:
                            pass

                    mtype = "VIDEO" if "Video" in window or "playable_duration" in window else ("IMAGE" if "photo" in window or "image" in window else "TEXT")

                    posts_dict[pf_id] = NormalizedPost(
                        platform_post_id=pf_id,
                        url=f"https://www.facebook.com/{clean_slug}/posts/{pf_id}",
                        caption=caption,
                        posted_at=posted_at,
                        media_type=mtype,
                        metrics=NormalizedPostMetrics(likes=None, comments=None, shares=None, views=None, engagement=None)
                    )

                # 3b. Extract numeric post_id nodes
                for m_post in re.finditer(r'"post_id"\s*:\s*"(\d+)"', stext):
                    if len(posts_dict) >= limit:
                        break
                    post_num_id = m_post.group(1)
                    if post_num_id in posts_dict:
                        continue

                    window = stext[max(0, m_post.start() - 500): min(len(stext), m_post.end() + 1000)]
                    msg_match = re.search(r'"message":\s*\{\s*"text":\s*"((?:[^"\\]|\\.)*)"', window)
                    caption = None
                    if msg_match:
                        try:
                            caption = msg_match.group(1).encode("utf-8").decode("unicode_escape", errors="ignore").replace("\\n", "\n")
                        except Exception:
                            caption = msg_match.group(1)

                    time_match = re.search(r'"(?:publish_time|creation_time)":\s*(\d{9,10})', window)
                    posted_at = None
                    if time_match:
                        try:
                            epoch = int(time_match.group(1))
                            posted_at = datetime.fromtimestamp(epoch, tz=timezone.utc)
                        except ValueError:
                            pass

                    mtype = "VIDEO" if "Video" in window or "playable_duration" in window else ("IMAGE" if "photo" in window or "image" in window else "TEXT")

                    posts_dict[post_num_id] = NormalizedPost(
                        platform_post_id=post_num_id,
                        url=f"https://www.facebook.com/{clean_slug}/posts/{post_num_id}",
                        caption=caption,
                        posted_at=posted_at,
                        media_type=mtype,
                        metrics=NormalizedPostMetrics(likes=None, comments=None, shares=None, views=None, engagement=None)
                    )

        # Post-processing metric enrichment from embedded script payloads for all discovered posts
        for pid, post in posts_dict.items():
            script_metrics = cls._extract_post_metrics_from_scripts(html_content, pid)
            likes = post.metrics.likes if post.metrics and post.metrics.likes is not None else script_metrics["likes"]
            comments = post.metrics.comments if post.metrics and post.metrics.comments is not None else script_metrics["comments"]
            shares = post.metrics.shares if post.metrics and post.metrics.shares is not None else script_metrics["shares"]
            views = post.metrics.views if post.metrics and post.metrics.views is not None else script_metrics["views"]

            posts_dict[pid] = NormalizedPost(
                platform_post_id=post.platform_post_id,
                url=post.url,
                caption=post.caption,
                posted_at=post.posted_at,
                media_type=post.media_type,
                metrics=NormalizedPostMetrics(
                    likes=likes,
                    comments=comments,
                    shares=shares,
                    views=views,
                    engagement=None
                )
            )

        return list(posts_dict.values())

