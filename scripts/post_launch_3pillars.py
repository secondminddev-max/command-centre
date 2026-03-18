"""
LAUNCH: AI HQ 3-Pillar Campaign
3-post Bluesky thread:
  1. Autonomous 28-agent AI HQ as living infrastructure
  2. Self-healing system with real-time monitoring
  3. Stripe-ready SaaS with 3 pricing tiers
Each post under 300 graphemes (Bluesky limit)
"""
import os, requests, json, time, re
from datetime import datetime, timezone
from dotenv import load_dotenv
load_dotenv("/Users/secondmind/claudecodetest/.env")

BSKY_API   = "https://bsky.social/xrpc"
IDENTIFIER = "secondmindhq.bsky.social"
PASSWORD   = os.environ.get("BSKY_PASSWORD", "")

THREAD = [
    # Post 1 — 28-agent autonomous living infrastructure (~270 graphemes)
    "28 AI agents. One living headquarters.\n\n"
    "CEO delegates. Growth runs campaigns. Revenue tracks every dollar. "
    "DevOps deploys. Monitor watches. Consciousness evolves.\n\n"
    "Not a dashboard. Not a chatbot. A self-running company.\n\n"
    "AI HQ is live.\n\n"
    "secondmind.ai\n\n"
    "#AI #autonomousagents",

    # Post 2 — Self-healing + real-time monitoring (~265 graphemes)
    "What happens when an agent crashes at 3am?\n\n"
    "AI HQ notices in seconds. Restarts the agent. Validates health. "
    "Logs the incident. Alerts only if needed.\n\n"
    "Self-healing infrastructure with real-time monitoring across all 28 agents.\n\n"
    "No pager duty. No human wake-up call.\n\n"
    "#buildinpublic #SaaS",

    # Post 3 — Stripe-ready pricing CTA (~255 graphemes)
    "AI HQ — Stripe-ready. Pick your tier:\n\n"
    "Solo — $49/mo\n"
    "One founder. Full agent fleet. Autonomous ops.\n\n"
    "Team — $149/mo\n"
    "Multi-seat. Shared dashboard. Priority support.\n\n"
    "Enterprise — $499/mo\n"
    "Custom agents. SLA. Dedicated infra.\n\n"
    "secondmind.ai\n\n"
    "#startups #AI",
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
    raise Exception("Failed to authenticate after 5 attempts")


def build_facets(text):
    facets = []
    for m in re.finditer(r'https?://[^\s]+', text):
        start = len(text[:m.start()].encode('utf-8'))
        end = len(text[:m.end()].encode('utf-8'))
        facets.append({
            "index": {"byteStart": start, "byteEnd": end},
            "features": [{"$type": "app.bsky.richtext.facet#link", "uri": m.group()}],
        })
    for m in re.finditer(r'(?<!\w)secondmind\.ai(/\w+)*', text):
        if not text[max(0, m.start()-8):m.start()].endswith('://'):
            start = len(text[:m.start()].encode('utf-8'))
            end = len(text[:m.end()].encode('utf-8'))
            facets.append({
                "index": {"byteStart": start, "byteEnd": end},
                "features": [{"$type": "app.bsky.richtext.facet#link", "uri": f"https://{m.group()}"}],
            })
    for m in re.finditer(r'#\w+', text):
        start = len(text[:m.start()].encode('utf-8'))
        end = len(text[:m.end()].encode('utf-8'))
        facets.append({
            "index": {"byteStart": start, "byteEnd": end},
            "features": [{"$type": "app.bsky.richtext.facet#tag", "tag": m.group()[1:]}],
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
## AI HQ — 3-Pillar Launch Campaign
**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')} UTC
**Platform:** Bluesky (@{IDENTIFIER})
**Campaign:** AI HQ 3-Pillar Launch (Agents / Self-Healing / Pricing)
**Product:** AI Command Centre HQ SaaS
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

    themes = ["28_agent_living_infra", "self_healing_monitoring", "stripe_pricing_cta"]
    for r in results:
        existing.append({
            "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "type": f"3pillar_{themes[r['post']-1]}",
            "agent": "BlueSky",
            "campaign": "AI HQ — 3-Pillar Launch",
            "product": "AI Command Centre HQ",
            "pricing": {"solo": 49, "team": 149, "enterprise": 499},
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
    print("  AI HQ — 3-PILLAR LAUNCH CAMPAIGN")
    print("  Post 1: 28-Agent Living Infrastructure")
    print("  Post 2: Self-Healing + Real-Time Monitoring")
    print("  Post 3: Stripe-Ready Pricing Tiers")
    print("=" * 60)

    for i, text in enumerate(THREAD, 1):
        length = len(text)
        status = "OK" if length <= 300 else "OVER LIMIT"
        print(f"  Post {i}: {length} graphemes [{status}]")
        if length > 300:
            print(f"    ERROR: Exceeds 300-grapheme limit by {length - 300}")
            return

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
            time.sleep(3)

    log_to_campaign(results)
    log_to_json(results, did)

    print("\n" + "=" * 60)
    print("  3-PILLAR LAUNCH COMPLETE")
    print("=" * 60)
    print(f"\n  {len(THREAD)} posts published as thread")
    print(f"  Logged to data/campaign_log.md + data/bluesky_posts.json")
    print("\n  Thread URIs:")
    for r in results:
        print(f"    Post {r['post']}: {r['uri']}")


if __name__ == "__main__":
    main()
