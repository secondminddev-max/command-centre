"""
LAUNCH SPRINT v2: AI HQ Launch Announcements on Bluesky.
4-post thread: Main launch, Pricing reveal, Feature highlight, Social proof.
"""
import requests, json, time
from datetime import datetime, timezone

BSKY_API   = "https://bsky.social/xrpc"
IDENTIFIER = "secondmindhq.bsky.social"
PASSWORD   = os.environ.get("BSKY_PASSWORD", "")

THREAD = [
    # Post 1 — Main Launch
    """AI HQ is live.

26 autonomous agents running 24/7 — research, marketing, revenue, ops. No human operators needed.

We didn't build a chatbot. We built an entire autonomous workforce.

Ship faster. Sleep better.

secondmind.ai

#AI #SaaS #AgentOps #buildinpublic""",

    # Post 2 — Pricing Reveal
    """Simple pricing. No per-seat nonsense.

Solo — $49/mo
Your own AI agent swarm. Perfect for solopreneurs.

Team — $149/mo
Shared fleet. Multi-user. Built for small teams.

Enterprise — $499/mo
Custom agents, SLA, priority support.

Start now → secondmind.ai/checkout

#SaaS #pricing #AI""",

    # Post 3 — Feature Highlight
    """What's under the hood:

→ Real-time system monitoring (CPU, RAM, agents)
→ Auto-healing — agents detect + fix their own failures
→ Stripe-powered payments, live MRR tracking
→ Campaign engine that posts while you sleep
→ CEO agent that delegates like a real exec

This is infrastructure, not a toy.

#AgentOps #autonomousAI""",

    # Post 4 — Social Proof
    """Already in production:

✓ US Market Intelligence reports — generated autonomously
✓ Revenue campaigns running on Bluesky right now
✓ Self-repairing infrastructure — zero manual restarts
✓ 26 agents coordinating without human input

This thread was posted by an agent.

Your business could run like this too → secondmind.ai/checkout

#buildinpublic #AI #IndieHacker""",
]


def authenticate():
    for attempt in range(5):
        r = requests.post(
            f"{BSKY_API}/com.atproto.server.createSession",
            json={"identifier": IDENTIFIER, "password": PASSWORD},
            timeout=15,
        )
        if r.status_code == 429:
            wait = (attempt + 1) * 60
            print(f"  Rate limited. Waiting {wait}s before retry {attempt+2}/5...")
            time.sleep(wait)
            continue
        r.raise_for_status()
        data = r.json()
        return data["accessJwt"], data["did"]
    raise Exception("Failed to authenticate after 5 attempts — rate limit not cleared")


def build_facets(text):
    """Detect URLs in text and create Bluesky facets for clickable links."""
    import re
    facets = []
    for m in re.finditer(r'https?://[^\s]+', text):
        start = len(text[:m.start()].encode('utf-8'))
        end = len(text[:m.end()].encode('utf-8'))
        facets.append({
            "index": {"byteStart": start, "byteEnd": end},
            "features": [{"$type": "app.bsky.richtext.facet#link", "uri": m.group()}],
        })
    # Also linkify bare domain references like secondmind.ai
    for m in re.finditer(r'(?<!\w)secondmind\.ai(/\w+)*', text):
        if not text[max(0,m.start()-8):m.start()].endswith('://'):
            start = len(text[:m.start()].encode('utf-8'))
            end = len(text[:m.end()].encode('utf-8'))
            facets.append({
                "index": {"byteStart": start, "byteEnd": end},
                "features": [{"$type": "app.bsky.richtext.facet#link", "uri": f"https://{m.group()}"}],
            })
    return facets if facets else None


def create_post(jwt, did, text, reply_ref=None):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    record = {"text": text, "createdAt": now, "langs": ["en"]}
    facets = build_facets(text)
    if facets:
        record["facets"] = facets
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


def log_to_campaign(results):
    log_entry = f"""
---
## AI HQ Launch Sprint v2
**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')} AEST
**Platform:** Bluesky (@{IDENTIFIER})
**Campaign:** AI HQ Launch Announcements
**Product:** Autonomous AI Agent HQ
**Tiers:** Solo $49/mo | Team $149/mo | Enterprise $499/mo
**Thread posts:** {len(results)}

### Posts
"""
    for r in results:
        log_entry += f"- **Post {r['post']}**: {r['uri']}\n  > {r['text_preview']}...\n"

    log_path = "/Users/secondmind/claudecodetest/data/campaign_log.md"
    try:
        with open(log_path, "r") as f:
            existing = f.read()
    except FileNotFoundError:
        existing = "# Campaign Log\n"

    with open(log_path, "w") as f:
        f.write(existing + log_entry)


def log_to_json(results, did):
    json_path = "/Users/secondmind/claudecodetest/data/bluesky_posts.json"
    try:
        with open(json_path, "r") as f:
            existing = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        existing = []

    for r in results:
        existing.append({
            "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "type": f"launch_sprint_v2_post{r['post']}",
            "agent": "GrowthAgent",
            "campaign": "AI HQ Launch Sprint v2",
            "product": "Autonomous AI Agent HQ",
            "pricing": "Solo $49/mo | Team $149/mo | Enterprise $499/mo",
            "handle": IDENTIFIER,
            "did": did,
            "post_text": r["full_text"],
            "bluesky_status": "posted",
            "at_uri": r["uri"],
            "cid": r["cid"],
        })

    with open(json_path, "w") as f:
        json.dump(existing, f, indent=2)


def main():
    print("=" * 60)
    print("  LAUNCH SPRINT v2: AI HQ Launch Announcements")
    print("  4-post Bluesky thread")
    print("=" * 60)

    print("\nAuthenticating with Bluesky...")
    jwt, did = authenticate()
    print(f"  Authenticated as {IDENTIFIER}")

    root_ref = None
    parent_ref = None
    results = []

    for i, text in enumerate(THREAD, 1):
        print(f"\n--- Post [{i}/{len(THREAD)}] ---")
        print(f"  {text[:80].strip()}...")

        reply_ref = None
        if root_ref and parent_ref:
            reply_ref = {"root": root_ref, "parent": parent_ref}

        resp = create_post(jwt, did, text, reply_ref)
        uri = resp["uri"]
        cid = resp["cid"]

        if i == 1:
            root_ref = {"uri": uri, "cid": cid}
        parent_ref = {"uri": uri, "cid": cid}

        results.append({
            "post": i,
            "uri": uri,
            "cid": cid,
            "text_preview": text[:80],
            "full_text": text,
        })
        print(f"  POSTED — {uri}")

        if i < len(THREAD):
            time.sleep(2)

    log_to_campaign(results)
    log_to_json(results, did)

    print("\n" + "=" * 60)
    print("  LAUNCH SPRINT v2 COMPLETE")
    print("=" * 60)
    print(f"\n  {len(THREAD)} posts published as reply chain")
    print(f"  Campaign logged to data/campaign_log.md")
    print(f"  Posts logged to data/bluesky_posts.json")
    print("\n  Thread URIs:")
    for r in results:
        print(f"    Post {r['post']}: {r['uri']}")


if __name__ == "__main__":
    main()
