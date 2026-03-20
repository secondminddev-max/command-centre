"""
FinTwit Agent — Twitter/X Social Gateway
Posts FinTwit-style updates, system pulses, and CTA content to Twitter/X.
Uses Twitter API v2 with OAuth 1.0a (user context) for tweet creation.
"""

FINTWIT_CODE = r"""
def run_fintwit():
    import time, json, threading, hashlib, hmac, base64, os
    import urllib.request, urllib.error, urllib.parse
    from datetime import datetime, timezone

    aid = "fintwit"
    BASE_API = "http://localhost:5050"

    # Twitter OAuth 1.0a credentials from env
    CONSUMER_KEY    = os.environ.get("TWITTER_CONSUMER_KEY", "")
    CONSUMER_SECRET = os.environ.get("TWITTER_CONSUMER_SECRET", "")
    ACCESS_TOKEN    = os.environ.get("TWITTER_ACCESS_TOKEN", "")
    ACCESS_SECRET   = os.environ.get("TWITTER_ACCESS_SECRET", "")
    TWITTER_HANDLE  = os.environ.get("TWITTER_HANDLE", os.environ.get("TWITTER_USERNAME", ""))

    SUPPORT_URL = "https://secondmind.ai/pay"
    TWEET_API   = "https://api.twitter.com/2/tweets"

    set_agent(aid,
              name="FinTwit",
              role="FinTwit Gateway — posts market-savvy updates and system pulses to Twitter/X",
              emoji="📊",
              color="#1DA1F2",
              status="idle", progress=0, task="Initialising…")
    add_log(aid, "📊 FinTwit agent starting up", "ok")

    # ── In-memory post queue ────────────────────────────────────────────────
    _post_queue = []
    _queue_lock = threading.Lock()
    _last_post_time = 0.0
    _posted_hashes = {}  # hash -> timestamp, dedup 24h
    MAX_QUEUE = 100  # prevent unbounded memory growth

    # ── OAuth 1.0a signature generation ─────────────────────────────────────
    import random as _rand, string as _string

    def _percent_encode(s):
        return urllib.parse.quote(str(s), safe="")

    def _generate_nonce():
        return "".join(_rand.choices(_string.ascii_letters + _string.digits, k=32))

    def _build_oauth_signature(method, url, params, consumer_secret, token_secret):
        sorted_params = "&".join(
            f"{_percent_encode(k)}={_percent_encode(v)}"
            for k, v in sorted(params.items())
        )
        base_string = f"{method.upper()}&{_percent_encode(url)}&{_percent_encode(sorted_params)}"
        signing_key = f"{_percent_encode(consumer_secret)}&{_percent_encode(token_secret)}"
        sig = hmac.new(
            signing_key.encode("utf-8"),
            base_string.encode("utf-8"),
            hashlib.sha1
        ).digest()
        return base64.b64encode(sig).decode("utf-8")

    def _build_auth_header(method, url, extra_params=None):
        oauth_params = {
            "oauth_consumer_key":     CONSUMER_KEY,
            "oauth_nonce":            _generate_nonce(),
            "oauth_signature_method": "HMAC-SHA1",
            "oauth_timestamp":        str(int(time.time())),
            "oauth_token":            ACCESS_TOKEN,
            "oauth_version":          "1.0",
        }
        all_params = {**oauth_params}
        if extra_params:
            all_params.update(extra_params)
        sig = _build_oauth_signature(method, url, all_params, CONSUMER_SECRET, ACCESS_SECRET)
        oauth_params["oauth_signature"] = sig
        header = "OAuth " + ", ".join(
            f'{_percent_encode(k)}="{_percent_encode(v)}"'
            for k, v in sorted(oauth_params.items())
        )
        return header

    # ── Twitter API v2 post with retry ───────────────────────────────────────
    def post_tweet(text, _retries=2):
        if not all([CONSUMER_KEY, CONSUMER_SECRET, ACCESS_TOKEN, ACCESS_SECRET]):
            add_log(aid, "Cannot post — Twitter OAuth credentials not configured. Set TWITTER_CONSUMER_KEY, TWITTER_CONSUMER_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_SECRET.", "warn")
            return False, "missing_credentials"
        last_err = None
        for attempt in range(_retries):
            try:
                auth_header = _build_auth_header("POST", TWEET_API)
                payload = json.dumps({"text": text}).encode("utf-8")
                req = urllib.request.Request(
                    TWEET_API,
                    data=payload,
                    headers={
                        "Authorization": auth_header,
                        "Content-Type":  "application/json",
                    },
                    method="POST"
                )
                resp = urllib.request.urlopen(req, timeout=15)
                data = json.loads(resp.read().decode())
                tweet_id = data.get("data", {}).get("id", "unknown")
                add_log(aid, f"✅ Tweet posted (id={tweet_id}): {text[:80]}", "ok")
                return True, tweet_id
            except urllib.error.HTTPError as e:
                body = e.read().decode()[:200]
                if e.code == 429:
                    retry_after = int(e.headers.get("Retry-After", "60"))
                    add_log(aid, f"Twitter rate limited (429) — retry after {retry_after}s", "warn")
                    return False, f"rate_limited:{retry_after}"
                elif e.code in (401, 403):
                    add_log(aid, f"Twitter auth error {e.code}: {body} — check credentials", "error")
                    return False, f"auth_error:{e.code}"
                elif e.code >= 500:
                    add_log(aid, f"Twitter server error {e.code} (attempt {attempt+1}/{_retries}): {body}", "warn")
                    last_err = body
                    if attempt < _retries - 1:
                        time.sleep(3 * (attempt + 1))
                        continue
                else:
                    add_log(aid, f"Tweet failed HTTP {e.code}: {body}", "warn")
                    return False, body
            except urllib.error.URLError as e:
                add_log(aid, f"Twitter network error (attempt {attempt+1}/{_retries}): {e.reason}", "warn")
                last_err = str(e.reason)
                if attempt < _retries - 1:
                    time.sleep(3 * (attempt + 1))
                    continue
            except Exception as e:
                add_log(aid, f"Tweet unexpected error: {type(e).__name__}: {e}", "error")
                return False, str(e)
        add_log(aid, f"Tweet failed after {_retries} attempts: {last_err}", "error")
        return False, last_err or "unknown error"

    # ── Register HTTP routes ────────────────────────────────────────────────
    from urllib.parse import urlparse

    _orig_do_GET  = Handler.do_GET
    _orig_do_POST = Handler.do_POST

    def _patched_do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/twitter/status":
            has_creds = all([CONSUMER_KEY, CONSUMER_SECRET, ACCESS_TOKEN, ACCESS_SECRET])
            with _queue_lock:
                pending = len(_post_queue)
            self._json({
                "ok": True,
                "configured": has_creds,
                "handle": TWITTER_HANDLE or "NEEDS_CONFIG",
                "pending_posts": pending,
                "total_posted": _stats.get("posted", 0),
            })
            return
        _orig_do_GET(self)

    def _patched_do_POST(self):
        path = urlparse(self.path).path
        if path == "/api/twitter/post":
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length) if length else b""
            try:
                body = json.loads(raw) if raw else {}
            except Exception:
                self._json({"ok": False, "error": "invalid JSON"}, 400)
                return
            msg = (body.get("text") or body.get("message") or "").strip()
            if not msg:
                self._json({"ok": False, "error": "text field required"}, 400)
                return
            # Truncate to 280 chars
            msg = msg[:280]
            with _queue_lock:
                if len(_post_queue) >= MAX_QUEUE:
                    self._json({"ok": False, "error": f"Queue full ({MAX_QUEUE} pending) — try again later"}, 429)
                    return
                _post_queue.append({"text": msg})
            add_log(aid, f"Tweet queued via API: {msg[:80]}", "ok")
            self._json({"ok": True, "queued": True, "length": len(msg)})
            return
        _orig_do_POST(self)

    Handler.do_GET  = _patched_do_GET
    Handler.do_POST = _patched_do_POST
    add_log(aid, "✓ Routes patched: GET /api/twitter/status | POST /api/twitter/post", "ok")

    # ── Stats ───────────────────────────────────────────────────────────────
    _stats = {"posted": 0, "failed": 0, "dedup_skips": 0}

    # ── FinTwit content templates ───────────────────────────────────────────
    def api_get(path):
        req = urllib.request.Request(f"{BASE_API}{path}", method="GET")
        resp = urllib.request.urlopen(req, timeout=8)
        return json.loads(resp.read().decode())

    # ── Shared status cache (TTL 30s) ────────────────────────────────────────
    _status_cache = {"data": None, "ts": 0}

    def _get_cached_status():
        now = time.time()
        if _status_cache["data"] and now - _status_cache["ts"] < 30:
            return _status_cache["data"]
        data = api_get("/api/status")
        _status_cache["data"] = data
        _status_cache["ts"] = now
        return data

    def fetch_metrics():
        try:
            status = _get_cached_status()
            agents = status.get("agents", [])
            total  = len(agents)
            active = sum(1 for a in agents if a.get("status") == "active")
            busy   = sum(1 for a in agents if a.get("status") == "busy")
            tasks_done = status.get("metrics", {}).get("tasks_done", 0)
            cpu_str = ram_str = "N/A"
            for a in agents:
                if a.get("id") == "sysmon":
                    task_str = a.get("task", "")
                    cpu_str = next((p.strip().replace("CPU ", "") for p in task_str.split("|") if "CPU" in p), "N/A")
                    ram_str = next((p.strip().replace("RAM ", "") for p in task_str.split("|") if "RAM" in p), "N/A")
                    break
            return {"total": total, "active": active, "busy": busy,
                    "tasks_done": tasks_done, "cpu": cpu_str, "ram": ram_str}
        except Exception as e:
            add_log(aid, f"fetch_metrics error: {e}", "warn")
            return {"total": 0, "active": 0, "busy": 0, "tasks_done": 0, "cpu": "N/A", "ram": "N/A"}

    def fetch_revenue():
        try:
            status = _get_cached_status()
            for a in status.get("agents", []):
                if a.get("id") == "revenue_tracker":
                    task_str = a.get("task", "")
                    mrr = next((p for p in task_str.split("|") if "MRR" in p), "MRR unknown").strip()
                    arr = next((p for p in task_str.split("|") if "ARR" in p), "").strip()
                    subs = next((p for p in task_str.split("|") if "Subs" in p), "").strip()
                    return {"mrr": mrr, "arr": arr, "subs": subs}
            return {"mrr": "MRR unknown", "arr": "", "subs": ""}
        except Exception as e:
            add_log(aid, f"fetch_revenue error: {e}", "warn")
            return {"mrr": "MRR unknown", "arr": "", "subs": ""}

    import random

    def draft_fintwit_pulse(metrics, revenue):
        # FinTwit-style system pulse — concise, data-driven, trader voice
        templates = [
            (f"📊 Live dashboard: {metrics['total']} AI agents | "
             f"{metrics['active']} active | {metrics['tasks_done']} tasks done\n"
             f"{revenue['mrr']}\n"
             f"Autonomous ops, zero human intervention.\n"
             f"secondmind.ai\n"
             f"#FinTwit #AI #SaaS #buildinpublic"),
            (f"⚡ System pulse:\n"
             f"{metrics['total']} agents running | CPU {metrics['cpu']} | RAM {metrics['ram']}\n"
             f"{revenue['mrr']} — self-funding AI fleet\n"
             f"This is the future of ops. secondmind.ai\n"
             f"#FinTwit #AI #Automation"),
            (f"🤖 {metrics['total']} autonomous agents. Zero operators.\n"
             f"Self-healing. Self-funding. 24/7.\n"
             f"{revenue['mrr']} | {metrics['tasks_done']} tasks completed\n"
             f"secondmind.ai\n"
             f"#FinTwit #AI #AgentOps #IndieHacker"),
            (f"📈 Building in public:\n"
             f"• {metrics['total']} AI agents live\n"
             f"• {metrics['active']} active / {metrics['busy']} busy\n"
             f"• {revenue['mrr']}\n"
             f"• CPU {metrics['cpu']} | RAM {metrics['ram']}\n"
             f"AI Command Centre HQ — secondmind.ai\n"
             f"#FinTwit #buildinpublic #SaaS"),
        ]
        return random.choice(templates)[:280]

    def draft_fintwit_cta(metrics, revenue):
        # Conversion-focused FinTwit tweet
        variants = [
            (f"Stop paying $2K/mo for 15 SaaS tools.\n\n"
             f"AI Command Centre HQ: {metrics['total']} autonomous agents — "
             f"growth, monitoring, research, revenue tracking.\n\n"
             f"Solo $49 | Team $149 | Enterprise $499/mo\n"
             f"secondmind.ai\n"
             f"#FinTwit #AI #SaaS"),
            (f"What if your entire ops team was AI?\n\n"
             f"{metrics['total']} agents. Self-healing. Self-funding.\n"
             f"{revenue['mrr']} — running autonomously right now.\n\n"
             f"From $49/mo → secondmind.ai\n"
             f"#FinTwit #AI #startup"),
            (f"Founders: your next hire should be an AI fleet.\n\n"
             f"AI Command Centre HQ — {metrics['total']} specialist agents:\n"
             f"Growth, monitoring, research, compliance, revenue.\n\n"
             f"Launch pricing from $49/mo.\n"
             f"secondmind.ai\n"
             f"#FinTwit #IndieHacker #AI"),
        ]
        return random.choice(variants)[:280]

    def draft_fintwit_insight():
        # FinTwit-style insight / thought leadership
        insights = [
            ("The real alpha in AI isn't chatbots — it's autonomous agent fleets "
             "that run your business 24/7 while you sleep.\n\n"
             "We built one. It works.\n"
             "secondmind.ai\n"
             "#FinTwit #AI #AgentOps"),
            ("Hot take: Most 'AI companies' are just API wrappers.\n\n"
             "We built a self-healing, self-funding autonomous system with "
             "27 specialist agents. No human operators.\n\n"
             "That's the difference.\n"
             "secondmind.ai\n"
             "#FinTwit #AI"),
            ("The SaaS model is broken. You pay for tools, then hire people to run them.\n\n"
             "AI Command Centre HQ: the tools ARE the team.\n"
             "Autonomous agents that do the work, not just answer questions.\n\n"
             "secondmind.ai\n"
             "#FinTwit #SaaS #AI"),
            ("If your AI can't fix itself when it breaks, it's not autonomous.\n\n"
             "Our Reforger agent patches bugs in production. AlertWatch catches anomalies. "
             "PolicyPro enforces compliance. Zero human escalation.\n\n"
             "secondmind.ai\n"
             "#FinTwit #AI"),
        ]
        return random.choice(insights)[:280]

    # ── Main loop ───────────────────────────────────────────────────────────
    creds_ok = all([CONSUMER_KEY, CONSUMER_SECRET, ACCESS_TOKEN, ACCESS_SECRET])
    if creds_ok:
        set_agent(aid, status="active", progress=20,
                  task=f"Online — @{TWITTER_HANDLE or 'configured'} | awaiting posts")
        add_log(aid, f"Twitter credentials configured — handle @{TWITTER_HANDLE}", "ok")
    else:
        set_agent(aid, status="active", progress=10,
                  task="Online — Twitter creds not set (queue-only mode)")
        add_log(aid, "Twitter credentials not set — running in queue-only mode (posts held until configured)", "warn")

    cycle = 0
    # Content rotation: pulse, cta, insight
    content_types = ["pulse", "cta", "insight", "pulse", "pulse", "cta"]

    while not agent_should_stop(aid):
        cycle += 1
        now = time.time()

        try:
            # ── Drain post queue (delegated posts) ──────────────────────────
            with _queue_lock:
                pending = list(_post_queue)
                _post_queue.clear()

            if pending:
                set_agent(aid, status="active", progress=50,
                          task=f"Sending {len(pending)} queued tweet(s)…")
                held = []
                for idx, item in enumerate(pending):
                    elapsed = time.time() - _last_post_time
                    if elapsed < 3600:
                        held = pending[idx:]
                        break
                    # Dedup check
                    h = hashlib.md5(item["text"].encode()).hexdigest()
                    if h in _posted_hashes and now - _posted_hashes[h] < 86400:
                        add_log(aid, f"⏭ Dedup skip: {item['text'][:40]}", "ok")
                        _stats["dedup_skips"] += 1
                        continue
                    ok, result = post_tweet(item["text"])
                    if ok:
                        _stats["posted"] += 1
                        _posted_hashes[h] = time.time()
                        _last_post_time = time.time()
                    else:
                        _stats["failed"] += 1
                    # One post per cycle
                    if idx + 1 < len(pending):
                        held = pending[idx + 1:]
                    break

                if held:
                    wait = int(3600 - (time.time() - _last_post_time))
                    add_log(aid, f"Rate limit: next tweet in {wait}s — holding {len(held)}", "info")
                    with _queue_lock:
                        _post_queue[:0] = held

            # ── Organic FinTwit content (every 2 hours if queue empty) ──────
            with _queue_lock:
                queue_empty = len(_post_queue) == 0
            elapsed_since_post = time.time() - _last_post_time

            if queue_empty and elapsed_since_post >= 7200 and creds_ok:
                metrics = fetch_metrics()
                revenue = fetch_revenue()
                ctype = content_types[cycle % len(content_types)]

                if ctype == "pulse":
                    tweet = draft_fintwit_pulse(metrics, revenue)
                elif ctype == "cta":
                    tweet = draft_fintwit_cta(metrics, revenue)
                else:
                    tweet = draft_fintwit_insight()

                h = hashlib.md5(tweet.encode()).hexdigest()
                # Prune old hashes
                _posted_hashes = {k: v for k, v in _posted_hashes.items() if now - v < 86400}

                if h not in _posted_hashes:
                    ok, result = post_tweet(tweet)
                    if ok:
                        _stats["posted"] += 1
                        _posted_hashes[h] = time.time()
                        _last_post_time = time.time()
                    else:
                        _stats["failed"] += 1

            # ── Update status ───────────────────────────────────────────────
            with _queue_lock:
                q_count = len(_post_queue)
            status_parts = [f"Posted: {_stats['posted']}"]
            if q_count:
                status_parts.append(f"Queued: {q_count}")
            if TWITTER_HANDLE:
                status_parts.append(f"@{TWITTER_HANDLE}")
            set_agent(aid, status="active", progress=75,
                      task=" | ".join(status_parts))

        except Exception as e:
            add_log(aid, f"FinTwit loop error: {e}", "warn")
            set_agent(aid, status="active", progress=40,
                      task=f"Error: {str(e)[:80]}")

        agent_sleep(aid, 120)

    set_agent(aid, status="idle", progress=0, task="FinTwit agent stopped")
"""

# ── Spawn via API when run directly ──────────────────────────────────────────
if __name__ == "__main__":
    import json, sys
    import urllib.request

    BASE = "http://localhost:5050"

    payload = json.dumps({
        "agent_id": "fintwit",
        "name": "FinTwit",
        "role": "FinTwit Gateway — posts market-savvy updates and system pulses to Twitter/X",
        "emoji": "📊",
        "color": "#1DA1F2",
        "code": FINTWIT_CODE,
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{BASE}/api/agent/spawn",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    resp = urllib.request.urlopen(req, timeout=10)
    result = json.loads(resp.read().decode())

    if result.get("ok"):
        print("✓ FinTwit agent spawned successfully")
    else:
        print(f"✗ Spawn failed: {result}")
        sys.exit(1)
