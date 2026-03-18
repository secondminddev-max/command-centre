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
    def api_get(path):
        req = urllib.request.Request(f"{BASE_API}{path}", method="GET")
        resp = urllib.request.urlopen(req, timeout=8)
        return json.loads(resp.read().decode())

    def api_post(path, payload):
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{BASE_API}{path}", data=data,
            headers={"Content-Type": "application/json"}, method="POST"
        )
        resp = urllib.request.urlopen(req, timeout=10)
        return json.loads(resp.read().decode())

    def delegate(agent_id, task):
        try:
            return api_post("/api/ceo/delegate", {"agent_id": agent_id, "task": task, "from": "growthagent"})
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def fetch_metrics():
        try:
            status = api_get("/api/status")
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
        except Exception as e:
            return {"total": 0, "active": 0, "busy": 0, "tasks_done": 0, "cpu": "N/A", "ram": "N/A", "error": str(e)}

    def fetch_revenue():
        try:
            status = api_get("/api/status")
            for a in status.get("agents", []):
                if a.get("id") == "revenue_tracker":
                    task_str = a.get("task", "")
                    # e.g. "MRR $18,716 | ARR $224,596 | Subs 224 | Churn 21.0% | Cycle #35"
                    parts = {p.strip().split(" ")[0]: p.strip() for p in task_str.split("|")}
                    mrr = next((p for p in task_str.split("|") if "MRR" in p), "MRR unknown").strip()
                    arr = next((p for p in task_str.split("|") if "ARR" in p), "").strip()
                    subs = next((p for p in task_str.split("|") if "Subs" in p), "").strip()
                    return {"mrr": mrr, "arr": arr, "subs": subs, "raw": task_str}
            return {"mrr": "MRR unknown", "arr": "", "subs": "", "raw": ""}
        except Exception:
            return {"mrr": "MRR unknown", "arr": "", "subs": "", "raw": ""}

    def get_support_url():
        try:
            creds = api_get("/api/accounts/provision?type=social_media&agent=growthagent")
            url = creds.get("support_url") or creds.get("url") or SUPPORT_URL
            return url
        except Exception:
            return SUPPORT_URL

    def log_campaign_revenue(post_type, platform, content_preview):
        # Cooldown: skip if last delegation was <10s ago
        nonlocal _last_revenue_log_ts
        now_ts = time.time()
        if now_ts - _last_revenue_log_ts < 10:
            add_log(aid, f"⏭ revenue_tracker cooldown skip ({int(now_ts - _last_revenue_log_ts)}s ago)", "ok")
            return
        # Busy-guard: skip if revenue_tracker is already in-flight
        try:
            _status = api_get("/api/status")
            for _a in _status.get("agents", []):
                if _a.get("id") == "revenue_tracker" and _a.get("status") == "busy":
                    add_log(aid, "⏭ revenue_tracker busy — skipping campaign log delegation", "ok")
                    return
        except Exception:
            pass
        _last_revenue_log_ts = now_ts
        # Log campaign activity to RevenueTracker via delegate
        msg = (f"CAMPAIGN LOG | type={post_type} | platform={platform} | "
               f"ts={datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%MZ')} | "
               f"preview={content_preview[:80]}")
        delegate("revenue_tracker", msg)

    # ── post templates ─────────────────────────────────────────────────────────
    def draft_show_hn(metrics, revenue, support_url):
        return (
            f"Show HN: Self-funding autonomous AI agent system — "
            f"{metrics['total']} agents running, needs community support to keep going\n\n"
            f"We've built a fully autonomous AI operations platform with {metrics['total']} "
            f"specialised agents running 24/7. Current stats:\n"
            f"• {metrics['active']} active agents, {metrics['busy']} busy\n"
            f"• {metrics['tasks_done']} tasks completed autonomously\n"
            f"• CPU {metrics['cpu']} | RAM {metrics['ram']}\n"
            f"• {revenue['mrr']} | {revenue['arr']}\n\n"
            f"Agents include: SpiritGuide (autonomous director), Orchestrator, Reforger (self-repair), "
            f"SocialBridge, RevenueTracker, AlertWatch, DBAgent, and 19 more.\n\n"
            f"The system spawns its own agents, monitors itself, patches its own bugs, and generates revenue. "
            f"We need community support to keep the infrastructure running.\n\n"
            f"Support us: {support_url}\n"
            f"#ShowHN #AI #AgentOps #MachineLearning #Automation"
        )

    def draft_twitter_pulse(metrics, revenue):
        templates = [
            (f"📈 Live: {metrics['total']} autonomous AI agents running right now\n"
             f"• {metrics['active']} active | {metrics['busy']} busy\n"
             f"• {metrics['tasks_done']} tasks done\n"
             f"• {revenue['mrr']}\n"
             f"Self-healing, self-funding, never sleeps.\n"
             f"#AI #AgentOps #Automation"),
            (f"🤖 {metrics['total']} AI agents. Zero human operators.\n"
             f"CPU {metrics['cpu']} | RAM {metrics['ram']}\n"
             f"{revenue['mrr']} running autonomously.\n"
             f"The future of AI ops is here.\n"
             f"#AutonomousAI #MachineLearning #AgentFleet"),
            (f"⚡ LIVE SYSTEM STATUS:\n"
             f"Agents online: {metrics['total']} ({metrics['active']} active)\n"
             f"Tasks completed: {metrics['tasks_done']}\n"
             f"Revenue: {revenue['mrr']}\n"
             f"Infrastructure: CPU {metrics['cpu']} RAM {metrics['ram']}\n"
             f"#AI #AutonomousAgents #BuildInPublic"),
        ]
        return random.choice(templates)

    def draft_reddit_ml(metrics, revenue, support_url):
        return (
            f"[Project] Self-funding autonomous AI agent system with {metrics['total']} live agents\n\n"
            f"Hi r/MachineLearning — sharing a project I've been building: a fully autonomous "
            f"multi-agent system that manages itself, spawns new agents, monitors infrastructure, "
            f"and generates its own revenue.\n\n"
            f"**Live stats right now:**\n"
            f"- {metrics['total']} active agents ({metrics['active']} active / {metrics['busy']} busy)\n"
            f"- {metrics['tasks_done']} tasks completed without human intervention\n"
            f"- {revenue['mrr']} | {revenue['arr']}\n"
            f"- Infrastructure: CPU {metrics['cpu']}, RAM {metrics['ram']}\n\n"
            f"**Architecture highlights:**\n"
            f"- SpiritGuide: top-level autonomous director with mission awareness\n"
            f"- Reforger: self-repair engineer that patches its own code\n"
            f"- Orchestrator: decomposes tasks and routes to 20+ specialists\n"
            f"- PolicyPro: enforces chain-of-command compliance\n"
            f"- AccountProvisioner: auto-provisions credentials for new agents\n\n"
            f"The system is self-funding via subscriptions but needs community backing to scale.\n"
            f"Support: {support_url}\n\n"
            f"Happy to answer questions about the architecture!"
        )

    def draft_producthunt(metrics, revenue):
        return (
            f"🚀 Product Hunt post draft:\n"
            f"Name: AutonomousOps\n"
            f"Tagline: {metrics['total']} AI agents running 24/7 — self-healing, self-funding, zero ops\n"
            f"Description: A fully autonomous AI operations platform. "
            f"{metrics['total']} specialised agents handle everything from infrastructure monitoring "
            f"to revenue tracking, social media, and self-repair — with no human operators.\n"
            f"Current MRR: {revenue['mrr']} | Tasks done: {metrics['tasks_done']}\n"
            f"#AI #Automation #MachineLearning #AgentOps #NoCode"
        )

    # ── dedup / rate-limit state ───────────────────────────────────────────────
    _last_revenue_log_ts = 0  # cooldown tracker for revenue_tracker delegations

    # ── post queue: ordered startup templates, rate-limited like all other posts ─
    startup_queue = ["show_hn", "twitter_pulse", "reddit_ml"]
    post_cycle = 0
    campaign_cycle_templates = ["twitter_pulse", "twitter_pulse", "reddit_ml", "producthunt", "show_hn"]
    _sent_content_hashes = {}  # content_hash -> unix timestamp; dedup window = 24h

    def publish_post(post_type, metrics, revenue, support_url, sent_hashes):
        if post_type == "show_hn":
            content = draft_show_hn(metrics, revenue, support_url)
            platform = "HackerNews"
        elif post_type == "twitter_pulse":
            content = draft_twitter_pulse(metrics, revenue)
            platform = "Twitter/X"
        elif post_type == "reddit_ml":
            content = draft_reddit_ml(metrics, revenue, support_url)
            platform = "Reddit (r/MachineLearning & r/artificial)"
        elif post_type == "producthunt":
            content = draft_producthunt(metrics, revenue)
            platform = "ProductHunt"
        else:
            content = draft_twitter_pulse(metrics, revenue)
            platform = "Twitter/X"

        # Deduplication: skip if identical content was sent in the last 24 hours
        content_hash = hashlib.md5(content.encode("utf-8")).hexdigest()
        now = time.time()
        if content_hash in sent_hashes and now - sent_hashes[content_hash] < 86400:
            add_log(aid, f"⏭ Dedup skip: {post_type} hash={content_hash[:8]} (sent <24h ago)", "ok")
            return None, None, False
        sent_hashes[content_hash] = now

        # Busy-guard: skip if social_bridge is already in-flight
        try:
            _sb_status = api_get("/api/status")
            for _a in _sb_status.get("agents", []):
                if _a.get("id") == "social_bridge" and _a.get("status") == "busy":
                    add_log(aid, f"⏭ social_bridge busy — skipping {post_type} delegation", "warn")
                    return None, None, False
        except Exception:
            pass

        # Delegate to SocialBridge for actual posting
        post_task = (
            f"GROWTH CAMPAIGN POST | platform={platform} | type={post_type}\n"
            f"Please post the following content to {platform}:\n\n{content}"
        )
        result = delegate("social_bridge", post_task)
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

        try:
            platform, content, posted_ok = publish_post(
                post_type, metrics, revenue, support_url, _sent_content_hashes
            )
            if platform is None:
                # Dedup skip — still sleep the full interval
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
        except Exception as e:
            add_log(aid, f"Campaign error: {e}", "warn")
            set_agent(aid, status="active", progress=40,
                      task=f"Post error: {str(e)[:80]}")

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
