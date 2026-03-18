"""
Post US Stock Market Intelligence Report CTA thread to Bluesky as a reply chain.
Logs results to data/campaign_log.md.
"""
import requests, json, time
from datetime import datetime, timezone

BSKY_API   = "https://bsky.social/xrpc"
IDENTIFIER = "secondmindhq.bsky.social"
PASSWORD   = os.environ.get("BSKY_PASSWORD", "")

THREAD = [
    # Post 1 — Hook with bold market insight
    """S&P 500: large-cap growth vs small-cap value divergence is at a 3-week extreme.

When this pattern forms, sector rotation accelerates fast.

The names that outperform are hiding in plain sight right now 🧵 #markets #investing""",

    # Post 2 — Report value description
    """Our US Stock Market Intelligence Report ($29) covers:

→ S&P 500 momentum stocks (ranked)
→ Sector strength heat map
→ Watchlist candidates + entry signals
→ Risk dashboard: VIX, breadth, put/call

Sharp quant analysis. No noise. #fintech #trading""",

    # Post 3 — CTA
    """Serious about US markets? This is your edge.

→ One-time $29
→ Instant delivery
→ Updated weekly

Get this week's report:
https://secondmind.ai/checkout

#markets #investing #fintech #trading""",
]


def authenticate():
    r = requests.post(
        f"{BSKY_API}/com.atproto.server.createSession",
        json={"identifier": IDENTIFIER, "password": PASSWORD},
        timeout=15,
    )
    r.raise_for_status()
    data = r.json()
    return data["accessJwt"], data["did"]


def create_post(jwt, did, text, reply_ref=None):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    record = {"text": text, "createdAt": now, "langs": ["en"]}
    if reply_ref:
        record["reply"] = reply_ref
    r = requests.post(
        f"{BSKY_API}/com.atproto.repo.createRecord",
        headers={"Authorization": f"Bearer {jwt}", "Content-Type": "application/json"},
        json={"repo": did, "collection": "app.bsky.feed.post", "record": record},
        timeout=15,
    )
    r.raise_for_status()
    return r.json()


def uri_to_url(uri):
    # at://did:plc:xxx/app.bsky.feed.post/rkey -> https://bsky.app/profile/handle/post/rkey
    parts = uri.replace("at://", "").split("/")
    did = parts[0]
    rkey = parts[2]
    return f"https://bsky.app/profile/{IDENTIFIER}/post/{rkey}"


def main():
    print("Authenticating with Bluesky…")
    jwt, did = authenticate()
    print(f"  ✓ Authenticated as {IDENTIFIER}")

    root_ref = None
    parent_ref = None
    results = []

    for i, text in enumerate(THREAD, 1):
        print(f"\nPosting [{i}/{len(THREAD)}]…")
        print(f"  {text[:80].strip()}…")

        reply_ref = None
        if root_ref and parent_ref:
            reply_ref = {"root": root_ref, "parent": parent_ref}

        resp = create_post(jwt, did, text, reply_ref)
        uri = resp["uri"]
        cid = resp["cid"]
        url = uri_to_url(uri)

        if i == 1:
            root_ref = {"uri": uri, "cid": cid}
        parent_ref = {"uri": uri, "cid": cid}

        results.append({"post": i, "uri": uri, "cid": cid, "url": url, "text_preview": text[:80]})
        print(f"  ✓ Posted — URL: {url}")

        if i < len(THREAD):
            time.sleep(2)

    # Log to data/campaign_log.md
    log_entry = f"""
---
## US Stock Market Intelligence Report — CTA Thread
**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')} AEST
**Platform:** Bluesky (@{IDENTIFIER})
**Thread posts:** {len(THREAD)}
**Product:** US Stock Market Intelligence Report ($29)
**Checkout:** https://secondmind.ai/checkout

### Posts
"""
    for r in results:
        log_entry += f"- **Post {r['post']}**: {r['url']}\n  > {r['text_preview']}…\n"

    log_path = "/Users/secondmind/claudecodetest/data/campaign_log.md"
    try:
        with open(log_path, "r") as f:
            existing = f.read()
    except FileNotFoundError:
        existing = "# Campaign Log\n"

    with open(log_path, "w") as f:
        f.write(existing + log_entry)

    print(f"\n✓ Thread posted. Logged to {log_path}")
    print("\nThread URLs:")
    for r in results:
        print(f"  Post {r['post']}: {r['url']}")

    return results


if __name__ == "__main__":
    main()
