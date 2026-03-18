"""
Post Autonomous AI HQ capabilities thread to Bluesky as a reply chain.
Revenue content push — consulting/custom builds CTA.
Logs results to data/campaign_log.md and data/campaign_log.json.
"""
import requests, json, time, os
from datetime import datetime, timezone

BSKY_API   = "https://bsky.social/xrpc"
IDENTIFIER = os.environ.get("BSKY_HANDLE", "secondmindhq.bsky.social")
PASSWORD   = os.environ.get("BSKY_PASSWORD", "")

THREAD = [
    # Post 1 — Hook
    """We built an autonomous AI headquarters with 28 agents running 24/7.

It monitors itself. Heals itself. Builds on command.

No human babysitting. No downtime. Just execution.

Here's what it actually does 🧵""",

    # Post 2 — Capabilities
    """What 28 agents handle autonomously:

→ Real-time system monitoring & self-healing alerts
→ Web research on demand
→ API building & deployment
→ Social media automation
→ Email automation
→ Scheduled tasks & cron jobs
→ Policy enforcement across all agents

All running right now. No human in the loop.""",

    # Post 3 — Live proof
    """This isn't a demo. It's live.

Our command centre dashboard shows every agent, every task, every health check — in real time.

The post you're reading? An agent wrote it, scheduled it, and posted it. Autonomously.

See it yourself: https://secondmind.ai""",

    # Post 4 — The offer
    """We don't just run this for ourselves — we build these systems for businesses.

Custom autonomous AI operations:
→ 24/7 monitoring & alerting
→ Automated research pipelines
→ Data processing & reporting
→ API integrations
→ Task automation

No human intervention required. Built to your spec.""",

    # Post 5 — CTA
    """Want autonomous AI running your operations?

→ Visit our command centre: https://secondmind.ai
→ DM us for consulting & custom builds

We're builders. We ship autonomous systems that work while you sleep.

#AI #automation #autonomousAI #AIagents #buildinpublic""",
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
    parts = uri.replace("at://", "").split("/")
    rkey = parts[2]
    return f"https://bsky.app/profile/{IDENTIFIER}/post/{rkey}"


def main():
    print("Authenticating with Bluesky...")
    jwt, did = authenticate()
    print(f"  Authenticated as {IDENTIFIER}")

    root_ref = None
    parent_ref = None
    results = []

    for i, text in enumerate(THREAD, 1):
        print(f"\nPosting [{i}/{len(THREAD)}]...")
        print(f"  {text[:80].strip()}...")

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
        print(f"  Posted — URL: {url}")

        if i < len(THREAD):
            time.sleep(2)

    # Log to data/campaign_log.md
    log_entry = f"""
---
## Autonomous AI HQ Capabilities — Revenue CTA Thread
**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')} AEST
**Platform:** Bluesky (@{IDENTIFIER})
**Thread posts:** {len(THREAD)}
**Campaign:** Autonomous AI HQ — consulting & custom builds
**Offer:** Custom autonomous AI systems — consulting/custom builds
**CTA:** https://secondmind.ai + DM

### Posts
"""
    for r in results:
        log_entry += f"- **Post {r['post']}**: {r['url']}\n  > {r['text_preview']}...\n"

    log_path = "/Users/secondmind/claudecodetest/data/campaign_log.md"
    try:
        with open(log_path, "r") as f:
            existing = f.read()
    except FileNotFoundError:
        existing = "# Campaign Log\n"

    with open(log_path, "w") as f:
        f.write(existing + log_entry)

    # Log to data/campaign_log.json
    json_log_path = "/Users/secondmind/claudecodetest/data/campaign_log.json"
    try:
        with open(json_log_path, "r") as f:
            campaigns = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        campaigns = []

    campaigns.append({
        "campaign": "autonomous_hq_capabilities",
        "agent": "GrowthAgent",
        "platform": "bluesky",
        "handle": IDENTIFIER,
        "date": datetime.now(timezone.utc).isoformat(),
        "product": "Consulting & Custom Autonomous AI Builds",
        "cta_url": "https://secondmind.ai",
        "posts": results,
        "status": "posted",
    })

    with open(json_log_path, "w") as f:
        json.dump(campaigns, f, indent=2)

    print(f"\nThread posted. Logged to {log_path}")
    print("\nThread URLs:")
    for r in results:
        print(f"  Post {r['post']}: {r['url']}")

    return results


if __name__ == "__main__":
    main()
