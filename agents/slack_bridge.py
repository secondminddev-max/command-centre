"""
SlackBridge Agent — Slack Comms Bridge
Forwards critical alerts and summaries to Slack via incoming webhook.
"""

SLACK_BRIDGE_CODE = r"""
def run_slack_bridge():
    import os, time, json
    import urllib.request, urllib.error
    from datetime import datetime

    aid = "slack_bridge"
    BASE_API = "http://localhost:5050"
    LOOP_INTERVAL = 60

    try:
        set_agent(aid,
                  name="SlackBridge",
                  role="Slack Comms Bridge — forwards critical alerts and summaries via incoming webhook",
                  emoji="💬",
                  color="#818CF8",
                  status="active", progress=10, task="Initialising...")
        add_log(aid, "SlackBridge starting up", "ok")
    except Exception as _e:
        add_log(aid, f"SlackBridge startup error: {_e}", "warn")
        set_agent(aid, status="active", progress=10, task=f"Startup error (recovered): {str(_e)[:80]}")

    last_alert_ids = set()   # track which alerts we've already sent
    sent_count = 0
    skipped_count = 0
    cycle = 0
    no_webhook_logged = False

    def slack_post(webhook_url, payload):
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            webhook_url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        urllib.request.urlopen(req, timeout=10)

    def fetch_status():
        req = urllib.request.Request(f"{BASE_API}/api/status", method="GET")
        resp = urllib.request.urlopen(req, timeout=8)
        return json.loads(resp.read().decode())

    def fetch_alerts():
        try:
            req = urllib.request.Request(f"{BASE_API}/api/alerts", method="GET")
            resp = urllib.request.urlopen(req, timeout=8)
            data = json.loads(resp.read().decode())
            alerts = data.get("alerts", data) if isinstance(data, dict) else data
            return alerts if isinstance(alerts, list) else []
        except Exception:
            return []

    def build_alert_blocks(alerts):
        lines = [f"🚨 *Critical Alert* — {datetime.now().strftime('%H:%M:%S')}"]
        for a in alerts:
            text = a if isinstance(a, str) else json.dumps(a)[:200]
            lines.append(f"• {text}")
        return {"text": "\n".join(lines)}

    def build_summary_blocks(status_data):
        agents = status_data.get("agents", [])
        total  = len(agents)
        active = sum(1 for a in agents if a.get("status") == "active")
        busy   = sum(1 for a in agents if a.get("status") == "busy")
        idle   = sum(1 for a in agents if a.get("status") == "idle")
        error  = sum(1 for a in agents if a.get("status") == "error")

        # Gather resource metrics from sysmon task string if available
        cpu_str = ram_str = ""
        for a in agents:
            if a.get("id") == "sysmon":
                task = a.get("task", "")
                # e.g. "HeatIndex: 37 WARM | CPU 26.9% | RAM 56.2% | Disk 3.7%"
                cpu_str = next((p.strip() for p in task.split("|") if "CPU" in p), "")
                ram_str = next((p.strip() for p in task.split("|") if "RAM" in p), "")
                break

        problem_agents = [
            f"• {a.get('emoji','')} *{a.get('name', a.get('id','?'))}* [{a.get('status')}] — {(a.get('task') or '')[:80]}"
            for a in agents if a.get("status") in ("error", "idle") and a.get("id") not in ("ceo",)
        ]

        summary_lines = [
            f"📊 *System Summary* — {datetime.now().strftime('%H:%M')}",
            f"Agents: {total} total — {active} active, {busy} busy, {idle} idle, {error} error",
        ]
        if cpu_str or ram_str:
            summary_lines.append(f"Resources: {cpu_str}  {ram_str}".strip())
        if problem_agents:
            summary_lines.append("Attention:")
            summary_lines.extend(problem_agents[:5])

        return {"text": "\n".join(summary_lines)}

    while not agent_should_stop(aid):
        cycle += 1
        webhook_url = os.environ.get("SLACK_WEBHOOK_URL", "").strip()

        if not webhook_url:
            skipped_count += 1
            if not no_webhook_logged:
                add_log(aid,
                        "No SLACK_WEBHOOK_URL configured. "
                        "Export SLACK_WEBHOOK_URL=https://hooks.slack.com/services/... to enable.",
                        "warn")
                no_webhook_logged = True
            set_agent(aid, status="active", progress=70,
                      task=f"No webhook configured, monitoring only | Sent:{sent_count} Skipped:{skipped_count}")
            agent_sleep(aid, LOOP_INTERVAL)
            continue

        try:
            # ── 1. Check for new alerts ──────────────────────────────────────
            alerts = fetch_alerts()
            new_alerts = []
            for a in alerts:
                alert_key = a if isinstance(a, str) else json.dumps(a, sort_keys=True)
                if alert_key not in last_alert_ids:
                    new_alerts.append(a)
                    last_alert_ids.add(alert_key)

            if new_alerts:
                payload = build_alert_blocks(new_alerts)
                slack_post(webhook_url, payload)
                sent_count += 1
                add_log(aid, f"Sent {len(new_alerts)} alert(s) to Slack", "ok")
                set_agent(aid, status="active", progress=90,
                          task=f"Sent {len(new_alerts)} alert(s) | Sent:{sent_count} | cycle #{cycle}")
            else:
                # ── 2. Every cycle send a concise status summary ─────────────
                status_data = fetch_status()
                # Flag if any agent is in error state
                error_agents = [a for a in status_data.get("agents", [])
                                if a.get("status") == "error"]
                if error_agents:
                    names = ", ".join(a.get("name", a.get("id", "?")) for a in error_agents)
                    payload = {"text": f"⚠️ *Agent Error Detected* — {names}\n"
                                       f"Check system dashboard for details."}
                    slack_post(webhook_url, payload)
                    add_log(aid, f"Sent error alert for: {names}", "warn")
                    set_agent(aid, status="active", progress=85,
                              task=f"Error alert sent: {names[:60]} | cycle #{cycle}")
                else:
                    # Periodic summary (every ~5 cycles = ~5 min)
                    if cycle % 5 == 0:
                        payload = build_summary_blocks(status_data)
                        slack_post(webhook_url, payload)
                        add_log(aid, f"Sent periodic summary to Slack (cycle #{cycle})", "ok")
                        set_agent(aid, status="active", progress=80,
                                  task=f"Summary sent | cycle #{cycle}")
                    else:
                        set_agent(aid, status="active", progress=70,
                                  task=f"Monitoring... no new alerts | Sent:{sent_count} Skipped:{skipped_count} | cycle #{cycle}")

        except Exception as e:
            add_log(aid, f"Slack post error: {e}", "warn")
            set_agent(aid, status="active", progress=40,
                      task=f"Post error: {str(e)[:80]} | cycle #{cycle}")

        agent_sleep(aid, LOOP_INTERVAL)

    set_agent(aid, status="idle", progress=0, task="SlackBridge stopped")
"""

# ── Spawn via API when run directly ──────────────────────────────────────────
if __name__ == "__main__":
    import json, sys
    import urllib.request

    BASE = "http://localhost:5050"

    payload = json.dumps({
        "agent_id": "slack_bridge",
        "name": "SlackBridge",
        "role": "Slack Comms Bridge — forwards critical alerts and summaries via incoming webhook",
        "emoji": "💬",
        "color": "#818CF8",
        "code": SLACK_BRIDGE_CODE,
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
        print("✓ SlackBridge agent spawned successfully")
    else:
        print(f"✗ Spawn failed: {result}")
        sys.exit(1)
