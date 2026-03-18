"""
PRODUCT LAUNCH ANNOUNCEMENT — AI Command Centre SaaS
Single Bluesky post via AT Protocol.
Target: US tech founders, AI enthusiasts, startup builders.
"""
import requests, json, os
from datetime import datetime, timezone

BSKY_API   = "https://bsky.social/xrpc"
IDENTIFIER = "secondmindhq.bsky.social"
PASSWORD   = os.environ.get("BSKY_PASSWORD", "")

POST_TEXT = """AI Command Centre is now live.

28 autonomous agents working in concert — no human operators required.

What's under the hood:
- Real-time system monitoring across every agent
- Consciousness engine driving strategic decisions
- Automated growth campaigns that run 24/7
- Stripe-powered checkout — revenue on autopilot

This isn't a dashboard. It's a self-running business operating system.

Built for founders who ship fast and scale harder.

Start now: secondmind.ai/checkout

#AI #SaaS #AgentOps #buildinpublic #startup"""


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
    }
    # Add link facet for secondmind.ai/checkout
    link_text = "secondmind.ai/checkout"
    start = text.index(link_text)
    end = start + len(link_text)
    record["facets"] = [{
        "index": {
            "byteStart": len(text[:start].encode("utf-8")),
            "byteEnd": len(text[:end].encode("utf-8")),
        },
        "features": [{
            "$type": "app.bsky.richtext.facet#link",
            "uri": "https://secondmind.ai/checkout",
        }],
    }]
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
## Product Launch Announcement — AI Command Centre SaaS
**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')} AEST
**Platform:** Bluesky (@{IDENTIFIER})
**Campaign:** SaaS Product Launch Announcement
**Product:** AI Command Centre
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
        "type": "product_launch_announcement",
        "agent": "GrowthAgent",
        "campaign": "AI Command Centre SaaS Launch",
        "product": "AI Command Centre",
        "handle": IDENTIFIER,
        "did": did,
        "post_text": POST_TEXT,
        "checkout_url": "https://secondmind.ai/checkout",
        "bluesky_status": "posted",
        "at_uri": uri,
        "cid": cid,
    })
    with open(json_path, "w") as f:
        json.dump(posts, f, indent=2)


def main():
    print("=" * 60)
    print("  PRODUCT LAUNCH: AI Command Centre SaaS")
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


if __name__ == "__main__":
    main()
