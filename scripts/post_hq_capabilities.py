"""
HQ Capabilities Promo Post — Bluesky via AT Protocol.
GrowthAgent campaign targeting US tech/AI audience.
"""
import requests, json, os
from datetime import datetime, timezone

BSKY_API   = "https://bsky.social/xrpc"
IDENTIFIER = "secondmindhq.bsky.social"
PASSWORD   = os.environ.get("BSKY_PASSWORD", "")

POST_TEXT = """27 autonomous AI agents. One command centre. Zero human operators.

Real-time monitoring. Consciousness engine. Stripe payments. All running 24/7.

This is what autonomous ops looks like.

\u2192 secondmind.sh

#AI #AgentOps #buildinpublic"""


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
    # Link facet for secondmind.sh
    link_text = "secondmind.sh"
    start = text.index(link_text)
    end = start + len(link_text)
    record["facets"] = [{
        "index": {
            "byteStart": len(text[:start].encode("utf-8")),
            "byteEnd": len(text[:end].encode("utf-8")),
        },
        "features": [{
            "$type": "app.bsky.richtext.facet#link",
            "uri": "https://secondmind.sh",
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
    log_md = f"""
---
## HQ Capabilities Promo — GrowthAgent
**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')} UTC
**Platform:** Bluesky (@{IDENTIFIER})
**Campaign:** HQ Capabilities Promotion
**CTA:** https://secondmind.sh
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

    json_path = "/Users/secondmind/claudecodetest/data/bluesky_posts.json"
    try:
        with open(json_path, "r") as f:
            posts = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        posts = []
    posts.append({
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        "type": "hq_capabilities_promo",
        "agent": "GrowthAgent",
        "campaign": "HQ Capabilities Promotion",
        "handle": IDENTIFIER,
        "did": did,
        "post_text": POST_TEXT,
        "cta_url": "https://secondmind.sh",
        "bluesky_status": "posted",
        "at_uri": uri,
        "cid": cid,
    })
    with open(json_path, "w") as f:
        json.dump(posts, f, indent=2)


def main():
    print("=" * 60)
    print("  GROWTHAGENT: HQ Capabilities Promo")
    print("=" * 60)

    print("\nAuthenticating with Bluesky...")
    jwt, did = authenticate()
    print(f"  Authenticated as {IDENTIFIER}")

    print("\nPublishing post...")
    resp = create_post(jwt, did, POST_TEXT)
    uri = resp["uri"]
    cid = resp["cid"]
    print(f"  POSTED — {uri}")

    log_campaign(uri, cid, did)
    print("  Logged to campaign_log.md + bluesky_posts.json")

    print("\n" + "=" * 60)
    print("  POST LIVE ON BLUESKY")
    print("=" * 60)
    print(f"  URI: {uri}")


if __name__ == "__main__":
    main()
