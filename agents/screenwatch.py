"""
ScreenWatch — Quality Controller / HQ Assessor
Periodically reads the live HQ dashboard state, assesses overall health,
flags broken/erroring/stalled agents, and writes a structured report to
data/screenwatch_report.json. Posts a digest to the CEO delegate endpoint
every cycle. Runs on a 5-minute cycle.
"""

SCREENWATCH_CODE = r"""
def run_screenwatch():
    import time, json, os
    import urllib.request, urllib.error
    from datetime import datetime, timezone

    aid        = "screenwatch"
    BASE_API   = "http://localhost:5050"
    REPORT_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data/screenwatch_report.json"
    CYCLE_SECS  = 300   # 5-minute assessment cycle
    cycle_num   = 0

    set_agent(aid,
              name="ScreenWatch",
              role="Quality Controller / HQ Assessor — monitors agent health, flags errors, and reports to CEO",
              emoji="🖥️",
              color="#e11d48",
              status="active", progress=10, task="Initialising — first assessment pending...")
    add_log(aid, "🖥️ ScreenWatch online — HQ quality control active", "ok")

    # ── helpers ────────────────────────────────────────────────────────────────
    def api_get(path):
        req = urllib.request.Request(f"{BASE_API}{path}", method="GET")
        resp = urllib.request.urlopen(req, timeout=10)
        return json.loads(resp.read().decode())

    def api_post(path, payload):
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{BASE_API}{path}", data=data,
            headers={"Content-Type": "application/json"}, method="POST"
        )
        try:
            resp = urllib.request.urlopen(req, timeout=10)
            return json.loads(resp.read().decode())
        except Exception:
            return {"ok": False}

    def write_report(report):
        try:
            with open(REPORT_FILE, "w") as f:
                json.dump(report, f, indent=2)
        except Exception as e:
            add_log(aid, f"Failed to write report: {e}", "error")

    def assess_agents(agents):
        # Return (issues, suggestions, summary_counts) from agent list
        issues      = []
        suggestions = []
        counts      = {"total": 0, "active": 0, "busy": 0, "idle": 0, "error": 0, "unknown": 0}

        for a in agents:
            aid_a   = a.get("id", "?")
            name    = a.get("name", aid_a)
            status  = a.get("status", "unknown")
            task    = a.get("task", "")
            counts["total"] += 1
            if status in counts:
                counts[status] += 1
            else:
                counts["unknown"] += 1

            # Flag error status
            if status == "error":
                issues.append({
                    "agent": aid_a,
                    "severity": "critical",
                    "issue": f"{name} is in ERROR state",
                    "detail": task,
                    "action": f"Restart or redeploy {aid_a}"
                })

            # Flag agents that mention error in their task string
            if "error" in task.lower() and status != "error":
                issues.append({
                    "agent": aid_a,
                    "severity": "warning",
                    "issue": f"{name} task string contains error marker",
                    "detail": task[:120],
                    "action": f"Inspect logs for {aid_a}"
                })

            # Flag agents stuck at 0 progress that should be active
            if status == "active" and a.get("progress", 0) == 0:
                issues.append({
                    "agent": aid_a,
                    "severity": "warning",
                    "issue": f"{name} is active but reports 0% progress",
                    "detail": task[:120],
                    "action": f"Check if {aid_a} loop is stalled"
                })

            # Flag idle agents that are critical infrastructure
            CRITICAL_IDS = {"orchestrator", "sysmon", "apipatcher", "alertwatch", "policypro"}
            if status == "idle" and aid_a in CRITICAL_IDS:
                issues.append({
                    "agent": aid_a,
                    "severity": "critical",
                    "issue": f"Critical agent {name} is IDLE",
                    "detail": task[:120],
                    "action": f"Restart {aid_a} immediately"
                })

        # General health suggestions
        error_count = counts["error"]
        if error_count == 0:
            suggestions.append("All agents report non-error status — no immediate restarts needed.")
        else:
            suggestions.append(f"{error_count} agent(s) in ERROR — prioritise restart of erroring agents.")

        if counts["active"] + counts["busy"] < counts["total"] * 0.5:
            suggestions.append("Less than 50% of agents are active/busy — fleet may be under-utilised or degraded.")

        return issues, suggestions, counts

    def calculate_health_score(issues, counts):
        # Simple 0-100 health score
        score = 100
        for issue in issues:
            if issue["severity"] == "critical":
                score -= 20
            elif issue["severity"] == "warning":
                score -= 5
        # Penalise if total agents drop below expected floor
        if counts["total"] < 10:
            score -= 15
        return max(0, min(100, score))

    # ── main loop ──────────────────────────────────────────────────────────────
    while True:
        if agent_should_stop(aid):
            set_agent(aid, status="idle", task="Stopped")
            time.sleep(1)
            continue

        # Run assessment immediately on first cycle, then wait
        if cycle_num > 0:
            agent_sleep(aid, CYCLE_SECS)
            if agent_should_stop(aid):
                continue

        cycle_num += 1
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        set_agent(aid, status="busy", progress=20,
                  task=f"🔍 Assessing HQ health — cycle #{cycle_num}...")

        try:
            status_data = api_get("/api/status")
        except Exception as e:
            add_log(aid, f"Failed to fetch /api/status: {e}", "error")
            set_agent(aid, status="error", progress=0, task=f"Cannot reach /api/status: {e}")
            time.sleep(30)
            continue

        agents   = status_data.get("agents", [])
        metrics  = status_data.get("metrics", {})

        set_agent(aid, status="busy", progress=50,
                  task=f"🔍 Analysing {len(agents)} agents — cycle #{cycle_num}...")

        issues, suggestions, counts = assess_agents(agents)
        health_score = calculate_health_score(issues, counts)

        # Classify overall health
        if health_score >= 85:
            health_label = "HEALTHY"
        elif health_score >= 60:
            health_label = "DEGRADED"
        else:
            health_label = "CRITICAL"

        critical_issues  = [i for i in issues if i["severity"] == "critical"]
        warning_issues   = [i for i in issues if i["severity"] == "warning"]

        # Build structured report
        report = {
            "timestamp":      ts,
            "cycle":          cycle_num,
            "health_score":   health_score,
            "health_label":   health_label,
            "agent_counts":   counts,
            "system_metrics": metrics,
            "critical_issues": critical_issues,
            "warning_issues":  warning_issues,
            "suggestions":     suggestions,
            "raw_agent_count": len(agents),
        }

        write_report(report)

        # Build digest message for CEO
        crit_names  = ", ".join(i["agent"] for i in critical_issues) or "none"
        warn_names  = ", ".join(i["agent"] for i in warning_issues) or "none"
        digest = (
            f"[ScreenWatch Cycle #{cycle_num}] Health: {health_label} ({health_score}/100) | "
            f"Agents: {counts['total']} total, {counts['active']} active, {counts['busy']} busy, "
            f"{counts['error']} error | "
            f"Critical: {crit_names} | Warnings: {warn_names}"
        )

        # Fire notifications for critical health issues
        if health_label == "CRITICAL":
            api_post("/api/notify", {
                "event_type": "system_health_critical",
                "message": (
                    f"HQ health is CRITICAL — score {health_score}/100\n"
                    f"Agents: {counts['total']} total, {counts['error']} in error\n"
                    f"Critical issues: {', '.join(i['agent'] for i in critical_issues) or 'none'}\n"
                    f"Cycle #{cycle_num}"
                ),
                "severity": "critical",
                "agent": "screenwatch",
                "timestamp": ts,
            })
        elif health_label == "DEGRADED" and critical_issues:
            for _ci in critical_issues:
                api_post("/api/notify", {
                    "event_type": "agent_error",
                    "message": (
                        f"{_ci['issue']}\n"
                        f"Action: {_ci['action']}\n"
                        f"Detail: {_ci.get('detail', '')[:120]}\n"
                        f"Cycle #{cycle_num}"
                    ),
                    "severity": "critical",
                    "agent": _ci["agent"],
                    "timestamp": ts,
                })

        # Post to CEO delegate only when there are issues or every 3rd cycle
        if issues or cycle_num % 3 == 0:
            api_post("/api/ceo/delegate", {
                "agent_id": "ceo",
                "task": digest,
                "from": "screenwatch"
            })

        # Log notable findings
        for issue in critical_issues:
            add_log(aid, f"🚨 CRITICAL [{issue['agent']}]: {issue['issue']} → {issue['action']}", "error")
        for issue in warning_issues:
            add_log(aid, f"⚠️  WARNING [{issue['agent']}]: {issue['issue']}", "warn")
        if not issues:
            add_log(aid, f"✅ Cycle #{cycle_num}: All clear — health {health_score}/100", "ok")

        # Update agent status
        icon = "✅" if health_label == "HEALTHY" else ("⚠️" if health_label == "DEGRADED" else "🚨")
        set_agent(aid, status="active",
                  progress=health_score,
                  task=f"{icon} {health_label} {health_score}/100 | "
                       f"{counts['error']} errors | "
                       f"{len(critical_issues)} critical | "
                       f"{len(warning_issues)} warnings | Cycle #{cycle_num}")

"""

# ── Spawn via API when run directly ──────────────────────────────────────────
if __name__ == "__main__":
    import requests, sys

    BASE = "http://localhost:5050"

    def spawn():
        r = requests.post(f"{BASE}/api/agent/spawn", json={
            "agent_id": "screenwatch",
            "name":     "ScreenWatch",
            "role":     "Quality Controller / HQ Assessor — monitors agent roster health, flags errors and stalled agents, writes data/screenwatch_report.json and briefs the CEO every 5 minutes",
            "emoji":    "🖥️",
            "color":    "#e11d48",
            "code":     SCREENWATCH_CODE,
        }, timeout=10)
        return r.json()

    result = spawn()
    if result.get("ok"):
        print("✓ ScreenWatch spawned successfully")
    else:
        print(f"✗ Spawn failed: {result}")
        sys.exit(1)
