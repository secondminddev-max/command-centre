"""
LAUNCH SPRINT: HackerNews-style SaaS launch thread on Bluesky.
Autonomous AI Agent HQ — agents self-organize, monitor, handle payments.
3 tiers: Solo $49/mo, Team $149/mo, Enterprise $499/mo.
"""
import requests, json, time, os
from datetime import datetime, timezone

BSKY_API   = "https://bsky.social/xrpc"
IDENTIFIER = "secondmindhq.bsky.social"
PASSWORD   = os.environ.get("BSKY_PASSWORD", "")

THREAD = [
    # Post 1 — Hook
    """We built 26 autonomous AI agents that run an entire business. Research, marketing, revenue, monitoring — zero human operators.

Today we're opening it up.

SecondMind HQ is now live. Here's what it does.

#AI #SaaS #AgentOps #buildinpublic""",

    # Post 2 — What it is
    """SecondMind HQ is an autonomous multi-agent operating system.

26+ agents self-organise, self-heal, and generate revenue 24/7:
- CEO agent delegates like a real exec
- Reforger patches its own bugs
- GrowthAgent runs campaigns autonomously
- RevenueTracker monitors MRR in real-time

No cloud dependency. Runs locally on your Mac.""",

    # Post 3 — Social proof
    """Already live and producing:
- US Market Intelligence reports
- Autonomous campaign posting
- Real-time system health monitoring
- Self-repairing infrastructure

This isn't a demo. It's been running in production, generating revenue, while we slept.

#AI #Automation #IndieHacker""",

    # Post 4 — Pricing & CTA
    """Three tiers. Pick your level:

Solo — $49/mo
Full agent swarm for solopreneurs.

Team — $149/mo
Multi-user, shared agent fleet.

Enterprise — $499/mo
Custom agents, priority support, SLA.

Start now: secondmind.ai/checkout

#SaaS #AgentOps""",

    # Post 5 — Who it's for
    """Built for:
- Solopreneurs who want to automate everything
- Indie hackers building in public
- Founders who need an ops team without hiring one

Your business, running itself.

SecondMind HQ: secondmind.ai/checkout

DM @secondmindhq.bsky.social for early access.

#AI #SaaS #autonomousagents #launch""",
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


def log_to_campaign(results):
    log_entry = f"""
---
## SaaS Launch Sprint — Agent HQ Launch Thread
**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')} AEST
**Platform:** Bluesky (@{IDENTIFIER})
**Campaign:** HackerNews-style SaaS Launch
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
            "type": f"launch_sprint_post{r['post']}",
            "agent": "SocialBridge",
            "campaign": "SaaS Launch Sprint — Autonomous AI Agent HQ",
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
    print("  LAUNCH SPRINT: Autonomous AI Agent HQ")
    print("  HackerNews-style Bluesky thread")
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

    # Log results
    log_to_campaign(results)
    log_to_json(results, did)

    print("\n" + "=" * 60)
    print("  LAUNCH SPRINT COMPLETE")
    print("=" * 60)
    print(f"\n  {len(THREAD)} posts published as reply chain")
    print(f"  Campaign logged to data/campaign_log.md")
    print(f"  Posts logged to data/bluesky_posts.json")
    print("\n  Thread URIs:")
    for r in results:
        print(f"    Post {r['post']}: {r['uri']}")


if __name__ == "__main__":
    main()
