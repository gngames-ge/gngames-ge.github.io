#!/usr/bin/env python3
"""Two-way news sync between the website (news/posts.json) and the GN Racing GE Facebook Page.

- Site -> Facebook: every post with "facebook": true and no "fb_id" is published on the Page
  (its images and the caption built from the KA + EN text), and its new fb_id is written back.
- Facebook -> site: Page posts that the site does not know yet are added to posts.json
  (text, date, picture saved under img/news/fb/, link to the post).
- news/feed.xml is rebuilt from posts.json every run.

Needs the secret FB_PAGE_TOKEN (a Page access token with pages_manage_posts and
pages_read_engagement) and the variable FB_PAGE_ID. Without a token it only rebuilds the feed.
"""
import json, os, sys, urllib.parse, urllib.request
from datetime import datetime, timezone
from email.utils import format_datetime
from xml.sax.saxutils import escape

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
POSTS = os.path.join(ROOT, "news", "posts.json")
FEED = os.path.join(ROOT, "news", "feed.xml")
SITE = "https://gngames-ge.github.io"
API = "https://graph.facebook.com/" + os.environ.get("FB_API_VERSION", "v23.0")
TOKEN = os.environ.get("FB_PAGE_TOKEN", "").strip()
PAGE = os.environ.get("FB_PAGE_ID", "").strip()
# Page posts older than this are already on the site by hand: never pull them.
SINCE = os.environ.get("FB_PULL_SINCE") or "2026-10-27"


def call(path, params=None, post=False):
    params = dict(params or {}, access_token=TOKEN)
    data = urllib.parse.urlencode(params).encode()
    if post:
        req = urllib.request.Request(API + path, data=data, method="POST")
    else:
        req = urllib.request.Request(API + path + "?" + data.decode())
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def abs_url(src):
    return src if src.startswith("http") else SITE + "/" + src.lstrip("./").replace("../", "")


def caption(p):
    t = p.get("title", {})
    b = p.get("body", {})
    parts = []
    for lang in ("ka", "en"):
        head = t.get(lang, "")
        text = b.get(lang, "")
        if head or text:
            parts.append((head + "\n" + text).strip())
    link = SITE + "/news/#" + p["id"]
    return "\n\n".join(parts + [link])


def push(posts):
    changed = False
    for p in posts:
        if not p.get("facebook") or p.get("fb_id") or p.get("source") == "facebook":
            continue
        images = [abs_url(i) for i in p.get("images", [])]
        msg = caption(p)
        if len(images) <= 1:
            if images:
                r = call("/%s/photos" % PAGE, {"url": images[0], "caption": msg}, post=True)
                p["fb_id"] = r.get("post_id") or r.get("id")
            else:
                p["fb_id"] = call("/%s/feed" % PAGE, {"message": msg}, post=True)["id"]
        else:
            media = []
            for u in images:
                r = call("/%s/photos" % PAGE, {"url": u, "published": "false"}, post=True)
                media.append({"media_fbid": r["id"]})
            params = {"message": msg}
            for i, m in enumerate(media):
                params["attached_media[%d]" % i] = json.dumps(m)
            p["fb_id"] = call("/%s/feed" % PAGE, params, post=True)["id"]
        print("posted to Facebook:", p["id"], p["fb_id"])
        changed = True
    return changed


def pull(posts):
    known = {p.get("fb_id") for p in posts if p.get("fb_id")}
    r = call("/%s/posts" % PAGE, {"fields": "id,message,created_time,full_picture,permalink_url", "limit": 25})
    added = False
    os.makedirs(os.path.join(ROOT, "img", "news", "fb"), exist_ok=True)
    for fp in r.get("data", []):
        if fp["id"] in known or not fp.get("message") or fp["created_time"][:10] < SINCE:
            continue
        pid = "fb-" + fp["id"].split("_")[-1]
        images = []
        if fp.get("full_picture"):
            rel = "img/news/fb/%s.jpg" % pid
            urllib.request.urlretrieve(fp["full_picture"], os.path.join(ROOT, rel))
            images.append("../" + rel)
        text = fp["message"].strip()
        first, _, rest = text.partition("\n")
        posts.append({
            "id": pid,
            "date": fp["created_time"][:10],
            "title": {"ka": first[:120]},
            "body": {"ka": rest.strip()},
            "images": images,
            "link": fp.get("permalink_url", ""),
            "source": "facebook",
            "fb_id": fp["id"],
        })
        print("pulled from Facebook:", pid)
        added = True
    return added


def feed(posts):
    items = []
    for p in posts:
        if p.get("draft"):
            continue
        t = p.get("title", {})
        b = p.get("body", {})
        title = t.get("en") or t.get("ka") or ""
        desc = b.get("en") or b.get("ka") or ""
        dt = datetime.strptime(p["date"], "%Y-%m-%d").replace(hour=18, tzinfo=timezone.utc)
        img = p.get("images", [])
        media = '\n    <media:content url="%s" medium="image"/>' % escape(abs_url(img[0])) if img else ""
        items.append("""  <item>
    <title>%s</title>
    <link>%s/news/#%s</link>
    <guid isPermaLink="false">gn-news-%s</guid>
    <pubDate>%s</pubDate>
    <description>%s</description>%s
  </item>""" % (escape(title), SITE, p["id"], p["id"], format_datetime(dt), escape(desc), media))
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:media="http://search.yahoo.com/mrss/">
<channel>
  <title>GN Games News</title>
  <link>%s/news/</link>
  <description>GN Racing GE updates, new cars and modes from GN Games, Georgia.</description>
  <language>en</language>
%s
</channel>
</rss>
""" % (SITE, "\n".join(items))
    with open(FEED, "w", encoding="utf-8") as f:
        f.write(xml)


def main():
    with open(POSTS, encoding="utf-8") as f:
        posts = json.load(f)
    if TOKEN and PAGE:
        push([p for p in posts if not p.get("draft")])
        pull(posts)
    else:
        print("FB_PAGE_TOKEN or FB_PAGE_ID missing: only the feed is rebuilt", file=sys.stderr)
    posts.sort(key=lambda p: p["date"], reverse=True)
    with open(POSTS, "w", encoding="utf-8") as f:
        json.dump(posts, f, ensure_ascii=False, indent=2)
        f.write("\n")
    feed(posts)


if __name__ == "__main__":
    main()
