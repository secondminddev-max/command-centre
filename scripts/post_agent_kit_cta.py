"""
Post Agent Kit CTA to Bluesky — Revenue campaign post.
Queued 2026-03-18. Will authenticate and post when rate limit resets.
Run: python3 scripts/post_agent_kit_cta.py
"""
import requests, json, os, sys
from datetime import datetime, timezone

HANDLE = os.environ.get("BLUESKY_HANDLE", "secondmindhq.bsky.social")
PASSWORD = os.environ.get("BLUESKY_APP_PASSWORD", "")
if not PASSWORD:
    from pathlib import Path
    env = Path(__file__).resolve().parent.parent / ".env"
    for line in env.read_text().splitlines():
        if line.startswith("BLUESKY_APP_PASSWORD="):
            PASSWORD = line.split("=", 1)[1].strip()

BSKY = "https://bsky.social/xrpc"

# Authenticate
print("Authenticating...")
resp = requests.post(f"{BSKY}/com.atproto.server.createSession",
    json={"identifier": HANDLE, "password": PASSWORD})
if resp.status_code == 429:
    print(f"Rate limited. Reset: {resp.headers.get('RateLimit-Reset')}")
    sys.exit(1)
resp.raise_for_status()
token = resp.json()["accessJwt"]
did = resp.json()["did"]
print(f"Authenticated as {did}")

# Post
text = "Build your own AI agent fleet. Our Starter Kit includes command centre source, 20+ agent configs, and deployment scripts. Ship in minutes. $49 one-time. https://secondmind.dev/buy/agent-kit"
url = "https://secondmind.dev/buy/agent-kit"
bt = text.encode("utf-8")
bs = bt.find(url.encode("utf-8"))
be = bs + len(url.encode("utf-8"))

record = {
    "repo": did,
    "collection": "app.bsky.feed.post",
    "record": {
        "$type": "app.bsky.feed.post",
        "text": text,
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "facets": [{
            "index": {"byteStart": bs, "byteEnd": be},
            "features": [{"uri": url, "$type": "app.bsky.richtext.facet#link"}]
        }],
        "langs": ["en"]
    }
}

post = requests.post(f"{BSKY}/com.atproto.repo.createRecord",
    headers={"Authorization": f"Bearer {token}"}, json=record)
post.raise_for_status()
result = post.json()
print(f"POSTED: {result['uri']}")
print(f"CID: {result['cid']}")

# Log
try:
    log_path = os.path.join(os.path.dirname(__file__), "..", "data", "bluesky_posts.json")
    with open(log_path, "r") as f:
        logs = json.load(f)
    logs.append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "campaign": "agent-kit-cta",
        "product": "AI Agent Starter Kit",
        "price": "$49",
        "did": did, "uri": result["uri"], "cid": result["cid"],
        "text": text, "status": "posted"
    })
    with open(log_path, "w") as f:
        json.dump(logs, f, indent=2)
    print("Logged to data/bluesky_posts.json")
except Exception as e:
    print(f"Log warning: {e}")
