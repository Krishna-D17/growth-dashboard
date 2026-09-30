from bs4 import BeautifulSoup
import json
import re

with open('scratch_x_sample.html', 'r', encoding='utf-8') as f:
    html = f.read()

soup = BeautifulSoup(html, 'html.parser')

output = []

output.append("=== TITLE ===")
output.append(str(soup.title.string if soup.title else "No title"))

output.append("\n=== META TAGS ===")
for meta in soup.find_all('meta'):
    p = meta.get('property') or meta.get('name') or meta.get('itemprop')
    c = meta.get('content')
    if c:
        output.append(f"{p}: {c}")

output.append("\n=== SCRIPTS ===")
for i, s in enumerate(soup.find_all('script')):
    stype = s.get('type') or 'text/javascript'
    text = s.string or ''
    output.append(f"Script {i}: type={stype}, length={len(text)}")
    if 'ld+json' in stype:
        output.append(f"JSON-LD Content: {text[:1000]}")
    elif 'followers' in text.lower() or 'following' in text.lower() or 'tweet' in text.lower():
        output.append(f"Matching text snippet: {text[:300]}")

output.append("\n=== ARTICLES / TWEET ELEMENTS ===")
articles = soup.find_all('article')
output.append(f"Article elements count: {len(articles)}")
for i, a in enumerate(articles):
    output.append(f"Article {i} text: {a.get_text()[:200]}")

output.append("\n=== LINKS WITH /STATUS/ ===")
status_links = soup.find_all('a', href=re.compile(r'/status/\d+'))
output.append(f"Status links count: {len(status_links)}")
for i, link in enumerate(status_links[:10]):
    output.append(f"Link {i}: href={link['href']}, text={link.get_text()[:100]}")

output.append("\n=== BODY TEXT SNIPPET ===")
output.append(soup.get_text()[:2000])

with open('scratch_x_analysis.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(output))

print("Wrote scratch_x_analysis.txt cleanly")
