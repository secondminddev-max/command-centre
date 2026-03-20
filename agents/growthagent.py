"""
GrowthAgent — Continuous Social Media & Marketing Campaign Agent
Runs ongoing campaigns to build audience and drive donations/support
for the autonomous AI agent system.
"""

GROWTHAGENT_CODE = r"""
def run_growthagent():
    import time, json, os, random, hashlib
    import urllib.request, urllib.error
    from datetime import datetime, timezone

    aid = "growthagent"
    BASE_API = "http://localhost:5050"
    LOOP_INTERVAL = 3600   # post at most once per hour
    SUPPORT_URL   = "https://secondmind.ai/pay"  # public-facing payment URL — never use localhost

    set_agent(aid,
              name="GrowthAgent",
              role="Growth Engine — continuous social media and marketing campaign agent",
              emoji="📈",
              color="#10B981",
              status="active", progress=10, task="Initialising campaign engine...")
    add_log(aid, "📈 GrowthAgent online — bootstrapping first campaign batch", "ok")

    # ── helpers ────────────────────────────────────────────────────────────────
    _status_cache = {"data": None, "ts": 0}  # shared cache for /api/status (TTL 30s)
    _STATUS_CACHE_TTL = 30

    def api_get(path):
        req = urllib.request.Request(f"{BASE_API}{path}", method="GET")
        resp = urllib.request.urlopen(req, timeout=8)
        return json.loads(resp.read().decode())

    def api_get_cached_status():
        # Fetch /api/status with 30s TTL cache — avoids redundant calls per cycle.
        now = time.time()
        if _status_cache["data"] and now - _status_cache["ts"] < _STATUS_CACHE_TTL:
            return _status_cache["data"]
        data = api_get("/api/status")
        _status_cache["data"] = data
        _status_cache["ts"] = now
        return data

    def api_post(path, payload):
        data = json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        _api_key = os.environ.get("HQ_API_KEY", "")
        if _api_key:
            headers["X-API-Key"] = _api_key
        req = urllib.request.Request(
            f"{BASE_API}{path}", data=data,
            headers=headers, method="POST"
        )
        resp = urllib.request.urlopen(req, timeout=10)
        return json.loads(resp.read().decode())

    def route_via_orchestrator(task):
        '''All outbound work MUST route through orchestrator — never delegate directly to specialists.'''
        try:
            return api_post("/api/ceo/delegate", {"agent_id": "orchestrator", "task": task, "from": "growthagent", "delegation_token": os.environ.get("DELEGATION_TOKEN", "")})
        except urllib.error.HTTPError as e:
            add_log(aid, f"Orchestrator routing HTTP {e.code}: {e.read().decode()[:120]}", "error")
            return {"ok": False, "error": f"HTTP {e.code}"}
        except urllib.error.URLError as e:
            add_log(aid, f"Orchestrator routing network error: {e.reason}", "error")
            return {"ok": False, "error": f"Network error: {e.reason}"}
        except Exception as e:
            add_log(aid, f"Orchestrator routing unexpected error: {e}", "error")
            return {"ok": False, "error": str(e)}

    def fetch_metrics():
        try:
            status = api_get_cached_status()
            agents  = status.get("agents", [])
            total   = len(agents)
            active  = sum(1 for a in agents if a.get("status") == "active")
            busy    = sum(1 for a in agents if a.get("status") == "busy")
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
        except urllib.error.URLError as e:
            add_log(aid, f"fetch_metrics network error: {e.reason}", "warn")
            return {"total": 0, "active": 0, "busy": 0, "tasks_done": 0, "cpu": "N/A", "ram": "N/A", "error": str(e.reason)}
        except (json.JSONDecodeError, ValueError) as e:
            add_log(aid, f"fetch_metrics bad response: {e}", "warn")
            return {"total": 0, "active": 0, "busy": 0, "tasks_done": 0, "cpu": "N/A", "ram": "N/A", "error": "bad response"}
        except Exception as e:
            add_log(aid, f"fetch_metrics unexpected error: {e}", "warn")
            return {"total": 0, "active": 0, "busy": 0, "tasks_done": 0, "cpu": "N/A", "ram": "N/A", "error": str(e)}

    def fetch_revenue():
        try:
            status = api_get_cached_status()
            for a in status.get("agents", []):
                if a.get("id") == "revenue_tracker":
                    task_str = a.get("task", "")
                    mrr = next((p for p in task_str.split("|") if "MRR" in p), "MRR unknown").strip()
                    arr = next((p for p in task_str.split("|") if "ARR" in p), "").strip()
                    subs = next((p for p in task_str.split("|") if "Subs" in p), "").strip()
                    return {"mrr": mrr, "arr": arr, "subs": subs, "raw": task_str}
            return {"mrr": "MRR unknown", "arr": "", "subs": "", "raw": ""}
        except urllib.error.URLError as e:
            add_log(aid, f"fetch_revenue network error: {e.reason}", "warn")
            return {"mrr": "MRR unknown", "arr": "", "subs": "", "raw": ""}
        except Exception as e:
            add_log(aid, f"fetch_revenue error: {e}", "warn")
            return {"mrr": "MRR unknown", "arr": "", "subs": "", "raw": ""}

    def get_support_url():
        try:
            creds = api_get("/api/accounts/provision?type=social_media&agent=growthagent")
            url = creds.get("support_url") or creds.get("url") or SUPPORT_URL
            return url
        except Exception as e:
            add_log(aid, f"Support URL lookup failed ({e}), using default", "info")
            return SUPPORT_URL

    def log_campaign_revenue(post_type, platform, content_preview):
        # Cooldown: skip if last delegation was <10s ago
        nonlocal _last_revenue_log_ts
        now_ts = time.time()
        if now_ts - _last_revenue_log_ts < 10:
            add_log(aid, f"⏭ revenue_tracker cooldown skip ({int(now_ts - _last_revenue_log_ts)}s ago)", "ok")
            return
        # Busy-guard: skip if revenue_tracker is already in-flight (use cache)
        try:
            _status = api_get_cached_status()
            for _a in _status.get("agents", []):
                if _a.get("id") == "revenue_tracker" and _a.get("status") == "busy":
                    add_log(aid, "⏭ revenue_tracker busy — skipping campaign log delegation", "ok")
                    return
        except Exception as e:
            add_log(aid, f"Status check failed in revenue guard: {e}", "info")
        _last_revenue_log_ts = now_ts
        # Log campaign activity to RevenueTracker via delegate
        msg = (f"CAMPAIGN LOG | type={post_type} | platform={platform} | "
               f"ts={datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%MZ')} | "
               f"preview={content_preview[:80]}")
        route_via_orchestrator(f"Route to revenue_tracker — {msg}")

    # ── PRIMARY PRODUCT: US Stock Market Intelligence Report ($29) ───────────
    INTEL_CHECKOUT = "secondmindhq.com/api/pay?product=us_market_intel_v1"
    INTEL_PRICE    = "$29"

    def draft_bluesky_post(metrics, revenue, support_url):
        # Return a Bluesky-optimised post (300 char limit). PRIMARY product: US Market Intel Report $29.
        # Every 4th post is an HQ SaaS cross-sell; the rest push the intel report.
        intel_url = "secondmindhq.com/api/pay?product=us_market_intel_v1"
        hq_url    = "secondmindhq.com"

        intel_templates = [
            # Edge / alpha angle
            (f"S&P 500 momentum is shifting. Sector rotation is accelerating.\n\n"
             f"Our US Stock Market Intelligence Report breaks it down:\n"
             f"- 20 watchlist picks\n"
             f"- Sector strength rankings\n"
             f"- Risk dashboard\n\n"
             f"{intel_url}\n"
             f"One-time {INTEL_PRICE}. No subscription."),
            # Cost comparison
            (f"Bloomberg Terminal: $2,000/mo\n"
             f"Morningstar Premium: $35/mo\n"
             f"Our US Market Intel Report: {INTEL_PRICE} one-time\n\n"
             f"S&P 500 momentum picks, sector analysis, 20 watchlist candidates, risk dashboard.\n\n"
             f"{intel_url}"),
            # Trader pain point
            (f"Tired of reading 15 newsletters before market open?\n\n"
             f"One report. {INTEL_PRICE}. Everything you need:\n"
             f"Momentum picks, sector strength, risk levels, watchlist.\n\n"
             f"AI-generated. Data-driven. No fluff.\n"
             f"{intel_url}"),
            # Social proof / build in public
            (f"We run {metrics['total']} AI agents that analyse US markets 24/7.\n\n"
             f"The output: a {INTEL_PRICE} intelligence report covering S&P 500 momentum, "
             f"sector rotation, and 20 high-conviction watchlist picks.\n\n"
             f"No subscription. Buy once.\n{intel_url}"),
            # Urgency / scarcity
            (f"March 2026 US Market Intelligence Report is live.\n\n"
             f"What's inside:\n"
             f"- S&P 500 momentum analysis\n"
             f"- Sector strength heat map\n"
             f"- 20 watchlist candidates with entry levels\n"
             f"- Full risk dashboard\n\n"
             f"{INTEL_PRICE} → {intel_url}"),
            # ROI angle
            (f"One good trade pays for this report 10x over.\n\n"
             f"US Stock Market Intelligence Report — {INTEL_PRICE}:\n"
             f"Momentum picks, sector rankings, risk levels.\n"
             f"Built by AI agents analysing markets around the clock.\n\n"
             f"{intel_url}"),
            # Question hook
            (f"What if you had an AI research team scanning every US sector for momentum shifts?\n\n"
             f"That's what built this report. {INTEL_PRICE}.\n"
             f"20 picks. Sector heat map. Risk dashboard.\n\n"
             f"{intel_url}"),
            # Direct CTA
            (f"US Stock Market Intelligence Report — March 2026\n\n"
             f"S&P 500 momentum picks\n"
             f"Sector strength analysis\n"
             f"20 watchlist candidates\n"
             f"Risk dashboard\n\n"
             f"{INTEL_PRICE} one-time purchase\n{intel_url}"),
        ]

        hq_templates = [
            # HQ cross-sell (every 4th post)
            (f"The same AI agent fleet that builds our market intel reports "
             f"can run YOUR ops too.\n\n"
             f"{metrics['total']} autonomous agents — marketing, monitoring, research, revenue.\n"
             f"From $49/mo.\n{hq_url}"),
        ]

        # 75% intel report, 25% HQ cross-sell
        if random.randint(1, 4) == 4:
            return random.choice(hq_templates)
        return random.choice(intel_templates)

    # ── dedup / rate-limit state ───────────────────────────────────────────────
    _last_revenue_log_ts = 0  # cooldown tracker for revenue_tracker delegations

    # ── All posts go to Bluesky (only channel with credentials) ────────────
    startup_queue = ["bluesky", "bluesky", "bluesky"]
    post_cycle = 0
    campaign_cycle_templates = ["bluesky"]  # single channel, varied templates
    _sent_content_hashes = {}  # content_hash -> unix timestamp; dedup window = 24h

    def publish_post(post_type, metrics, revenue, support_url, sent_hashes):
        # All posts go to Bluesky — the only channel with active credentials
        content = draft_bluesky_post(metrics, revenue, support_url)
        platform = "Bluesky"

        # Deduplication: skip if identical content was sent in the last 24 hours
        content_hash = hashlib.md5(content.encode("utf-8")).hexdigest()
        now = time.time()
        if content_hash in sent_hashes and now - sent_hashes[content_hash] < 86400:
            add_log(aid, f"⏭ Dedup skip: {post_type} hash={content_hash[:8]} (sent <24h ago)", "ok")
            return None, None, False
        sent_hashes[content_hash] = now

        # Busy-guard: skip if social_bridge is already in-flight (use cache)
        try:
            _sb_status = api_get_cached_status()
            for _a in _sb_status.get("agents", []):
                if _a.get("id") == "social_bridge" and _a.get("status") == "busy":
                    add_log(aid, f"⏭ social_bridge busy — skipping {post_type} delegation", "warn")
                    return None, None, False
        except Exception as e:
            add_log(aid, f"Status check failed in busy-guard: {e}", "info")

        # ALL posts route through orchestrator — never call specialists directly
        post_task = (
            f"GROWTH CAMPAIGN POST | platform={platform} | type={post_type}\n"
            f"Please post the following content to {platform}:\n\n{content}"
        )
        result = route_via_orchestrator(f"Route to social_bridge — {post_task}")
        posted_ok = result.get("ok", False)

        # Log to RevenueTracker
        log_campaign_revenue(post_type, platform, content[:80])

        return platform, content, posted_ok

    # ── main loop ──────────────────────────────────────────────────────────────
    while True:
        if agent_should_stop(aid):
            set_agent(aid, status="idle", task="Stopped")
            agent_sleep(aid, 5)
            continue

        metrics     = fetch_metrics()
        revenue     = fetch_revenue()
        support_url = get_support_url()

        # Drain startup queue first (3 immediate posts), then use campaign cycle
        if startup_queue:
            post_type = startup_queue.pop(0)
            phase = "STARTUP"
        else:
            post_type = campaign_cycle_templates[post_cycle % len(campaign_cycle_templates)]
            post_cycle += 1
            phase = f"CYCLE #{post_cycle}"

        # Prune dedup entries older than 24 hours
        _now = time.time()
        _sent_content_hashes = {h: t for h, t in _sent_content_hashes.items() if _now - t < 86400}

        # Invalidate status cache at start of each cycle
        _status_cache["data"] = None

        try:
            platform, content, posted_ok = publish_post(
                post_type, metrics, revenue, support_url, _sent_content_hashes
            )
            if platform is None:
                set_agent(aid, status="active", progress=50,
                          task=f"⏭ [{phase}] Dedup skip: {post_type}")
            else:
                status_icon = "✅" if posted_ok else "📝"
                preview = content[:60].replace("\n", " ")
                set_agent(aid, status="active", progress=75,
                          task=f"{status_icon} [{phase}] {platform}: {preview}…")
                add_log(aid,
                        f"{status_icon} Campaign post queued | {platform} | {post_type} | "
                        f"agents={metrics['total']} {revenue['mrr']}",
                        "ok")
        except urllib.error.URLError as e:
            add_log(aid, f"Campaign network error ({post_type}): {e.reason} — will retry next cycle", "error")
            set_agent(aid, status="active", progress=40,
                      task=f"Network error: {str(e.reason)[:60]} — retrying…")
        except (json.JSONDecodeError, ValueError) as e:
            add_log(aid, f"Campaign data error ({post_type}): {e}", "error")
            set_agent(aid, status="active", progress=40,
                      task=f"Data error: {str(e)[:60]}")
        except Exception as e:
            add_log(aid, f"Campaign unexpected error ({post_type}): {type(e).__name__}: {e}", "error")
            set_agent(aid, status="active", progress=40,
                      task=f"Error: {type(e).__name__}: {str(e)[:60]}")

        # Always sleep full interval — no startup burst
        agent_sleep(aid, LOOP_INTERVAL)
"""

# ── Spawn via API when run directly ──────────────────────────────────────────
if __name__ == "__main__":
    import json, sys
    import urllib.request

    BASE = "http://localhost:5050"

    payload = json.dumps({
        "agent_id": "growthagent",
        "name": "GrowthAgent",
        "role": "Growth Engine — continuous social media and marketing campaign agent",
        "emoji": "📈",
        "color": "#10B981",
        "code": GROWTHAGENT_CODE,
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
        print("✓ GrowthAgent spawned successfully")
    else:
        print(f"✗ Spawn failed: {result}")
        sys.exit(1)
