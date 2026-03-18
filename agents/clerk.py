"""
Clerk Agent — CEO Clerk
Watches reports/ directory for new files and updates status.
Scans every 15 seconds. Logs newly discovered files with name and timestamp.
"""

CLERK_CODE = r"""
def run_clerk():
    import os, time
    from datetime import datetime

    aid = "clerk"
    PROJECT_ROOT = globals().get("CWD") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    REPORTS_DIR = os.path.join(PROJECT_ROOT, "reports")

    set_agent(aid,
              name="Clerk",
              role="CEO Clerk — collects and delivers reports and documents to the customer mailbox",
              emoji="📬",
              color="#f5c842",
              status="active", progress=0, task="Initialising — scanning reports/...")
    add_log(aid, "Clerk online — watching reports/ for new files", "ok")

    known_files = set()

    # Initial scan
    try:
        entries = os.listdir(REPORTS_DIR)
        for fname in entries:
            fpath = os.path.join(REPORTS_DIR, fname)
            if os.path.isfile(fpath):
                known_files.add(fname)
        add_log(aid, f"Initial scan: {len(known_files)} files on record", "ok")
    except Exception as e:
        add_log(aid, f"Initial scan error: {e}", "error")

    while True:
        if agent_should_stop(aid):
            set_agent(aid, status="idle", task="Stopped")
            time.sleep(1)
            continue

        agent_sleep(aid, 15)
        if agent_should_stop(aid):
            continue

        try:
            current_files = set()
            try:
                entries = os.listdir(REPORTS_DIR)
                for fname in entries:
                    fpath = os.path.join(REPORTS_DIR, fname)
                    if os.path.isfile(fpath):
                        current_files.add(fname)
            except Exception as e:
                add_log(aid, f"Scan error: {e}", "error")
                continue

            new_files = current_files - known_files
            for fname in sorted(new_files):
                ts_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                add_log(aid, f"New report received: {fname} at {ts_str}", "ok")
                known_files.add(fname)

            count = len(known_files)
            if count > 0:
                set_agent(aid, status="active", progress=70,
                          task=f"📬 Watching reports/ — {count} files on record")
            else:
                set_agent(aid, status="idle", progress=0,
                          task="📬 Watching reports/ — 0 files on record")

        except Exception as e:
            add_log(aid, f"Clerk loop error: {e}", "error")
            set_agent(aid, status="active", progress=0, task=f"Error: {e}")
"""

# ── Spawn via API when run directly ──────────────────────────────────────────
if __name__ == "__main__":
    import requests, sys

    BASE = "http://localhost:5050"

    def spawn():
        r = requests.post(f"{BASE}/api/agent/spawn", json={
            "agent_id": "clerk",
            "name": "Clerk",
            "role": "CEO Clerk — collects and delivers reports and documents to the customer mailbox. Watches reports/ for new files and updates the mailbox widget.",
            "emoji": "📬",
            "color": "#f5c842",
            "code": CLERK_CODE,
        }, timeout=10)
        return r.json()

    result = spawn()
    if result.get("ok"):
        print("✓ Clerk spawned successfully")
    else:
        print(f"✗ Spawn failed: {result}")
        sys.exit(1)
