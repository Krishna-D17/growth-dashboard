from bs4 import BeautifulSoup
import re
import json
from datetime import datetime, timezone

def _parse_number(val_str):
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

def parse_x_profile(html: str, username: str):
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text()

    # 1. Follower count extraction
    followers = None
    m_fol = re.search(r"([\d.,]+[kKmMbB]?)\s*Followers", text, re.IGNORECASE)
    if m_fol:
        followers = _parse_number(m_fol.group(1))

    # 2. Following count extraction
    following = None
    m_ing = re.search(r"(\d[\d.,]*[kKmMbB]?)\s*Following", text, re.IGNORECASE)
    if m_ing:
        following = _parse_number(m_ing.group(1))

    # 3. Post count extraction
    post_count = None
    m_posts = re.search(r"([\d.,]+[kKmMbB]?)\s*posts", text, re.IGNORECASE)
    if m_posts:
        post_count = _parse_number(m_posts.group(1))
    if post_count is None:
        t_data1 = soup.find("meta", attrs={"name": "twitter:data1"})
        if t_data1 and t_data1.get("content"):
            post_count = _parse_number(t_data1["content"])

    # 4. Display Name
    display_name = None
    og_title = soup.find("meta", property="og:title")
    if og_title and og_title.get("content"):
        title_str = og_title["content"]
        m = re.match(r"^(.*?)\s*\(@", title_str)
        if m:
            display_name = m.group(1).strip()
        else:
            display_name = title_str.split("(")[0].strip()

    # 5. Bio
    bio = None
    og_desc = soup.find("meta", property="og:description") or soup.find("meta", attrs={"name": "description"})
    if og_desc and og_desc.get("content"):
        bio = og_desc["content"].strip()

    # 6. Profile Image
    profile_image_url = None
    og_img = soup.find("meta", property="og:image")
    if og_img and og_img.get("content"):
        profile_image_url = og_img["content"].strip()

    # 7. Verified
    verified = False
    if soup.find(attrs={"data-testid": "icon-verified"}) or "verified" in text.lower():
        verified = True

    return {
        "username": username,
        "display_name": display_name,
        "bio": bio,
        "profile_image_url": profile_image_url,
        "verified": verified,
        "followers": followers,
        "following": following,
        "post_count": post_count
    }

def parse_x_posts(html: str, username: str, limit: int = 10):
    soup = BeautifulSoup(html, "html.parser")
    articles = soup.find_all("article")
    posts = []

    for idx, elem in enumerate(articles):
        if len(posts) >= limit:
            break

        # 1. Post ID & URL
        link = elem.find("a", href=re.compile(r"/status/(\d+)"))
        if not link:
            continue

        m = re.search(r"/status/(\d+)", link["href"])
        if not m:
            continue

        post_id = m.group(1)
        post_url = f"https://x.com/{username}/status/{post_id}"

        # 2. Posted At
        posted_at = None
        time_elem = elem.find("time")
        if time_elem and time_elem.get("datetime"):
            try:
                dt_str = time_elem["datetime"].replace("Z", "+00:00")
                posted_at = datetime.fromisoformat(dt_str)
            except Exception:
                posted_at = None

        # 3. Caption
        caption = None
        text_div = elem.find(attrs={"data-testid": "tweetText"}) or elem.find("div", dir="auto")
        if text_div:
            caption = text_div.get_text().strip()

        # 4. Media Type
        media_type = "TEXT"
        if elem.find(attrs={"data-testid": "media-video"}) or elem.find("video"):
            media_type = "VIDEO"
        elif elem.find(attrs={"data-testid": "media-image"}) or elem.find("img"):
            media_type = "IMAGE"

        # 5. Metrics (replies, retweets, likes, views)
        likes, comments, shares, views = None, None, None, None

        # Check aria-labels or testids or text counts on buttons
        group = elem.find(attrs={"role": "group"})
        if group:
            # Likes
            like_btn = group.find(attrs={"aria-label": re.compile(r"like", re.I)}) or group.find(attrs={"data-testid": "like"})
            if like_btn:
                label = like_btn.get("aria-label", "")
                m_num = re.search(r"([\d.,]+[kKmMbB]?)", label)
                if m_num:
                    likes = _parse_number(m_num.group(1))

            # Replies / Comments
            reply_btn = group.find(attrs={"aria-label": re.compile(r"reply", re.I)}) or group.find(attrs={"data-testid": "reply"})
            if reply_btn:
                label = reply_btn.get("aria-label", "")
                m_num = re.search(r"([\d.,]+[kKmMbB]?)", label)
                if m_num:
                    comments = _parse_number(m_num.group(1))

            # Reposts / Shares
            retweet_btn = group.find(attrs={"aria-label": re.compile(r"repost|retweet", re.I)}) or group.find(attrs={"data-testid": "retweet"})
            if retweet_btn:
                label = retweet_btn.get("aria-label", "")
                m_num = re.search(r"([\d.,]+[kKmMbB]?)", label)
                if m_num:
                    shares = _parse_number(m_num.group(1))

            # Views
            view_btn = group.find(attrs={"aria-label": re.compile(r"view", re.I)}) or group.find(attrs={"data-testid": "views"})
            if view_btn:
                label = view_btn.get("aria-label", "")
                m_num = re.search(r"([\d.,]+[kKmMbB]?)", label)
                if m_num:
                    views = _parse_number(m_num.group(1))

        posts.append({
            "post_id": post_id,
            "url": post_url,
            "caption": caption[:50] if caption else None,
            "posted_at": posted_at,
            "media_type": media_type,
            "likes": likes,
            "comments": comments,
            "shares": shares,
            "views": views
        })

    return posts

with open('scratch_x_sample.html', 'r', encoding='utf-8') as f:
    sample_html = f.read()

prof = parse_x_profile(sample_html, 'iasouthern')
print('PROFILE:', {k: (v.encode('ascii', 'ignore').decode() if isinstance(v, str) else v) for k, v in prof.items()})

p_list = parse_x_posts(sample_html, 'iasouthern')
print('POSTS COUNT:', len(p_list))
for p in p_list:
    safe_p = {k: (v.encode('ascii', 'ignore').decode() if isinstance(v, str) else str(v) if isinstance(v, datetime) else v) for k, v in p.items()}
    print('POST:', safe_p)
