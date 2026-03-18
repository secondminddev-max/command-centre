"""Post single Bluesky update: Autonomous Command Centre"""
import requests, json, re
from datetime import datetime, timezone

BSKY_API   = "https://bsky.social/xrpc"
IDENTIFIER = "secondmindhq.bsky.social"
PASSWORD   = os.environ.get("BSKY_PASSWORD", "")

POST_TEXT = (
    "Most AI tools do one thing.\n\n"
    "We built an entire autonomous command centre \u2014 25+ agents that monitor, "
    "research, trade, email, and scale themselves.\n\n"
    "No prompting. No babysitting. Just results.\n\n"
    "See it live \u2192 https://secondmind.sh"
)


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
            import time; time.sleep(wait)
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


def log_to_json(result, did):
    json_path = "/Users/secondmind/claudecodetest/data/bluesky_posts.json"
    try:
        with open(json_path, "r") as f:
            existing = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        existing = []
    existing.append({
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        "type": "command_centre_single",
        "agent": "BlueSky",
        "campaign": "Autonomous Command Centre — Product Awareness",
        "handle": IDENTIFIER,
        "did": did,
        "post_text": POST_TEXT,
        "bluesky_status": "posted",
        "at_uri": result["uri"],
        "cid": result["cid"],
    })
    with open(json_path, "w") as f:
        json.dump(existing, f, indent=2)


def main():
    length = len(POST_TEXT)
    print(f"Post length: {length} graphemes", "OK" if length <= 300 else "OVER LIMIT")
    if length > 300:
        print(f"ERROR: Exceeds limit by {length - 300}")
        return

    print("Authenticating with Bluesky...")
    jwt, did = authenticate()
    print(f"Authenticated as {IDENTIFIER}")

    print("Posting...")
    resp = create_post(jwt, did, POST_TEXT)
    print(f"POSTED — {resp['uri']}")

    log_to_json(resp, did)
    print("Logged to data/bluesky_posts.json")


if __name__ == "__main__":
    main()
