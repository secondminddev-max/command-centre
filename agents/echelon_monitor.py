"""
Spawn script for the 'echelon_monitor' agent.
Agent ID : echelon_monitor
Name     : EchelonMonitor
Role     : Echelon Vantage Health Monitor — checks local + remote status, auto-restarts, logs health
Emoji    : 🔭
Color    : #60A5FA
"""

ECHELON_MONITOR_CODE = r"""
def run_echelon_monitor():
    import time, json, os, subprocess
    from datetime import datetime, timezone

    aid = "echelon_monitor"
    CWD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    HEALTH_FILE = os.path.join(CWD, "data", "echelon_health.json")
    LOCAL_URL = "http://localhost:8900/api/status"
    REMOTE_URL = "https://echelonvantage.com"
    SPACE_OSINT_DIR = os.path.expanduser("~/space-osint")
    CHECK_INTERVAL = 300  # 5 minutes

    set_agent(aid,
              name="EchelonMonitor",
              role="Echelon Vantage Health Monitor — checks local + remote status, auto-restarts, logs health",
              emoji="\U0001f52d", color="#60A5FA",
              status="active", progress=0,
              task="Initialising Echelon Vantage health monitor\u2026")
    add_log(aid, "EchelonMonitor online — monitoring localhost:8900 + echelonvantage.com", "ok")

    os.makedirs(os.path.join(CWD, "data"), exist_ok=True)

    def _check_url(url, timeout=15):
        import urllib.request as _ur
        try:
            req = _ur.Request(url, method="GET")
            with _ur.urlopen(req, timeout=timeout) as resp:
                return resp.status == 200
        except Exception:
            return False

    def _restart_local():
        try:
            subprocess.Popen(
                ["python3", "server.py"],
                cwd=SPACE_OSINT_DIR,
                stdout=open("/tmp/space-osint.log", "a"),
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
            return True
        except Exception as e:
            add_log(aid, f"Restart failed: {e}", "error")
            return False

    def _load_health():
        if not os.path.exists(HEALTH_FILE):
            return []
        try:
            with open(HEALTH_FILE) as f:
                return json.load(f)
        except Exception:
            return []

    def _save_health(entries):
        tmp = HEALTH_FILE + ".tmp"
        try:
            with open(tmp, "w") as f:
                json.dump(entries, f, indent=2)
            os.replace(tmp, HEALTH_FILE)
        except Exception as e:
            add_log(aid, f"Failed to write echelon_health.json: {e}", "error")
            try:
                os.remove(tmp)
            except OSError:
                pass

    cycle = 0
    while not agent_should_stop(aid):
        cycle += 1
        try:
            ts = datetime.now(timezone.utc).isoformat()

            # 1. Check local server (localhost:8900)
            local_ok = _check_url(LOCAL_URL)
            local_status = "UP" if local_ok else "DOWN"

            # 2. Check remote (echelonvantage.com)
            remote_ok = _check_url(REMOTE_URL)
            remote_status = "UP" if remote_ok else "DOWN"

            action = "nominal"
            restarted = False

            # 3. Auto-restart local if down
            if not local_ok:
                add_log(aid, "localhost:8900 DOWN — attempting restart", "warn")
                restarted = _restart_local()
                if restarted:
                    action = "restarted_local"
                    add_log(aid, "Restart initiated — waiting 10s for server to come up", "warn")
                    time.sleep(10)
                    # Re-check after restart
                    local_ok = _check_url(LOCAL_URL)
                    local_status = "UP" if local_ok else "DOWN (post-restart)"
                    if local_ok:
                        add_log(aid, "localhost:8900 back UP after restart", "ok")
                    else:
                        add_log(aid, "localhost:8900 still DOWN after restart attempt", "error")
                else:
                    action = "restart_failed"

            # 4. Log to echelon_health.json
            entry = {
                "timestamp": ts,
                "local_status": local_status,
                "remote_status": remote_status,
                "restarted": restarted,
                "action": action,
                "cycle": cycle,
            }
            entries = _load_health()
            entries.append(entry)
            entries = entries[-500:]
            _save_health(entries)

            # Update dashboard status
            local_icon = "\u2705" if local_ok else "\u274c"
            remote_icon = "\u2705" if remote_ok else "\u274c"
            task_str = (
                f"Local {local_icon} | Remote {remote_icon} | "
                f"Last check {datetime.now().strftime('%H:%M:%S')} | Cycle #{cycle}"
            )
            set_agent(aid, status="active", progress=100 if (local_ok and remote_ok) else 50, task=task_str)

            if cycle % 5 == 1:
                add_log(aid, f"Health check: local={local_status} remote={remote_status} action={action}", "ok")

        except Exception as e:
            add_log(aid, f"Monitor loop error: {e}", "error")
            set_agent(aid, status="error", task=f"Error: {str(e)[:80]}")

        agent_sleep(aid, CHECK_INTERVAL)

    set_agent(aid, status="idle", task="Stopped")
"""

if __name__ == "__main__":
    import json, os, sys, urllib.request

    BASE = "http://localhost:5050"

    payload = json.dumps({
        "agent_id": "echelon_monitor",
        "name":     "EchelonMonitor",
        "role":     "Echelon Vantage Health Monitor \u2014 checks local + remote status, auto-restarts, logs health",
        "emoji":    "\U0001f52d",
        "color":    "#60A5FA",
        "code":     ECHELON_MONITOR_CODE,
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{BASE}/api/agent/spawn",
        data=payload,
        headers={"Content-Type": "application/json",
                 "X-API-Key": os.environ.get("HQ_API_KEY", "")},
        method="POST",
    )
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        result = json.loads(resp.read().decode())
    except Exception as e:
        print(f"HTTP error: {e}")
        sys.exit(1)

    if result.get("ok"):
        print("\u2713 echelon_monitor (EchelonMonitor) spawned successfully")
    else:
        print(f"\u2717 Spawn failed: {result}")
        sys.exit(1)
