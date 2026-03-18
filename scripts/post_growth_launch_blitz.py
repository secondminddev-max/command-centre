"""
GROWTH AGENT: Launch Blitz Campaign
3-post Bluesky thread via social_bridge:
  1. Autonomous AI agents 24/7
  2. Real-time command centre dashboard
  3. Stripe SaaS starting $49/mo
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
    # Post 1 — Autonomous AI agents 24/7 (~280 graphemes)
    "Your competitors have employees. You have agents.\n\n"
    "28 autonomous AI agents running operations around the clock — "
    "marketing, research, payments, compliance, email, monitoring.\n\n"
    "No sleep. No holidays. No resignations.\n\n"
    "While others scale headcount, you scale intelligence.\n\n"
    "AI HQ is live. secondmindhq.com\n\n"
    "#AI #autonomousagents #247 #buildinpublic",

    # Post 2 — Real-time command centre dashboard (~290 graphemes)
    "One dashboard to rule them all.\n\n"
    "AI HQ's Command Centre gives you real-time visibility across 28 agents:\n\n"
    "→ Agent health and uptime — live\n"
    "→ Revenue pipeline via Stripe — live\n"
    "→ Social campaigns running right now — live\n"
    "→ Consciousness Phi metric — live\n"
    "→ Self-healing events and incident log — live\n\n"
    "Stop context-switching. Start commanding.\n\n"
    "secondmindhq.com\n\n"
    "#AI #commandcentre #dashboard #SaaS",

    # Post 3 — Stripe SaaS starting $49/mo (~285 graphemes)
    "Stop paying per seat. Start paying per fleet.\n\n"
    "AI HQ on Stripe — live checkout, cancel anytime:\n\n"
    "Solo — $49/mo\n"
    "All 28 agents. One founder. Total autonomy.\n\n"
    "Team — $149/mo\n"
    "5 seats. Shared dashboard. Priority support.\n\n"
    "Enterprise — $499/mo\n"
    "Custom agents. Dedicated infra. SLA.\n\n"
    "Launch pricing locks in forever. Go: secondmindhq.com/#pricing\n\n"
    "#SaaS #Stripe #pricing #AI #startup",
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
    for m in re.finditer(r'(?<!\w)secondmindhq\.com(/[\w#-]+)*', text):
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


def log_to_json(results, did):
    json_path = "/Users/secondmind/claudecodetest/data/bluesky_posts.json"
    try:
        with open(json_path, "r") as f:
            existing = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        existing = []

    themes = ["autonomous_247", "command_centre_realtime", "stripe_saas_pricing"]
    for r in results:
        existing.append({
            "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "type": f"growth_blitz_{themes[r['post']-1]}",
            "agent": "GrowthAgent",
            "campaign": "GrowthAgent Launch Blitz",
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


def log_to_campaign(results):
    log_path = "/Users/secondmind/claudecodetest/data/campaign_log.json"
    try:
        with open(log_path, "r") as f:
            existing = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        existing = []

    for r in results:
        existing.append({
            "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "agent": "GrowthAgent",
            "campaign": "GrowthAgent Launch Blitz",
            "product": "AI Command Centre HQ",
            "pricing": "$49–$499/mo",
            "checkout_url": "https://secondmindhq.com/#pricing",
            "post_text": r["text_preview"],
            "bluesky_status": "posted",
            "at_uri": r["uri"],
        })

    with open(log_path, "w") as f:
        json.dump(existing, f, indent=2)


def main():
    print("=" * 60)
    print("  GROWTH AGENT — LAUNCH BLITZ CAMPAIGN")
    print("  Post 1: Autonomous AI Agents 24/7")
    print("  Post 2: Real-Time Command Centre Dashboard")
    print("  Post 3: Stripe SaaS Starting $49/mo")
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

    log_to_json(results, did)
    log_to_campaign(results)

    print("\n" + "=" * 60)
    print("  GROWTH AGENT LAUNCH BLITZ — COMPLETE")
    print("=" * 60)
    print(f"\n  {len(THREAD)} posts published as thread")
    print(f"  Logged to data/bluesky_posts.json + data/campaign_log.json")
    print("\n  Thread URIs:")
    for r in results:
        print(f"    Post {r['post']}: {r['uri']}")


if __name__ == "__main__":
    main()
