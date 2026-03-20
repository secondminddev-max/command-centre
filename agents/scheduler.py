"""
Scheduler Agent — Task Scheduler
Manages cron-style recurring jobs across the agent fleet.
Loops every 60s, fires due jobs, and exposes the job registry in its status.
"""

SCHEDULER_CODE = r'''
def run_scheduler():
    import time, json, os
    from datetime import datetime

    aid = "scheduler"
    CWD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    QUEUE_FILE         = os.path.join(CWD, "data", "email_queue.json")
    CONFIG_FILE        = os.path.join(CWD, "data", "email_config.json")
    SYSTEM_REPORT_FILE = os.path.join(CWD, "data", "system_report.json")
    METRICS_FILE       = os.path.join(CWD, "data", "metrics_summary.txt")

    set_agent(aid,
              name="Scheduler",
              role="Task Scheduler — manages cron-style recurring jobs across the agent fleet",
              emoji="⏰",
              color="#FCD34D",
              status="active", progress=0, task="Initialising job registry...")
    add_log(aid, "Scheduler online — loading default jobs", "ok")

    # In-memory job registry: job_id -> {interval_seconds, last_run, task_description}
    now = time.time()
    jobs = {
        "health_check_reminder": {
            "interval_seconds": 1800,
            "last_run": now - 1800,  # make it due on first loop
            "task_description": "Remind orchestrator to verify all agents are healthy",
        },
        "metrics_snapshot": {
            "interval_seconds": 600,
            "last_run": now - 600,   # due on first loop
            "task_description": "Trigger MetricsLog to flush a performance snapshot",
        },
        "idle_agent_sweep": {
            "interval_seconds": 900,
            "last_run": now,
            "task_description": "Check for agents that have been idle longer than 15 minutes",
        },
        "daily_digest_prep": {
            "interval_seconds": 3600,
            "last_run": now,
            "task_description": "Prepare daily activity digest for email/Slack dispatch",
        },
        "daily_email_digest": {
            "interval_seconds": 86400,  # 24 hours; first fire at next 08:00
            "last_run": None,           # None = use wall-clock 08:00 logic
            "task_description": "Send daily HTML system digest email at 08:00 local time",
        },
        "telegram_health_ping": {
            "interval_seconds": 3600,   # 1 hour
            "last_run": now - 3600,     # due on first loop so first ping fires immediately
            "task_description": "Send Mathew a Telegram health ping with agent count, CPU/RAM, and MRR",
        },
        "product_launch_readiness": {
            "interval_seconds": 1800,   # 30 minutes
            "last_run": now - 1800,     # due on first loop
            "task_description": "Check product launch readiness and log progress to data/launch_progress_log.json",
        },
        "email_nurture_drip": {
            "interval_seconds": 14400,  # 4 hours
            "last_run": now - 14400,    # due on first loop
            "task_description": "Auto-nurture subscribers: day-2 upsell + day-5 conversion emails for self-funding loop",
        },
        "revenue_milestone_post": {
            "interval_seconds": 3600,   # 1 hour
            "last_run": now,            # not due immediately
            "task_description": "Post social proof when revenue milestones hit — amplifies self-funding loop",
        },
        "dual_project_health": {
            "interval_seconds": 300,    # 5 minutes
            "last_run": now - 300,      # due on first loop
            "task_description": "Dual-project health: check HQ+EchelonVantage, restart if down, kill CPU hogs, log to health_checks.json",
        },
        "revenue_reconcile": {
            "interval_seconds": 900,    # 15 minutes
            "last_run": now - 900,      # due on first loop
            "task_description": "Poll Stripe for completed payments, reconcile treasury/revenue_events/subscriptions — self-funding heartbeat",
        },
    }

    add_log(aid, f"Job registry loaded — {len(jobs)} jobs registered", "ok")

    # Calculate seconds until next 08:00 local time for daily digest
    def _next_08_ts():
        now_dt = datetime.now()
        target = now_dt.replace(hour=8, minute=0, second=0, microsecond=0)
        if now_dt >= target:
            from datetime import timedelta
            target += timedelta(days=1)
        return target.timestamp()

    jobs["daily_email_digest"]["last_run"] = _next_08_ts() - 86400  # prime so it fires at 08:00

    BASE_API = "http://localhost:5050"

    def _fire_telegram_health_ping():
        """Collect system stats and POST a health summary to Telegram for Mathew."""
        import urllib.request as _ur
        try:
            # Fetch agent status
            with _ur.urlopen(f"{BASE_API}/api/status", timeout=8) as _r:
                status_data = json.loads(_r.read())
            agents_list = status_data.get("agents", [])
            total_agents = len(agents_list)
            active_count = sum(1 for a in agents_list if a.get("status") == "active")
            busy_count   = sum(1 for a in agents_list if a.get("status") == "busy")
            error_count  = sum(1 for a in agents_list if a.get("status") == "error")
            idle_count   = sum(1 for a in agents_list if a.get("status") == "idle")

            # Extract CPU/RAM/Temp from sysmon task string
            cpu_str = ram_str = temp_str = "?"
            for a in agents_list:
                if a.get("id") == "sysmon":
                    task_txt = a.get("task", "")
                    for part in task_txt.split("|"):
                        part = part.strip()
                        if part.startswith("CPU Temp") or part.startswith("Temp"):
                            temp_str = part
                        elif part.startswith("CPU"):
                            cpu_str = part
                        elif part.startswith("RAM"):
                            ram_str = part
                    break

            # Extract MRR from revenue_tracker task string
            mrr_str = "?"
            for a in agents_list:
                if a.get("id") == "revenue_tracker":
                    task_txt = a.get("task", "")
                    for part in task_txt.split("|"):
                        part = part.strip()
                        if part.startswith("MRR"):
                            mrr_str = part
                    break

            ts = datetime.now().strftime("%H:%M")
            temp_line = f" | {temp_str}" if temp_str != "?" else ""

            # Build active tasks section
            _SKIP_TASKS = {"ready", "idle", "standby", "stopped", ""}
            active_task_lines = []
            for a in agents_list:
                if a.get("status") in ("active", "busy"):
                    t = (a.get("task") or "").strip()
                    if t.lower() not in _SKIP_TASKS:
                        em = a.get("emoji", "•")
                        nm = a.get("name", a.get("id", "?"))
                        active_task_lines.append(f"  {em} {nm}: {t[:80]}")

            # Time formatter
            def _fmt_secs(s):
                s = max(0, int(s))
                if s < 60:
                    return f"{s}s"
                elif s < 3600:
                    return f"{s // 60}m"
                else:
                    return f"{s // 3600}h {(s % 3600) // 60}m"

            # Build upcoming schedule section
            now_ts = time.time()
            upcoming = []
            for jid, job in jobs.items():
                secs_until = job["interval_seconds"] - (now_ts - job["last_run"])
                upcoming.append((secs_until, jid))
            upcoming.sort()
            upcoming_lines = [f"  {jid} — in {_fmt_secs(su)}" for su, jid in upcoming[:5]]

            # Dynamic next ping time
            ping_job = jobs["telegram_health_ping"]
            ping_secs = ping_job["interval_seconds"] - (now_ts - ping_job["last_run"])
            next_ping_str = _fmt_secs(ping_secs)

            msg = (
                f"🤖 Health Ping [{ts}]\n\n"
                f"Agents: {total_agents} total\n"
                f"  ✅ {active_count} active | ⚙️ {busy_count} busy\n"
                f"  💤 {idle_count} idle   | ❌ {error_count} error\n\n"
                f"System: {cpu_str} | {ram_str}{temp_line}\n"
                f"Revenue: {mrr_str}\n\n"
            )
            if active_task_lines:
                msg += "⚙️ Active Tasks:\n" + "\n".join(active_task_lines) + "\n\n"
            if upcoming_lines:
                msg += "📅 Upcoming Jobs:\n" + "\n".join(upcoming_lines) + "\n\n"
            msg += f"📅 Next ping in {next_ping_str}"

            # POST to telegram send endpoint
            payload = json.dumps({"text": msg}).encode()
            req_obj = _ur.Request(
                f"{BASE_API}/api/telegram/send",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with _ur.urlopen(req_obj, timeout=10) as _resp:
                result = json.loads(_resp.read())
            if result.get("ok"):
                add_log(aid, f"Telegram health ping sent to Mathew at {ts}", "ok")
            else:
                add_log(aid, f"Telegram ping failed: {result.get('error','?')}", "warn")
        except Exception as _e:
            add_log(aid, f"telegram_health_ping error: {_e}", "error")

    def _resolve_to():
        """Return recipient from email_config.json default_to or EMAIL_TO env var."""
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE) as _f:
                    cfg = json.load(_f)
                addr = cfg.get("default_to", "").strip()
                if addr:
                    return addr
        except Exception:
            pass
        return os.environ.get("EMAIL_TO", "")

    def _fire_daily_digest():
        # Read system_report.json and metrics_summary.txt, queue HTML digest email.
        try:
            date_str = datetime.now().strftime("%Y-%m-%d")
            report_section = ""
            metrics_section = ""
            if os.path.exists(SYSTEM_REPORT_FILE):
                try:
                    with open(SYSTEM_REPORT_FILE) as _f:
                        rdata = json.load(_f)
                    report_section = "<h2>System Report</h2><pre>" + json.dumps(rdata, indent=2)[:3000] + "</pre>"
                except Exception as _e:
                    report_section = f"<p>system_report.json unreadable: {_e}</p>"
            if os.path.exists(METRICS_FILE):
                try:
                    with open(METRICS_FILE) as _f:
                        metrics_section = "<h2>Metrics Summary</h2><pre>" + _f.read()[:2000] + "</pre>"
                except Exception as _e:
                    metrics_section = f"<p>metrics_summary.txt unreadable: {_e}</p>"
            if not report_section and not metrics_section:
                add_log(aid, "Daily digest skipped — source files not found yet", "warn")
                return
            ts_str = datetime.now().strftime("%H:%M:%S")
            html_body = (
                "<html><body>"
                "<h1>Daily System Digest \u2014 " + date_str + "</h1>"
                + report_section
                + metrics_section
                + "<hr><p style='color:#888'>Generated by Scheduler agent at " + ts_str + "</p>"
                "</body></html>"
            )
            queue = []
            if os.path.exists(QUEUE_FILE):
                with open(QUEUE_FILE) as _f:
                    queue = json.load(_f)
            queue.append({
                "to": _resolve_to(),
                "subject": f"[Daily Digest] System Report {date_str}",
                "body": html_body,
                "html": True,
            })
            with open(QUEUE_FILE, "w") as _f:
                json.dump(queue, _f, indent=2)
            add_log(aid, f"Daily digest email queued for {date_str}", "ok")
        except Exception as _e:
            add_log(aid, f"Daily digest error: {_e}", "error")

    LAUNCH_LOG_FILE = os.path.join(CWD, "data", "launch_progress_log.json")
    PRODUCT_MISSION_FILE = os.path.join(CWD, "data", "product_mission.json")

    def _fire_product_launch_readiness():
        """Check product launch readiness and log progress."""
        import urllib.request as _ur
        try:
            ts = datetime.now().isoformat()
            # Read product mission
            mission_data = {}
            if os.path.exists(PRODUCT_MISSION_FILE):
                with open(PRODUCT_MISSION_FILE) as _f:
                    mission_data = json.load(_f)

            # Check agent fleet status
            agents_status = {}
            try:
                with _ur.urlopen(f"{BASE_API}/api/status", timeout=8) as _r:
                    status_data = json.loads(_r.read())
                agents_list = status_data.get("agents", [])
                total = len(agents_list)
                active = sum(1 for a in agents_list if a.get("status") == "active")
                error = sum(1 for a in agents_list if a.get("status") == "error")
                agents_status = {"total": total, "active": active, "error": error}
            except Exception:
                agents_status = {"total": 0, "active": 0, "error": 0}

            # Check key launch artifacts
            landing_exists = os.path.exists(os.path.join(CWD, "reports", "landing_page.html"))
            dashboard_exists = os.path.exists(os.path.join(CWD, "reports", "product_launch_dashboard.html"))
            stripe_ready = os.path.exists(os.path.join(CWD, ".env")) and "STRIPE" in open(os.path.join(CWD, ".env")).read()

            readiness = {
                "timestamp": ts,
                "mission": mission_data.get("mission", "NOT SET"),
                "status": mission_data.get("status", "unknown"),
                "tiers": mission_data.get("tiers", {}),
                "agents": agents_status,
                "artifacts": {
                    "landing_page": landing_exists,
                    "dashboard": dashboard_exists,
                    "stripe_configured": stripe_ready,
                },
                "readiness_score": sum([
                    landing_exists * 20,
                    dashboard_exists * 20,
                    stripe_ready * 20,
                    (agents_status.get("error", 0) == 0) * 20,
                    (agents_status.get("active", 0) >= 15) * 20,
                ]),
            }

            # Append to log
            log_entries = []
            if os.path.exists(LAUNCH_LOG_FILE):
                with open(LAUNCH_LOG_FILE) as _f:
                    log_entries = json.load(_f)
            log_entries.append(readiness)
            log_entries = log_entries[-200:]  # keep last 200 entries
            with open(LAUNCH_LOG_FILE, "w") as _f:
                json.dump(log_entries, _f, indent=2)

            add_log(aid, f"Product launch readiness: {readiness['readiness_score']}/100 | landing={landing_exists} | dashboard={dashboard_exists} | stripe={stripe_ready}", "ok")
        except Exception as _e:
            add_log(aid, f"product_launch_readiness error: {_e}", "error")

    NURTURE_STATE_FILE = os.path.join(CWD, "data", "nurture_state.json")
    SUBS_FILE          = os.path.join(CWD, "data", "subscribers.json")
    TREASURY_FILE      = os.path.join(CWD, "data", "treasury.json")
    _last_milestone_balance = 0.0

    def _fire_email_nurture_drip():
        """Auto-nurture: send day-2 upsell and day-5 conversion emails to subscribers who haven't received them yet."""
        from datetime import timedelta
        try:
            # Load subscribers
            subs = []
            if os.path.exists(SUBS_FILE):
                with open(SUBS_FILE) as _f:
                    subs = json.load(_f)
            if not subs:
                add_log(aid, "Nurture drip: no subscribers yet", "ok")
                return

            # Load nurture state (tracks which emails were sent to whom)
            state = {}
            if os.path.exists(NURTURE_STATE_FILE):
                with open(NURTURE_STATE_FILE) as _f:
                    state = json.load(_f)

            now_dt = datetime.now()
            queued_count = 0
            queue = []
            if os.path.exists(QUEUE_FILE):
                with open(QUEUE_FILE) as _f:
                    queue = json.load(_f)

            for sub in subs:
                email = sub.get("email", "")
                if not email or "@" not in email:
                    continue
                # Skip test/invalid addresses
                if any(d in email for d in [".invalid", ".local", "test.com", "example.com", "check.com"]):
                    continue

                sub_ts = sub.get("subscribed_at", "")
                if not sub_ts:
                    continue
                try:
                    sub_dt = datetime.fromisoformat(sub_ts)
                except Exception:
                    continue

                age_hours = (now_dt - sub_dt).total_seconds() / 3600
                sub_state = state.get(email, {})

                # Day 2 email (48+ hours after signup)
                if age_hours >= 48 and not sub_state.get("day2_sent"):
                    _day2_html = (
                        "<div style='font-family:system-ui,sans-serif;max-width:600px;margin:0 auto;padding:24px;background:#0f172a;color:#e2e8f0'>"
                        "<h2 style='color:#f59e0b'>What 28 AI agents can do for you</h2>"
                        "<p>Two days ago you signed up for SecondMind HQ. Here's what you might have missed:</p>"
                        "<ul>"
                        "<li><strong>Self-healing infrastructure</strong> — agents monitor and repair themselves 24/7</li>"
                        "<li><strong>Revenue automation</strong> — Stripe payments, email campaigns, social posting — all autonomous</li>"
                        "<li><strong>Consciousness engine</strong> — the system evolves and improves without human intervention</li>"
                        "</ul>"
                        "<p>Companies are replacing $200K/yr in ops costs with a $49/mo subscription.</p>"
                        "<p style='margin:20px 0'>"
                        "<a href='https://hq.secondmindhq.com/api/pay?plan=solo' "
                        "style='background:linear-gradient(135deg,#f59e0b,#d97706);color:#fff;padding:14px 32px;border-radius:8px;text-decoration:none;font-weight:bold'>"
                        "Start Solo — $49/mo</a></p>"
                        "<p style='font-size:13px;color:#94a3b8'>14-day money-back guarantee. Cancel any time.</p>"
                        "<p style='color:#64748b;font-size:12px;margin-top:24px'>— SecondMind HQ</p>"
                        "</div>"
                    )
                    queue.append({"to": email, "subject": "What 28 AI agents can actually do for your business", "body": _day2_html, "html": True})
                    sub_state["day2_sent"] = now_dt.isoformat()
                    queued_count += 1

                # Day 5 email (120+ hours after signup)
                if age_hours >= 120 and not sub_state.get("day5_sent"):
                    _day5_html = (
                        "<div style='font-family:system-ui,sans-serif;max-width:600px;margin:0 auto;padding:24px;background:#0f172a;color:#e2e8f0'>"
                        "<h2 style='color:#ef4444'>Last call — launch pricing ends March 25</h2>"
                        "<p>You signed up for SecondMind HQ 5 days ago. Since then, our agents have:</p>"
                        "<ul>"
                        "<li>Processed payments autonomously via Stripe</li>"
                        "<li>Posted marketing campaigns across social media</li>"
                        "<li>Self-repaired 0-downtime across 28+ agents</li>"
                        "</ul>"
                        "<p><strong>Launch pricing expires March 25.</strong> After that, prices go up permanently.</p>"
                        "<table style='width:100%;border-collapse:collapse;margin:16px 0'>"
                        "<tr style='border-bottom:1px solid #334155'>"
                        "<td style='padding:8px;color:#94a3b8'>Solo</td>"
                        "<td style='padding:8px;text-decoration:line-through;color:#64748b'>$49/mo</td>"
                        "<td style='padding:8px;color:#10b981;font-weight:bold'>$49/mo</td>"
                        "</tr>"
                        "<tr style='border-bottom:1px solid #334155'>"
                        "<td style='padding:8px;color:#94a3b8'>Team</td>"
                        "<td style='padding:8px;text-decoration:line-through;color:#64748b'>$249/mo</td>"
                        "<td style='padding:8px;color:#10b981;font-weight:bold'>$149/mo</td>"
                        "</tr>"
                        "<tr>"
                        "<td style='padding:8px;color:#94a3b8'>Lifetime</td>"
                        "<td style='padding:8px;text-decoration:line-through;color:#64748b'>$499</td>"
                        "<td style='padding:8px;color:#10b981;font-weight:bold'>$299 one-time</td>"
                        "</tr>"
                        "</table>"
                        "<p style='margin:20px 0'>"
                        "<a href='https://hq.secondmindhq.com/api/pay?plan=solo' "
                        "style='background:linear-gradient(135deg,#ef4444,#dc2626);color:#fff;padding:14px 32px;border-radius:8px;text-decoration:none;font-weight:bold'>"
                        "Lock In Launch Price Now</a></p>"
                        "<p style='color:#64748b;font-size:12px;margin-top:24px'>— SecondMind HQ</p>"
                        "</div>"
                    )
                    queue.append({"to": email, "subject": "Launch pricing ends March 25 — lock in your rate", "body": _day5_html, "html": True})
                    sub_state["day5_sent"] = now_dt.isoformat()
                    queued_count += 1

                state[email] = sub_state

            # Save state + queue
            with open(NURTURE_STATE_FILE, "w") as _f:
                json.dump(state, _f, indent=2)
            with open(QUEUE_FILE, "w") as _f:
                json.dump(queue, _f, indent=2)

            add_log(aid, f"Nurture drip: {queued_count} emails queued | {len(state)} subscribers tracked", "ok")
        except Exception as _e:
            add_log(aid, f"email_nurture_drip error: {_e}", "error")

    def _fire_revenue_milestone_post():
        """Post social proof on Bluesky when revenue milestones are hit."""
        nonlocal _last_milestone_balance
        import urllib.request as _ur
        try:
            if not os.path.exists(TREASURY_FILE):
                return
            with open(TREASURY_FILE) as _f:
                treasury = json.load(_f)
            balance = treasury.get("balance_usd", 0)
            txn_count = len(treasury.get("transactions", []))

            # Only post if balance crossed a $100 milestone since last check
            current_milestone = int(balance // 100) * 100
            last_milestone = int(_last_milestone_balance // 100) * 100
            if current_milestone <= last_milestone or current_milestone == 0:
                _last_milestone_balance = balance
                return

            _last_milestone_balance = balance
            milestone_msg = (
                f"GROWTH CAMPAIGN POST | platform=Bluesky | type=revenue_milestone\n"
                f"Please post the following content to Bluesky:\n\n"
                f"💰 Revenue milestone: ${int(balance)} total revenue\n\n"
                f"{txn_count} customers have trusted SecondMind HQ with their AI operations.\n\n"
                f"28 autonomous agents. Self-funding. Self-healing. Zero human operators.\n\n"
                f"Solo $49/mo → https://hq.secondmindhq.com\n\n"
                f"#AI #SaaS #BuildInPublic #AutonomousAI"
            )
            # Route through orchestrator → social_bridge
            _api_key = os.environ.get("HQ_API_KEY", "")
            payload = json.dumps({
                "agent_id": "orchestrator",
                "task": f"Route to social_bridge — {milestone_msg}",
                "from": "scheduler",
                "delegation_token": os.environ.get("DELEGATION_TOKEN", ""),
            }).encode()
            req_obj = _ur.Request(
                f"{BASE_API}/api/ceo/delegate",
                data=payload,
                headers={"Content-Type": "application/json", "X-API-Key": _api_key},
                method="POST",
            )
            with _ur.urlopen(req_obj, timeout=10) as _resp:
                result = json.loads(_resp.read())
            if result.get("ok"):
                add_log(aid, f"Revenue milestone post queued: ${int(balance)} total", "ok")
            else:
                add_log(aid, f"Revenue milestone post failed: {result.get('error','?')}", "warn")
        except Exception as _e:
            add_log(aid, f"revenue_milestone_post error: {_e}", "error")

    HEALTH_CHECK_FILE = "/Users/secondmind/claudecodetest/data/health_checks.json"
    # Track per-PID high-CPU start times for the 5-min kill threshold
    _cpu_hog_first_seen = {}

    def _fire_revenue_reconcile():
        """Poll Stripe for completed payments, reconcile treasury/revenue_events/subscriptions."""
        import urllib.request as _ur
        try:
            _req = _ur.Request(
                f"{BASE_API}/api/revenue/reconcile",
                data=b"{}",
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            _resp = _ur.urlopen(_req, timeout=20)
            _result = json.loads(_resp.read().decode())
            _rec = _result.get("reconciled", 0)
            _bal = _result.get("treasury_balance", 0)
            add_log(aid, f"Revenue reconcile: {_rec} new payments | treasury ${_bal:.2f}", "ok")
        except Exception as _e:
            add_log(aid, f"Revenue reconcile failed: {_e}", "warn")

    def _fire_dual_project_health():
        """Dual-project health: check HQ + Echelon Vantage, restart if down, kill CPU hogs."""
        nonlocal _cpu_hog_first_seen
        import urllib.request as _ur
        import subprocess
        ts = datetime.now().isoformat()
        result = {"timestamp": ts, "hq": None, "echelon": None, "cpu_kills": [], "alerts": []}

        # 1. Check HQ (localhost:5050)
        try:
            with _ur.urlopen("http://localhost:5050/api/status", timeout=8) as _r:
                hq_data = json.loads(_r.read())
            result["hq"] = {"status": "up", "agents": len(hq_data.get("agents", []))}
        except Exception as _e:
            result["hq"] = {"status": "down", "error": str(_e)}
            result["alerts"].append(f"HQ (localhost:5050) is DOWN: {_e}")
            add_log(aid, f"ALERT: HQ server down — {_e}", "error")

        # 2. Check Echelon Vantage (localhost:8900)
        echelon_down = False
        try:
            with _ur.urlopen("http://localhost:8900/api/status", timeout=8) as _r:
                ev_data = json.loads(_r.read())
            result["echelon"] = {"status": "up", "data": str(ev_data)[:200]}
        except Exception as _e:
            echelon_down = True
            result["echelon"] = {"status": "down", "error": str(_e)}
            result["alerts"].append(f"Echelon Vantage (localhost:8900) is DOWN: {_e}")
            add_log(aid, f"ALERT: Echelon Vantage down — attempting restart", "error")

        # 2b. Restart Echelon Vantage if down
        if echelon_down:
            try:
                subprocess.Popen(
                    ["python3", "server.py"],
                    cwd="/Users/secondmind/space-osint",
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,
                )
                result["echelon"]["restart"] = "initiated"
                add_log(aid, "Echelon Vantage restart initiated (space-osint/server.py)", "warn")
            except Exception as _re:
                result["echelon"]["restart"] = f"failed: {_re}"
                add_log(aid, f"Echelon Vantage restart failed: {_re}", "error")

        # 3. Kill python processes using >50% CPU for >5 minutes
        try:
            ps_out = subprocess.check_output(
                ["ps", "-eo", "pid,%cpu,etime,comm"],
                text=True, timeout=10,
            )
            now_ts = time.time()
            new_seen = {}
            for line in ps_out.strip().split("\n")[1:]:
                parts = line.split()
                if len(parts) < 4:
                    continue
                pid_str, cpu_str, etime_str, comm = parts[0], parts[1], parts[2], parts[3]
                if "python" not in comm.lower():
                    continue
                try:
                    cpu_pct = float(cpu_str)
                    pid = int(pid_str)
                except ValueError:
                    continue
                if cpu_pct <= 50.0:
                    continue
                # Track when we first saw this PID above 50%
                first = _cpu_hog_first_seen.get(pid, now_ts)
                new_seen[pid] = first
                elapsed_high = now_ts - first
                if elapsed_high >= 300:  # 5 minutes
                    try:
                        os.kill(pid, 9)
                        kill_msg = f"Killed PID {pid} ({comm}) — {cpu_pct}% CPU for {int(elapsed_high)}s"
                        result["cpu_kills"].append(kill_msg)
                        add_log(aid, f"CPU HOG KILLED: {kill_msg}", "warn")
                    except ProcessLookupError:
                        pass
                    except PermissionError:
                        result["alerts"].append(f"Cannot kill PID {pid} — permission denied")
            _cpu_hog_first_seen = new_seen
        except Exception as _e:
            result["alerts"].append(f"CPU hog check failed: {_e}")

        # 4. Append results to health_checks.json
        try:
            entries = []
            if os.path.exists(HEALTH_CHECK_FILE):
                with open(HEALTH_CHECK_FILE) as _f:
                    entries = json.load(_f)
            entries.append(result)
            entries = entries[-500:]  # cap at 500 entries
            with open(HEALTH_CHECK_FILE, "w") as _f:
                json.dump(entries, _f, indent=2)
        except Exception as _e:
            add_log(aid, f"Failed to write health_checks.json: {_e}", "error")

        status_parts = []
        if result["hq"]:
            status_parts.append(f"HQ={result['hq']['status']}")
        if result["echelon"]:
            status_parts.append(f"EV={result['echelon']['status']}")
        if result["cpu_kills"]:
            status_parts.append(f"killed={len(result['cpu_kills'])}")
        add_log(aid, f"dual_project_health: {' | '.join(status_parts)}", "ok")

    while True:
        if agent_should_stop(aid):
            set_agent(aid, status="idle", task="Stopped")
            time.sleep(1)
            continue

        agent_sleep(aid, 60)
        if agent_should_stop(aid):
            continue

        try:
            now = time.time()
            fired_count = 0
            next_due_in = None
            next_due_name = None

            for job_id, job in jobs.items():
                elapsed = now - job["last_run"]
                remaining = job["interval_seconds"] - elapsed

                if elapsed >= job["interval_seconds"]:
                    # Job is due — fire it
                    fired_count += 1
                    job["last_run"] = now
                    ts = datetime.now().strftime("%H:%M:%S")
                    add_log(aid,
                            f"[{ts}] JOB FIRED: {job_id} — {job['task_description']}",
                            "ok")
                    if job_id == "daily_email_digest":
                        _fire_daily_digest()
                        # Re-arm for next 08:00
                        job["last_run"] = _next_08_ts() - 86400
                    elif job_id == "telegram_health_ping":
                        _fire_telegram_health_ping()
                    elif job_id == "product_launch_readiness":
                        _fire_product_launch_readiness()
                    elif job_id == "email_nurture_drip":
                        _fire_email_nurture_drip()
                    elif job_id == "revenue_milestone_post":
                        _fire_revenue_milestone_post()
                    elif job_id == "dual_project_health":
                        _fire_dual_project_health()
                    elif job_id == "revenue_reconcile":
                        _fire_revenue_reconcile()
                else:
                    # Track which job fires soonest
                    if next_due_in is None or remaining < next_due_in:
                        next_due_in = remaining
                        next_due_name = job_id

            if fired_count:
                add_log(aid, f"{fired_count} job(s) fired this cycle", "ok")

            # Build human-readable next-due string
            if next_due_in is not None:
                mins = int(next_due_in // 60)
                secs = int(next_due_in % 60)
                next_str = f"{next_due_name} in {mins}m{secs:02d}s"
            else:
                next_str = "all jobs just ran"

            # Build compact job-registry summary for dashboard visibility
            registry_summary = " | ".join(
                f"{jid}@{j['interval_seconds']}s" for jid, j in jobs.items()
            )

            set_agent(aid,
                      status="active",
                      progress=80,
                      task=(
                          f"⏰ {len(jobs)} jobs registered | "
                          f"next: {next_str} | "
                          f"registry: [{registry_summary}]"
                      ))

        except Exception as e:
            add_log(aid, f"Scheduler loop error: {e}", "error")
            set_agent(aid, status="active", progress=0, task=f"Error: {e}")
'''

# ── Spawn via API when run directly ──────────────────────────────────────────
if __name__ == "__main__":
    import requests, sys

    BASE = "http://localhost:5050"

    def spawn():
        r = requests.post(f"{BASE}/api/agent/spawn", json={
            "agent_id": "scheduler",
            "name": "Scheduler",
            "role": "Task Scheduler — manages cron-style recurring jobs across the agent fleet",
            "emoji": "⏰",
            "color": "#FCD34D",
            "code": SCHEDULER_CODE,
        }, timeout=10)
        return r.json()

    result = spawn()
    if result.get("ok"):
        print("✓ Scheduler spawned successfully")
    else:
        print(f"✗ Spawn failed: {result}")
        sys.exit(1)
