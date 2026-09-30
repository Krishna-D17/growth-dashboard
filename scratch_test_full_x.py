from bs4 import BeautifulSoup
import re
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

    followers, following, post_count = None, None, None

    m_fol = re.search(r"([\d.,]+[kKmMbB]?)\s*Followers", text, re.IGNORECASE)
    if m_fol:
        followers = _parse_number(m_fol.group(1))

    m_ing = re.search(r"(\d[\d.,]*[kKmMbB]?)\s*Following", text, re.IGNORECASE)
    if m_ing:
        following = _parse_number(m_ing.group(1))

    m_posts = re.search(r"([\d.,]+[kKmMbB]?)\s*posts", text, re.IGNORECASE)
    if m_posts:
        post_count = _parse_number(m_posts.group(1))
    if post_count is None:
        t_data1 = soup.find("meta", attrs={"name": "twitter:data1"})
        if t_data1 and t_data1.get("content"):
            post_count = _parse_number(t_data1["content"])

    display_name = None
    og_title = soup.find("meta", property="og:title")
    if og_title and og_title.get("content"):
        title_str = og_title["content"]
        m = re.match(r"^(.*?)\s*\(@", title_str)
        if m:
            display_name = m.group(1).strip()
        else:
            display_name = title_str.split("(")[0].strip()

    bio = None
    og_desc = soup.find("meta", property="og:description") or soup.find("meta", attrs={"name": "description"})
    if og_desc and og_desc.get("content"):
        bio = og_desc["content"].strip()

    profile_image_url = None
    og_img = soup.find("meta", property="og:image")
    if og_img and og_img.get("content"):
        profile_image_url = og_img["content"].strip()

    verified = False
    if soup.find(attrs={"data-testid": "icon-verified"}) or "verified" in text.lower():
        verified = True

    return {
        "username": username,
        "display_name": display_name,
        "bio": bio[:60] if bio else None,
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
    seen_ids = set()

    for idx, elem in enumerate(articles):
        if len(posts) >= limit:
            break

        link = elem.find("a", href=re.compile(r"/status/(\d+)"))
        if not link:
            continue

        m = re.search(r"/status/(\d+)", link["href"])
        if not m:
            continue

        post_id = m.group(1)
        if post_id in seen_ids:
            continue
        seen_ids.add(post_id)

        post_url = f"https://x.com/{username}/status/{post_id}"

        posted_at = None
        time_elem = elem.find("time")
        if time_elem and time_elem.get("datetime"):
            try:
                dt_str = time_elem["datetime"].replace("Z", "+00:00")
                posted_at = datetime.fromisoformat(dt_str)
            except Exception:
                posted_at = None

        caption = None
        text_div = elem.find(attrs={"data-testid": "tweetText"}) or elem.find("div", dir="auto")
        if text_div:
            caption = text_div.get_text().strip()

        media_type = "TEXT"
        if elem.find(attrs={"data-testid": "media-video"}) or elem.find("video"):
            media_type = "VIDEO"
        elif elem.find(attrs={"data-testid": "media-image"}) or elem.find("img", src=re.compile(r"/media/")):
            media_type = "IMAGE"

        likes, comments, shares, views = None, None, None, None

        # Extract metrics from aria-labels or group buttons
        group = elem.find(attrs={"role": "group"})
        if group:
            for btn in group.find_all(["button", "div", "a"]):
                aria = btn.get("aria-label", "")
                txt = btn.get_text()

                # Reply
                if re.search(r"reply", aria, re.I) or btn.get("data-testid") == "reply":
                    m_num = re.search(r"([\d.,]+[kKmMbB]?)", aria or txt)
                    if m_num and comments is None:
                        comments = _parse_number(m_num.group(1))
                # Repost
                elif re.search(r"repost|retweet", aria, re.I) or btn.get("data-testid") == "retweet":
                    m_num = re.search(r"([\d.,]+[kKmMbB]?)", aria or txt)
                    if m_num and shares is None:
                        shares = _parse_number(m_num.group(1))
                # Like
                elif re.search(r"like", aria, re.I) or btn.get("data-testid") == "like":
                    m_num = re.search(r"([\d.,]+[kKmMbB]?)", aria or txt)
                    if m_num and likes is None:
                        likes = _parse_number(m_num.group(1))
                # View
                elif re.search(r"view", aria, re.I) or btn.get("data-testid") == "views":
                    m_num = re.search(r"([\d.,]+[kKmMbB]?)", aria or txt)
                    if m_num and views is None:
                        views = _parse_number(m_num.group(1))

        posts.append({
            "post_id": post_id,
            "url": post_url,
            "caption": caption[:40] if caption else None,
            "posted_at": str(posted_at) if posted_at else None,
            "media_type": media_type,
            "likes": likes,
            "comments": comments,
            "shares": shares,
            "views": views
        })

    return posts

with open("scratch_x_sample.html", "r", encoding="utf-8") as f:
    html = f.read()

prof = parse_x_profile(html, "iasouthern")
print("PROFILE PARSED:", prof)

posts = parse_x_posts(html, "iasouthern")
print(f"POSTS PARSED ({len(posts)} posts):")
for p in posts:
    safe_p = {k: (v.encode('ascii', 'ignore').decode() if isinstance(v, str) else v) for k, v in p.items()}
    print(" ", safe_p)
