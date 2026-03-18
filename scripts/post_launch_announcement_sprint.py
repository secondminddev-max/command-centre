#!/usr/bin/env python3
"""Launch Sprint: Autonomous AI HQ SaaS announcement thread on Bluesky."""

import requests
import time
import json
from datetime import datetime, timezone

IDENTIFIER = "secondmindhq.bsky.social"
PASSWORD   = os.environ.get("BSKY_PASSWORD", "")
API_BASE = "https://bsky.social/xrpc"

POSTS = [
    (
        "Introducing SecondMind HQ — your autonomous AI command centre.\n\n"
        "Multi-agent orchestration that actually runs your ops. "
        "Research, social, growth, treasury — all handled by specialist AI agents working 24/7.\n\n"
        "Not a chatbot. A headquarters.\n\n"
        "secondmindhq.com"
    ),
    (
        "What runs inside SecondMind HQ:\n\n"
        "- CEO agent coordinates everything\n"
        "- Research agents scan markets & competitors\n"
        "- Social agents post, engage & monitor\n"
        "- Growth agents find revenue opportunities\n"
        "- Treasury agents track your finances\n\n"
        "All autonomous. All orchestrated."
    ),
    (
        "Pricing built for builders:\n\n"
        "Solo — $49/mo\n"
        "→ 5 agents, core orchestration\n\n"
        "Team — $149/mo\n"
        "→ 15 agents, priority execution, shared workspace\n\n"
        "Enterprise — $499/mo\n"
        "→ Unlimited agents, custom integrations, dedicated infra\n\n"
        "Start free. Scale when ready."
    ),
    (
        "Why we built this:\n\n"
        "AI tools give you answers. SecondMind HQ gives you operators.\n\n"
        "Agents that don't wait for prompts — they watch, decide, and act. "
        "Your AI workforce runs while you sleep.\n\n"
        "Early access now open → secondmindhq.com"
    ),
]


def authenticate():
    for attempt in range(5):
        resp = requests.post(f"{API_BASE}/com.atproto.server.createSession", json={
            "identifier": IDENTIFIER,
            "password": PASSWORD,
        })
        if resp.status_code == 429:
            wait = 30 * (attempt + 1)
            print(f"  Rate limited, waiting {wait}s (attempt {attempt+1}/5)...")
            time.sleep(wait)
            continue
        resp.raise_for_status()
        data = resp.json()
        return data["accessJwt"], data["did"]
    raise Exception("Failed to authenticate after 5 attempts")


def post(token, did, text, reply_ref=None):
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    record = {
        "$type": "app.bsky.feed.post",
        "text": text,
        "createdAt": now,
    }
    if reply_ref:
        record["reply"] = reply_ref

    resp = requests.post(
        f"{API_BASE}/com.atproto.repo.createRecord",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "repo": did,
            "collection": "app.bsky.feed.post",
            "record": record,
        },
    )
    resp.raise_for_status()
    return resp.json()


def main():
    print("Authenticating with Bluesky...")
    token, did = authenticate()
    print(f"Authenticated as {did}\n")

    results = []
    root_ref = None

    for i, text in enumerate(POSTS):
        print(f"Posting [{i+1}/{len(POSTS)}]...")

        reply_ref = None
        if root_ref and results:
            last = results[-1]
            reply_ref = {
                "root": root_ref,
                "parent": {"uri": last["uri"], "cid": last["cid"]},
            }

        result = post(token, did, text, reply_ref)
        results.append(result)
        print(f"  → {result['uri']}")

        if i == 0:
            root_ref = {"uri": result["uri"], "cid": result["cid"]}

        if i < len(POSTS) - 1:
            time.sleep(3)

    # Log to campaign log
    log_entry = {
        "campaign": "AI HQ SaaS Launch Sprint",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "posts": len(results),
        "uris": [r["uri"] for r in results],
        "status": "posted",
    }

    log_path = "/Users/secondmind/claudecodetest/data/campaign_log.md"
    with open(log_path, "a") as f:
        f.write(f"\n\n## {log_entry['campaign']} — {log_entry['timestamp']}\n")
        f.write(f"- Posts: {log_entry['posts']}\n")
        for uri in log_entry["uris"]:
            f.write(f"- {uri}\n")
        f.write(f"- Status: {log_entry['status']}\n")

    # Update bluesky_posts.json
    posts_path = "/Users/secondmind/claudecodetest/data/bluesky_posts.json"
    try:
        with open(posts_path) as f:
            existing = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        existing = []

    for i, result in enumerate(results):
        existing.append({
            "campaign": "AI HQ SaaS Launch Sprint",
            "post_number": i + 1,
            "text": POSTS[i][:80] + "...",
            "uri": result["uri"],
            "cid": result["cid"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "posted",
        })

    with open(posts_path, "w") as f:
        json.dump(existing, f, indent=2)

    print(f"\nLaunch sprint complete — {len(results)} posts published.")
    print("Campaign logged to data/campaign_log.md")


if __name__ == "__main__":
    main()
