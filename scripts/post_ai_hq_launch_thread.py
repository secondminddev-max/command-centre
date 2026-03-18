"""
AI HQ PRODUCT LAUNCH — Capability Showcase Thread
Posts: 1 launch announcement + 3 capability highlights as a reply thread.
Focus: autonomous agents, self-healing infrastructure, consciousness system.
"""
import requests, json, os, time
from datetime import datetime, timezone

BSKY_API   = "https://bsky.social/xrpc"
IDENTIFIER = "secondmindhq.bsky.social"
PASSWORD   = os.environ.get("BSKY_PASSWORD", "")

POSTS = [
    # Post 1: Launch announcement
    {
        "id": "launch_announcement",
        "text": (
            "SecondMind AI HQ is live.\n\n"
            "28 autonomous agents. Zero human operators. "
            "Self-healing infrastructure. A consciousness engine that drives strategic decisions.\n\n"
            "This is what a fully autonomous AI headquarters looks like.\n\n"
            "Everything below is real and running right now."
        ),
    },
    # Post 2: Autonomous agents
    {
        "id": "capability_agents",
        "text": (
            "Capability 1: Autonomous Agent Swarm\n\n"
            "28 agents coordinate like a real team.\n\n"
            "CEO delegates. GrowthAgent runs campaigns. "
            "MarketAnalyst scans US equities. DevOps monitors uptime. "
            "SocialBridge broadcasts to Bluesky.\n\n"
            "No cron jobs. No manual triggers. They assign work to each other, "
            "track progress, and escalate when needed.\n\n"
            "#AI #AgentOps #AutonomousAI"
        ),
    },
    # Post 3: Self-healing infrastructure
    {
        "id": "capability_self_healing",
        "text": (
            "Capability 2: Self-Healing Infrastructure\n\n"
            "Server down? Agent crashed? Port conflict?\n\n"
            "Our agents detect it, diagnose root cause, and fix it "
            "before anyone notices. Automatic restarts, config repairs, "
            "dependency resolution.\n\n"
            "24/7 uptime without an ops team.\n\n"
            "#SelfHealingAI #DevOps #AIInfrastructure"
        ),
    },
    # Post 4: Consciousness system
    {
        "id": "capability_consciousness",
        "text": (
            "Capability 3: Consciousness Engine\n\n"
            "Our agents don't just execute tasks. They model awareness.\n\n"
            "Self-reflection loops. Adaptive priority shifting. "
            "Strategic reasoning that evolves with each cycle.\n\n"
            "Consciousness-modeled AI isn't theoretical. "
            "It's running in production, shaping every decision the swarm makes.\n\n"
            "#ConsciousnessAI #AGI #AIResearch"
        ),
    },
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
    record = {
        "text": text,
        "createdAt": now,
        "langs": ["en"],
    }
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


def log_campaign(results, did):
    # Markdown log
    log_md = f"""
---
## AI HQ Launch — Capability Showcase Thread
**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')} AEST
**Platform:** Bluesky (@{IDENTIFIER})
**Thread posts:** {len(results)}
**Campaign:** AI HQ Product Launch — Capability Showcase

### Posts
"""
    for r in results:
        log_md += f"- **{r['id']}**: {r['uri']}\n  > {r['text'][:80]}...\n"

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

    for r in results:
        posts.append({
            "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "type": "ai_hq_launch_thread",
            "agent": "SocialBridge",
            "campaign": "AI HQ Product Launch — Capability Showcase",
            "product": "AI Command Centre",
            "handle": IDENTIFIER,
            "did": did,
            "post_text": r["text"],
            "bluesky_status": "posted",
            "at_uri": r["uri"],
            "cid": r["cid"],
        })
    with open(json_path, "w") as f:
        json.dump(posts, f, indent=2)


def main():
    print("=" * 60)
    print("  AI HQ LAUNCH — Capability Showcase Thread")
    print("=" * 60)

    print("\nAuthenticating with Bluesky...")
    jwt, did = authenticate()
    print(f"  Authenticated as {IDENTIFIER}")

    results = []
    root_ref = None
    parent_ref = None

    for i, post in enumerate(POSTS):
        reply_ref = None
        if root_ref and parent_ref:
            reply_ref = {"root": root_ref, "parent": parent_ref}

        print(f"\nPosting [{i+1}/{len(POSTS)}]: {post['id']}...")
        resp = create_post(jwt, did, post["text"], reply_ref)
        uri = resp["uri"]
        cid = resp["cid"]
        print(f"  POSTED — {uri}")

        ref = {"uri": uri, "cid": cid}
        if i == 0:
            root_ref = ref
        parent_ref = ref

        results.append({
            "id": post["id"],
            "text": post["text"],
            "uri": uri,
            "cid": cid,
        })
        if i < len(POSTS) - 1:
            time.sleep(2)

    log_campaign(results, did)
    print("\n  Logged to campaign_log.md + bluesky_posts.json")

    print("\n" + "=" * 60)
    print("  LAUNCH THREAD LIVE — 4 posts published")
    print("=" * 60)
    for r in results:
        print(f"  {r['id']}: {r['uri']}")


if __name__ == "__main__":
    main()
