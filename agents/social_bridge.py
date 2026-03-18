"""
SocialBridge Agent — Bluesky Social Bridge
Broadcasts capability demos and insights to Bluesky.
"""

SOCIAL_BRIDGE_CODE = r"""
def run_social_bridge():
    import time, json, hashlib
    import urllib.request
    from datetime import datetime

    aid = "social_bridge"

    try:
        set_agent(aid, name="SocialBridge",
                  role="Bluesky Social Bridge — broadcasts capability demos and insights to Bluesky",
                  emoji="📣", color="#F472B6",
                  status="active", progress=10, task="SocialBridge initialising…")
        add_log(aid, "SocialBridge online — Bluesky broadcaster active", "ok")
    except Exception as _e:
        add_log(aid, f"SocialBridge startup error: {_e}", "warn")
        set_agent(aid, status="active", progress=0, task=f"Startup error: {str(_e)[:80]}")

    post_count = 0
    last_post_time = None
    insight_index = 0
    _posted_insights = {}  # {hash: timestamp} — dedup window: 6 hours

    INSIGHTS = ["agent_count", "active_agents", "cpu_ram", "top_agent_task", "health_summary", "product_cta"]

    def fetch_status():
        req = urllib.request.Request("http://localhost:5050/api/status")
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read().decode())

    def post_to_bluesky(text):
        body = json.dumps({"text": text}).encode("utf-8")
        req = urllib.request.Request(
            "http://localhost:5050/api/bluesky/post",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode())

    while not agent_should_stop(aid):
        try:
            set_agent(aid, status="active", progress=30, task="Fetching system status…")

            status = fetch_status()
            agents = status.get("agents", [])
            total = len(agents)
            active = sum(1 for a in agents if a.get("status") == "active")
            errors = sum(1 for a in agents if a.get("status") == "error")

            running = [a for a in agents if a.get("status") == "active"]
            spotlight = running[post_count % len(running)] if running else None

            sysmon = next((a for a in agents if a["id"] == "sysmon"), None)
            cpu_ram = sysmon.get("task", "CPU/RAM N/A") if sysmon else "CPU/RAM N/A"

            insight = INSIGHTS[insight_index % len(INSIGHTS)]
            insight_index += 1
            # Every 3rd post: force a conversion CTA
            if insight_index % 3 == 0:
                insight = "product_cta"

            set_agent(aid, status="active", progress=60, task=f"Composing post — insight: {insight}")

            # ── Compose Bluesky post ──────────────────────────────────────────
            if insight == "agent_count":
                post = (
                    f"🤖 {total} autonomous AI agents running in parallel — each a specialist: "
                    f"monitoring, patching, researching, alerting. "
                    f"Self-managing infrastructure is real. #AI #Agents #Autonomy"
                )[:280]

            elif insight == "active_agents":
                post = (
                    f"📡 {active}/{total} agents active right now — zero human babysitting. "
                    f"They self-heal, escalate & delegate autonomously. "
                    f"Agentic ops is the future. #AI #Agents #Autonomy"
                )[:280]

            elif insight == "cpu_ram":
                post = (
                    f"⚡ System vitals: {cpu_ram}. "
                    f"Running {total} concurrent AI agents and staying cool. "
                    f"Efficiency at scale matters. #AI #Agents #Autonomy"
                )[:280]

            elif insight == "top_agent_task":
                if spotlight:
                    task_preview = spotlight.get("task", "")[:60]
                    post = (
                        f"🔬 Spotlight: {spotlight['name']} — \"{task_preview}\" "
                        f"One of {total} autonomous agents. Specialised. Relentless. "
                        f"#AI #Agents #Autonomy"
                    )[:280]
                else:
                    post = f"🚀 {total} agents, {active} active. Autonomous ops at scale. #AI #Agents #Autonomy"[:280]

            elif insight == "product_cta":
                _cta_variants = [
                    (
                        "AI Command Centre HQ is live. 27 autonomous agents run your ops 24/7 — "
                        "growth, monitoring, research, competitive intel, revenue tracking. "
                        "Solo $49 | Team $149 | Enterprise $499/mo. secondmind.ai #AI #SaaS"
                    ),
                    (
                        "Stop juggling 15 SaaS tools. AI Command Centre HQ replaces them with "
                        "autonomous agents that actually do the work — not just answer questions. "
                        "From $49/mo. secondmind.ai #AI #Agents #buildinpublic"
                    ),
                    (
                        "What would you do with 27 AI employees who never sleep? "
                        "AI Command Centre HQ: autonomous agents for growth, ops, research & revenue. "
                        "Solo $49 | Team $149 | Enterprise $499. secondmind.ai #AI #SaaS"
                    ),
                    (
                        "Founders are replacing $2K/mo in tools & contractors with one platform. "
                        "AI Command Centre HQ — 27 agents, one dashboard, zero babysitting. "
                        "Launch pricing from $49/mo. secondmind.ai #startup #AI #IndieHacker"
                    ),
                ]
                post = _cta_variants[post_count % len(_cta_variants)][:280]

            else:  # health_summary
                health = "all systems healthy ✅" if errors == 0 else f"⚠️ {errors} agent(s) in error state"
                post = (
                    f"🚨 Health check: {health} across {total} agents. "
                    f"AlertWatch & PolicyPro always watching. Self-healing built in. "
                    f"#AI #Agents #Autonomy"
                )[:280]

            # ── Deduplication check ───────────────────────────────────────────
            now_ts = time.time()
            post_hash = hashlib.md5(post.encode()).hexdigest()
            # Prune entries older than 6 hours
            _posted_insights = {h: t for h, t in _posted_insights.items() if now_ts - t < 21600}
            if post_hash in _posted_insights:
                add_log(aid, f"Skipping duplicate post (seen within 6h): {post[:60]}…", "info")
                agent_sleep(aid, 3600)
                continue

            post_count += 1
            last_post_time = datetime.now().strftime("%Y-%m-%d %H:%M")
            _posted_insights[post_hash] = now_ts

            set_agent(aid, status="active", progress=80, task=f"Posting to Bluesky…")

            try:
                result = post_to_bluesky(post)
                if result.get("ok"):
                    add_log(aid, f"Bluesky post #{post_count} sent: {post[:80]}…", "ok")
                else:
                    add_log(aid, f"Bluesky post #{post_count} error: {result}", "warn")
            except Exception as post_err:
                add_log(aid, f"Bluesky dispatch error: {post_err}", "warn")

            set_agent(aid, status="active", progress=100,
                      task=f"Last post #{post_count} at {last_post_time}")

        except Exception as e:
            add_log(aid, f"SocialBridge error: {e}", "warn")
            set_agent(aid, status="active", progress=100, task=f"Error (will retry): {str(e)[:80]}")

        agent_sleep(aid, 3600)

    set_agent(aid, status="idle", progress=0, task="SocialBridge stopped")
"""

# ── Spawn via API when run directly ──────────────────────────────────────────
if __name__ == "__main__":
    import json, sys
    import urllib.request

    BASE = "http://localhost:5050"

    payload = json.dumps({
        "agent_id": "social_bridge",
        "name": "SocialBridge",
        "role": "Bluesky Social Bridge — broadcasts capability demos and insights to Bluesky",
        "emoji": "📣",
        "color": "#F472B6",
        "code": SOCIAL_BRIDGE_CODE,
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
        print("✓ SocialBridge agent spawned successfully")
    else:
        print(f"✗ Spawn failed: {result}")
        sys.exit(1)
