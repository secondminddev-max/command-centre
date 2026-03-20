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
        try:
            req = urllib.request.Request("http://localhost:5050/api/status")
            with urllib.request.urlopen(req, timeout=5) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.URLError as e:
            add_log(aid, f"Status fetch network error: {getattr(e, 'reason', e)}", "warn")
            return None
        except (json.JSONDecodeError, ValueError) as e:
            add_log(aid, f"Status fetch bad response: {e}", "warn")
            return None
        except Exception as e:
            add_log(aid, f"Status fetch error: {type(e).__name__}: {e}", "warn")
            return None

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

    ALLOWED_CALLERS = {"orchestrator", "ceo"}

    def validate_delegation_source(delegation):
        '''Reject delegated tasks from unauthorized callers. Only orchestrator (and ceo) may delegate to social_bridge.'''
        caller = delegation.get("from", "unknown") if isinstance(delegation, dict) else "unknown"
        if caller not in ALLOWED_CALLERS:
            add_log(aid, f"🚫 POLICY VIOLATION: rejected delegation from '{caller}' — only {ALLOWED_CALLERS} may delegate to social_bridge", "error")
            return False
        return True

    import urllib.error

    while not agent_should_stop(aid):
        try:
            set_agent(aid, status="active", progress=30, task="Fetching system status…")

            status = fetch_status()
            if status is None:
                add_log(aid, "Could not fetch status — skipping this cycle", "warn")
                set_agent(aid, status="active", progress=20, task="Status unavailable — waiting…")
                agent_sleep(aid, 3600)
                continue
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
                        "US Stock Market Intelligence Report — $29 one-time.\n"
                        "S&P 500 momentum picks, sector strength analysis, "
                        "20 watchlist candidates, risk dashboard.\n"
                        "secondmindhq.com/api/pay?product=us_market_intel_v1 #stocks #trading"
                    ),
                    (
                        "Bloomberg Terminal: $2,000/mo. Our US Market Intel Report: $29.\n"
                        "Momentum picks. Sector heat map. 20 watchlist candidates. Risk dashboard.\n"
                        "AI-generated. Data-driven.\n"
                        "secondmindhq.com/api/pay?product=us_market_intel_v1 #investing"
                    ),
                    (
                        "One good trade pays for this 10x over.\n"
                        "US Stock Market Intelligence Report — $29:\n"
                        "S&P 500 momentum, sector rankings, 20 picks, risk levels.\n"
                        "secondmindhq.com/api/pay?product=us_market_intel_v1 #stocks #fintwit"
                    ),
                    (
                        f"{total} AI agents scan US markets around the clock.\n"
                        "The output: a $29 intelligence report — momentum picks, "
                        "sector rotation, watchlist candidates.\n"
                        "No subscription. Buy once.\n"
                        "secondmindhq.com/api/pay?product=us_market_intel_v1 #AI #trading"
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
                    err_detail = result.get("error", result.get("message", str(result)))
                    add_log(aid, f"Bluesky post #{post_count} rejected: {err_detail}", "warn")
            except urllib.error.HTTPError as post_err:
                add_log(aid, f"Bluesky HTTP {post_err.code}: {post_err.read().decode()[:120]}", "error")
            except urllib.error.URLError as post_err:
                add_log(aid, f"Bluesky network error: {post_err.reason} — post held for next cycle", "error")
            except Exception as post_err:
                add_log(aid, f"Bluesky dispatch error: {type(post_err).__name__}: {post_err}", "error")

            set_agent(aid, status="active", progress=100,
                      task=f"Last post #{post_count} at {last_post_time}")

        except Exception as e:
            add_log(aid, f"SocialBridge cycle error: {type(e).__name__}: {e}", "error")
            set_agent(aid, status="active", progress=100, task=f"Error (will retry): {type(e).__name__}: {str(e)[:60]}")

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
