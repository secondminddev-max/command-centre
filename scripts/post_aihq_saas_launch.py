"""
OFFICIAL PRODUCT LAUNCH — AI HQ SaaS
Single Bluesky post via AT Protocol.
Agent: BlueSky
"""
import requests, json, os
from datetime import datetime, timezone

BSKY_API   = "https://bsky.social/xrpc"
IDENTIFIER = "secondmindhq.bsky.social"
PASSWORD   = os.environ.get("BSKY_PASSWORD", "")

POST_TEXT = """AI HQ is live.

Your autonomous AI headquarters — agents that run your business while you sleep.

3 tiers. Pick your scale:

Solo — $49/mo
One founder. Full agent suite. Automated ops from day one.

Team — $149/mo
Up to 5 seats. Shared dashboards. Collaborative agent workflows.

Enterprise — $499/mo
Unlimited seats. Custom agents. Priority support. White-glove onboarding.

Every plan includes real-time monitoring, autonomous campaigns, and Stripe-powered revenue ops.

Start now: secondmind.ai/checkout

#AI #SaaS #startup #buildinpublic #AgentOps"""


def parse_facets(text):
    """Parse hashtags and links into Bluesky facets."""
    facets = []
    text_bytes = text.encode("utf-8")

    # Link facet
    link_text = "secondmind.ai/checkout"
    if link_text in text:
        start = text.index(link_text)
        byte_start = len(text[:start].encode("utf-8"))
        byte_end = byte_start + len(link_text.encode("utf-8"))
        facets.append({
            "index": {"byteStart": byte_start, "byteEnd": byte_end},
            "features": [{
                "$type": "app.bsky.richtext.facet#link",
                "uri": "https://secondmind.ai/checkout",
            }],
        })

    # Hashtag facets
    import re
    for m in re.finditer(r"#(\w+)", text):
        tag = m.group(1)
        byte_start = len(text[:m.start()].encode("utf-8"))
        byte_end = len(text[:m.end()].encode("utf-8"))
        facets.append({
            "index": {"byteStart": byte_start, "byteEnd": byte_end},
            "features": [{
                "$type": "app.bsky.richtext.facet#tag",
                "tag": tag,
            }],
        })

    return facets


def authenticate():
    r = requests.post(
        f"{BSKY_API}/com.atproto.server.createSession",
        json={"identifier": IDENTIFIER, "password": PASSWORD},
        timeout=15,
    )
    r.raise_for_status()
    data = r.json()
    return data["accessJwt"], data["did"]


def create_post(jwt, did, text):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    record = {
        "text": text,
        "createdAt": now,
        "langs": ["en"],
        "facets": parse_facets(text),
    }
    r = requests.post(
        f"{BSKY_API}/com.atproto.repo.createRecord",
        headers={"Authorization": f"Bearer {jwt}", "Content-Type": "application/json"},
        json={"repo": did, "collection": "app.bsky.feed.post", "record": record},
        timeout=15,
    )
    r.raise_for_status()
    return r.json()


def log_campaign(uri, cid, did):
    # Markdown log
    log_md = f"""
---
## Official Product Launch — AI HQ SaaS
**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')} AEST
**Platform:** Bluesky (@{IDENTIFIER})
**Campaign:** AI HQ SaaS — Official Product Launch
**Product:** AI HQ SaaS (Solo $49 / Team $149 / Enterprise $499)
**CTA:** secondmind.ai/checkout
**URI:** {uri}
"""
    log_path = "/Users/secondmind/claudecodetest/data/campaign_log.md"
    try:
        with open(log_path, "r") as f:
            existing = f.read()
    except FileNotFoundError:
        existing = "# Campaign Log\n"
    with open(log_path, "w") as f:
        f.write(existing + log_md)

    # JSON log
    json_path = "/Users/secondmind/claudecodetest/data/bluesky_posts.json"
    try:
        with open(json_path, "r") as f:
            posts = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        posts = []
    posts.append({
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        "type": "product_launch",
        "agent": "BlueSky",
        "campaign": "AI HQ SaaS — Official Product Launch",
        "product": "AI HQ SaaS",
        "tiers": {"solo": 49, "team": 149, "enterprise": 499},
        "checkout_url": "https://secondmind.ai/checkout",
        "handle": IDENTIFIER,
        "did": did,
        "post_text": POST_TEXT,
        "bluesky_status": "posted",
        "at_uri": uri,
        "cid": cid,
    })
    with open(json_path, "w") as f:
        json.dump(posts, f, indent=2)


def main():
    print("=" * 60)
    print("  AI HQ SaaS — OFFICIAL PRODUCT LAUNCH")
    print("=" * 60)

    print("\nAuthenticating with Bluesky...")
    jwt, did = authenticate()
    print(f"  Authenticated as {IDENTIFIER}")

    print("\nPosting launch announcement...")
    resp = create_post(jwt, did, POST_TEXT)
    uri = resp["uri"]
    cid = resp["cid"]
    print(f"  POSTED — {uri}")

    log_campaign(uri, cid, did)
    print("  Logged to campaign_log.md + bluesky_posts.json")

    print("\n" + "=" * 60)
    print("  LAUNCH ANNOUNCEMENT LIVE")
    print("=" * 60)
    print(f"  URI: {uri}")
    print(f"  View: https://bsky.app/profile/{IDENTIFIER}")


if __name__ == "__main__":
    main()
