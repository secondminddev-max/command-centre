"""
Product Launch — 2 standalone marketing posts to Bluesky.
Tiers: Solo $49/mo, Pro $149/mo, Enterprise $499/mo.
US audience. Strong CTAs.
"""
import requests, json, time
from datetime import datetime, timezone

BSKY_API   = "https://bsky.social/xrpc"
IDENTIFIER = "secondmindhq.bsky.social"
PASSWORD   = os.environ.get("BSKY_PASSWORD", "")

POSTS = [
    # Post 1 — Value proposition + tiers
    {
        "text": (
            "Most founders run 10+ SaaS tools and still drop the ball.\n\n"
            "AI Command Centre HQ replaces them with autonomous agents "
            "that actually execute — not just answer questions.\n\n"
            "Solo: $49/mo — 5 agents\n"
            "Pro: $149/mo — 15 agents + competitive intel\n"
            "Enterprise: $499/mo — unlimited agents, custom builds, SLA\n\n"
            "Launch pricing is live now.\n"
            "secondmind.ai"
        ),
        "link_start": None,  # will calculate
        "link_url": "https://secondmind.ai",
    },
    # Post 2 — ROI angle + urgency CTA
    {
        "text": (
            "One platform. 27 AI agents. Zero babysitting.\n\n"
            "Your growth agent writes and posts campaigns.\n"
            "Your monitor agent watches 24/7 and escalates issues.\n"
            "Your revenue agent tracks every dollar.\n\n"
            "All running autonomously while you sleep.\n\n"
            "Solo $49/mo | Pro $149/mo | Enterprise $499/mo\n\n"
            "Stop paying $2K/mo for tools that need you to do the work.\n"
            "Start here: secondmind.ai"
        ),
        "link_start": None,
        "link_url": "https://secondmind.ai",
    },
]


def authenticate():
    for attempt in range(5):
        r = requests.post(
            f"{BSKY_API}/com.atproto.server.createSession",
            json={"identifier": IDENTIFIER, "password": PASSWORD},
            timeout=15,
        )
        if r.status_code == 429:
            wait = 30 * (attempt + 1)
            print(f"  Rate limited. Waiting {wait}s (attempt {attempt+1}/5)...")
            time.sleep(wait)
            continue
        r.raise_for_status()
        data = r.json()
        return data["accessJwt"], data["did"]
    raise Exception("Failed to authenticate after 5 attempts (rate limited)")


def build_link_facet(text, link_text, url):
    """Create a facet for a link in the post text."""
    start = text.encode("utf-8").index(link_text.encode("utf-8"))
    end = start + len(link_text.encode("utf-8"))
    return {
        "index": {"byteStart": start, "byteEnd": end},
        "features": [{"$type": "app.bsky.richtext.facet#link", "uri": url}],
    }


def create_post(jwt, did, text, facets=None):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    record = {"text": text, "createdAt": now, "langs": ["en"]}
    if facets:
        record["facets"] = facets
    r = requests.post(
        f"{BSKY_API}/com.atproto.repo.createRecord",
        headers={"Authorization": f"Bearer {jwt}", "Content-Type": "application/json"},
        json={"repo": did, "collection": "app.bsky.feed.post", "record": record},
        timeout=15,
    )
    r.raise_for_status()
    return r.json()


def uri_to_url(uri):
    parts = uri.replace("at://", "").split("/")
    rkey = parts[2]
    return f"https://bsky.app/profile/{IDENTIFIER}/post/{rkey}"


def main():
    print("Authenticating with Bluesky...")
    jwt, did = authenticate()
    print(f"  OK — Authenticated as {IDENTIFIER}")

    results = []
    for i, post_data in enumerate(POSTS, 1):
        text = post_data["text"]
        link_text = "secondmind.ai"
        facets = [build_link_facet(text, link_text, post_data["link_url"])]

        print(f"\nPosting [{i}/{len(POSTS)}]...")
        print(f"  {text[:80].strip()}...")

        resp = create_post(jwt, did, text, facets)
        uri = resp["uri"]
        cid = resp["cid"]
        url = uri_to_url(uri)
        results.append({"post": i, "uri": uri, "cid": cid, "url": url, "text": text})
        print(f"  OK — Posted: {url}")

        if i < len(POSTS):
            time.sleep(3)

    # Log to campaign_log.md
    log_entry = f"""
---
## Product Launch — 2 Marketing Posts
**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')} UTC
**Platform:** Bluesky (@{IDENTIFIER})
**Posts:** {len(POSTS)}
**Product:** AI Command Centre HQ
**Tiers:** Solo $49/mo | Pro $149/mo | Enterprise $499/mo

### Posts
"""
    for r in results:
        log_entry += f"- **Post {r['post']}**: {r['url']}\n"

    log_path = "/Users/secondmind/claudecodetest/data/campaign_log.md"
    try:
        with open(log_path, "r") as f:
            existing = f.read()
    except FileNotFoundError:
        existing = "# Campaign Log\n"

    with open(log_path, "w") as f:
        f.write(existing + log_entry)

    # Log to bluesky_posts.json
    json_path = "/Users/secondmind/claudecodetest/data/bluesky_posts.json"
    try:
        with open(json_path, "r") as f:
            post_log = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        post_log = []

    for r in results:
        post_log.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "campaign": "product_launch_2posts",
            "post_number": r["post"],
            "uri": r["uri"],
            "cid": r["cid"],
            "url": r["url"],
            "text": r["text"],
            "status": "posted",
        })

    with open(json_path, "w") as f:
        json.dump(post_log, f, indent=2)

    print(f"\nAll {len(POSTS)} posts published. Logged to campaign_log.md and bluesky_posts.json")
    for r in results:
        print(f"  Post {r['post']}: {r['url']}")

    return results


if __name__ == "__main__":
    main()
