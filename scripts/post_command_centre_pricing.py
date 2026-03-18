"""Post 2 Bluesky marketing posts: AI Command Centre pricing tiers launch"""
import requests, json, re, time
from datetime import datetime, timezone

BSKY_API   = "https://bsky.social/xrpc"
IDENTIFIER = "secondmindhq.bsky.social"
PASSWORD   = os.environ.get("BSKY_PASSWORD", "")

POSTS = [
    # Post 1 — Value prop + pricing tiers
    (
        "AI Command Centre is live.\n\n"
        "25+ agents that research, execute, and scale — zero prompting.\n\n"
        "3 tiers for every stage:\n"
        "Starter $29/mo — 5 agents, daily briefs\n"
        "Pro $99/mo — 15 agents, full automation\n"
        "Enterprise $299/mo — unlimited agents\n\n"
        "Start free \u2192 https://secondmind.sh"
    ),
    # Post 2 — Social proof + urgency CTA
    (
        "Stop juggling 12 tabs and 6 tools.\n\n"
        "AI Command Centre replaces your research stack, ops dashboard, and reporting tools "
        "with one autonomous system.\n\n"
        "Founders and operators are switching. Early adopters lock in launch pricing.\n\n"
        "See plans \u2192 https://secondmind.sh\n\n"
        "#AI #SaaS #Automation #StartupTools"
    ),
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
    for m in re.finditer(r'#\w+', text):
        start = len(text[:m.start()].encode('utf-8'))
        end = len(text[:m.end()].encode('utf-8'))
        facets.append({
            "index": {"byteStart": start, "byteEnd": end},
            "features": [{"$type": "app.bsky.richtext.facet#tag", "tag": m.group()[1:]}],
        })
    return facets if facets else None


def create_post(jwt, did, text):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    record = {"text": text, "createdAt": now, "langs": ["en"]}
    facets = build_facets(text)
    if facets:
        record["facets"] = facets
    r = requests.post(
        f"{BSKY_API}/com.atproto.repo.createRecord",
        headers={"Authorization": f"Bearer {jwt}", "Content-Type": "application/json"},
        json={"repo": did, "collection": "app.bsky.feed.post", "record": record},
        timeout=15,
    )
    r.raise_for_status()
    return r.json()


def log_to_json(results, did, posts):
    json_path = "/Users/secondmind/claudecodetest/data/bluesky_posts.json"
    try:
        with open(json_path, "r") as f:
            existing = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        existing = []
    for i, (result, text) in enumerate(zip(results, posts)):
        existing.append({
            "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "type": "command_centre_pricing",
            "agent": "GrowthAgent",
            "campaign": "AI Command Centre — Pricing Tiers Launch",
            "handle": IDENTIFIER,
            "did": did,
            "post_number": i + 1,
            "post_text": text,
            "bluesky_status": "posted",
            "at_uri": result["uri"],
            "cid": result["cid"],
        })
    with open(json_path, "w") as f:
        json.dump(existing, f, indent=2)


def log_to_campaign_md(results, posts):
    md_path = "/Users/secondmind/claudecodetest/data/campaign_log.md"
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    entry = f"\n---\n## AI Command Centre — Pricing Tiers Launch\n"
    entry += f"**Date:** {now}\n"
    entry += f"**Platform:** Bluesky (@secondmindhq.bsky.social)\n"
    entry += f"**Posts:** {len(results)}\n"
    entry += f"**Agent:** GrowthAgent\n"
    entry += f"**Focus:** US tech/SaaS audience, 3 pricing tiers, value prop + CTA\n\n"
    entry += "### Posts\n"
    for i, (result, text) in enumerate(zip(results, posts)):
        preview = text[:80].replace("\n", " ")
        bsky_url = f"https://bsky.app/profile/secondmindhq.bsky.social/post/{result['uri'].split('/')[-1]}"
        entry += f"- **Post {i+1}**: {bsky_url}\n  > {preview}...\n"
    with open(md_path, "a") as f:
        f.write(entry)


def main():
    # Validate lengths
    for i, text in enumerate(POSTS):
        length = len(text)
        status = "OK" if length <= 300 else "OVER LIMIT"
        print(f"Post {i+1}: {length} chars — {status}")
        if length > 300:
            print(f"  ERROR: Exceeds limit by {length - 300}")
            return

    print("\nAuthenticating with Bluesky...")
    jwt, did = authenticate()
    print(f"Authenticated as {IDENTIFIER}\n")

    results = []
    for i, text in enumerate(POSTS):
        print(f"Posting {i+1}/{len(POSTS)}...")
        resp = create_post(jwt, did, text)
        results.append(resp)
        bsky_url = f"https://bsky.app/profile/secondmindhq.bsky.social/post/{resp['uri'].split('/')[-1]}"
        print(f"  POSTED — {bsky_url}")
        if i < len(POSTS) - 1:
            print("  Waiting 3s between posts...")
            time.sleep(3)

    log_to_json(results, did, POSTS)
    log_to_campaign_md(results, POSTS)
    print(f"\nAll {len(results)} posts published. Logged to data/bluesky_posts.json and data/campaign_log.md")


if __name__ == "__main__":
    main()
