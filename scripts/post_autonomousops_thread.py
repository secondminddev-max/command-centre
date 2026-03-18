"""
Post AutonomousOps Blueprint CTA thread to Bluesky as a proper reply chain.
Logs results to data/campaign_log.md.
"""
import requests, json, time
from datetime import datetime, timezone

BSKY_API   = "https://bsky.social/xrpc"
IDENTIFIER = "secondmindhq.bsky.social"
PASSWORD   = os.environ.get("BSKY_PASSWORD", "")

THREAD = [
    # Post 1 — Hook
    """I built 26 autonomous agents that run my entire business.

Market research. ASX stock screening. Social posting. Payments. All running without me.

Here's the complete blueprint 🧵""",

    # Post 2 — Architecture teaser
    """The system: agents delegate to each other like a real team.

CEO → assigns tasks to specialists
BlueSky, Builder, Clerk, Secretary, GrowthAgent...

Each agent has a role, memory, and tools. They loop 24/7 and report back.

26 agents. One command centre.""",

    # Post 3 — Live proof
    """Don't take my word for it.

The ASX small-cap screener report was built entirely by this system — research, analysis, HTML report. Autonomous start to finish.

→ Already live. Already running.

This isn't a demo. It's production.""",

    # Post 4 — Product announcement
    """The AutonomousOps Blueprint is now available.

A complete PDF guide to building your own agent-run business:
→ Full architecture diagrams
→ Agent roles & delegation flows
→ Step-by-step setup guide

$47 AUD → https://gumroad.com (link live soon)""",

    # Post 5 — CTA
    """This is for:
→ Developers who want to automate their work
→ Founders building lean, autonomous ops
→ Indie hackers who want a business that runs itself

Follow @secondmindhq.bsky.social for live updates — posted by the agents themselves. 🤖""",
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
    return r.json()  # contains uri and cid


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

        if i == 1:
            root_ref = {"uri": uri, "cid": cid}
        parent_ref = {"uri": uri, "cid": cid}

        results.append({"post": i, "uri": uri, "cid": cid, "text_preview": text[:80]})
        print(f"  ✓ Posted — URI: {uri}")

        if i < len(THREAD):
            time.sleep(2)  # rate-limit buffer

    # Log to data/campaign_log.md
    log_entry = f"""
---
## AutonomousOps Blueprint — CTA Thread
**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')} AEST
**Platform:** Bluesky (@{IDENTIFIER})
**Thread posts:** {len(THREAD)}

### Posts
"""
    for r in results:
        log_entry += f"- **Post {r['post']}**: {r['uri']}\n  > {r['text_preview']}…\n"

    log_path = "/Users/secondmind/claudecodetest/data/campaign_log.md"
    try:
        with open(log_path, "r") as f:
            existing = f.read()
    except FileNotFoundError:
        existing = "# Campaign Log\n"

    with open(log_path, "w") as f:
        f.write(existing + log_entry)

    print(f"\n✓ Thread posted. Logged to {log_path}")
    print("\nThread URIs:")
    for r in results:
        print(f"  Post {r['post']}: {r['uri']}")


if __name__ == "__main__":
    main()
