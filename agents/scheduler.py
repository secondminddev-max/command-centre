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
    CWD = "/Users/secondmind/claudecodetest"
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
