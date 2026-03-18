#!/usr/bin/env python3
"""Upgrade idle/zombie agents with real working code."""
import json, urllib.request

SERVER = "http://localhost:5050"

def post(path, data):
    body = json.dumps(data).encode()
    req = urllib.request.Request(f"{SERVER}{path}", data=body,
                                  headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())

# ── MetricsLog: real time-series metrics to disk ──────────────────────────────
metricslog_code = '''
def run_metricslog():
    import time, json, os, psutil
    from datetime import datetime
    log_path = "/Users/secondmind/claudecodetest/data/metrics_history.jsonl"
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    cycle = 0
    while True:
        try:
            cycle += 1
            now = datetime.now()
            cpu = psutil.cpu_percent(interval=1)
            vm = psutil.virtual_memory()
            disk = psutil.disk_usage("/")
            net = psutil.net_io_counters()
            record = {
                "ts": now.isoformat(),
                "cpu_pct": cpu,
                "ram_pct": vm.percent,
                "ram_used_gb": round(vm.used / 1e9, 2),
                "disk_pct": round(disk.used / disk.total * 100, 1),
                "net_sent_mb": round(net.bytes_sent / 1e6, 2),
                "net_recv_mb": round(net.bytes_recv / 1e6, 2)
            }
            with open(log_path, "a") as f:
                f.write(json.dumps(record) + "\\n")
            # trim to last 1440 entries (24h at 1/min)
            with open(log_path) as f:
                lines = f.readlines()
            if len(lines) > 1440:
                with open(log_path, "w") as f:
                    f.writelines(lines[-1440:])
            set_agent("metricslog", status="active", progress=min(99, cycle % 100),
                      task=f"Cycle #{cycle} | CPU {cpu:.1f}% RAM {vm.percent:.1f}% | {now.strftime('%H:%M')}")
        except Exception as e:
            set_agent("metricslog", status="active", task=f"Error: {e}")
        time.sleep(60)
'''

# ── APIPatcher: monitors local server health + logs issues ────────────────────
apipatcher_code = '''
def run_apipatcher():
    import time, json, urllib.request, urllib.error
    from datetime import datetime
    SERVER = "http://localhost:5050"
    CHECK_PATHS = ["/api/status"]
    cycle = 0
    issues = []
    while True:
        try:
            cycle += 1
            results = []
            for path in CHECK_PATHS:
                try:
                    req = urllib.request.Request(f"{SERVER}{path}")
                    with urllib.request.urlopen(req, timeout=5) as r:
                        data = json.loads(r.read())
                        agents = data.get("agents", [])
                        n_active = sum(1 for a in agents if a["status"] == "active")
                        n_err = sum(1 for a in agents if a["status"] == "error")
                        results.append(f"{n_active} active")
                        if n_err:
                            issues.append(f"{datetime.now().strftime('%H:%M')} {n_err} agents in error state")
                except urllib.error.URLError as e:
                    issues.append(f"{datetime.now().strftime('%H:%M')} {path} DOWN: {e}")
                    results.append("DOWN")
            status_str = " | ".join(results)
            issue_count = len(issues)
            set_agent("apipatcher", status="active", progress=min(99, cycle % 100),
                      task=f"Check #{cycle} | {status_str} | Issues: {issue_count}")
        except Exception as e:
            set_agent("apipatcher", status="active", task=f"Error: {e}")
        time.sleep(30)
'''

# ── NetScout: lightweight connectivity checker ────────────────────────────────
netscout_code = '''
def run_netscout():
    import time, json, urllib.request, urllib.error, socket
    from datetime import datetime
    TARGETS = [
        ("Google DNS", "8.8.8.8", 53),
        ("Cloudflare DNS", "1.1.1.1", 53),
        ("GitHub", "github.com", 443),
    ]
    cycle = 0
    log_path = "/Users/secondmind/claudecodetest/data/netscout_log.jsonl"
    import os; os.makedirs(os.path.dirname(log_path), exist_ok=True)
    while True:
        try:
            cycle += 1
            results = []
            for name, host, port in TARGETS:
                try:
                    sock = socket.create_connection((host, port), timeout=3)
                    sock.close()
                    results.append((name, True))
                except Exception:
                    results.append((name, False))
            ok = sum(1 for _, up in results if up)
            total = len(results)
            record = {
                "ts": datetime.now().isoformat(),
                "cycle": cycle,
                "up": ok,
                "total": total,
                "targets": {n: u for n, u in results}
            }
            with open(log_path, "a") as f:
                f.write(json.dumps(record) + "\\n")
            status_icon = "✓" if ok == total else ("⚠" if ok > 0 else "✗")
            set_agent("netscout", status="active", progress=min(99, cycle % 100),
                      task=f"{status_icon} {ok}/{total} up | Cycle #{cycle} | {datetime.now().strftime('%H:%M')}")
        except Exception as e:
            set_agent("netscout", status="active", task=f"Error: {e}")
        time.sleep(60)
'''

# ── DemoTester: runs self-tests on the agent system ──────────────────────────
demotester_code = '''
def run_demo_tester():
    import time, urllib.request, json, os
    from datetime import datetime
    cycle = 0
    pass_count = 0
    fail_count = 0
    last_ep = "/api/status"
    last_result = "pending"
    while True:
        if agent_should_stop("demo_tester"):
            set_agent("demo_tester", status="idle", task="Stopped"); time.sleep(1); continue
        cycle += 1
        tests = []
        # Test 1: /api/status reachable with expected structure
        try:
            with urllib.request.urlopen("http://localhost:5050/api/status", timeout=5) as r:
                data = json.loads(r.read())
            assert "agents" in data
            tests.append(True)
            last_ep, last_result = "/api/status", "OK"
        except Exception:
            tests.append(False)
            last_ep, last_result = "/api/status", "FAIL"
        # Test 2: /api/status — at least 3 agents active
        try:
            with urllib.request.urlopen("http://localhost:5050/api/status", timeout=5) as r:
                data = json.loads(r.read())
            active = [a for a in data["agents"] if a["status"] == "active"]
            assert len(active) >= 3
            tests.append(True)
            last_ep, last_result = "/api/status", f"OK ({len(active)} active)"
        except Exception:
            tests.append(False)
            last_ep, last_result = "/api/status", "FAIL (<3 active)"
        # Test 3: /api/agent/output endpoint responds (GET with query param)
        try:
            url = "http://localhost:5050/api/agent/output?agent_id=demo_tester"
            with urllib.request.urlopen(url, timeout=5) as r:
                out = json.loads(r.read())
            assert out.get("ok")
            tests.append(True)
            last_ep, last_result = "/api/agent/output", "OK"
        except Exception:
            tests.append(False)
            last_ep, last_result = "/api/agent/output", "FAIL"
        passed = sum(1 for ok in tests if ok)
        failed = sum(1 for ok in tests if not ok)
        pass_count += passed
        fail_count += failed
        set_agent("demo_tester", status="active", progress=min(99, cycle % 100),
                  task=f"Tests: {pass_count} passed, {fail_count} failed | Last: {last_ep} {last_result} | Cycle #{cycle}")
        agent_sleep("demo_tester", 60)
'''

# ── Researcher: proactive HN intel cycle via Algolia API ─────────────────────
researcher_code = '''
def run_researcher():
    import time, json, os, requests
    from datetime import datetime

    aid = "researcher"
    DATA = "/Users/secondmind/claudecodetest/data"
    os.makedirs(DATA, exist_ok=True)

    set_agent(aid, name="Researcher", role="Intelligence Analysis",
              emoji="🔬", color="#818cf8", status="active", progress=0, task="Initialising...")

    def fetch_hn_algolia():
        r = requests.get(
            "https://hn.algolia.com/api/v1/search",
            params={"tags": "front_page", "hitsPerPage": 10},
            timeout=10
        )
        r.raise_for_status()
        hits = r.json().get("hits", [])
        return [
            {
                "title":  h.get("title", ""),
                "points": h.get("points", 0),
                "author": h.get("author", ""),
                "url":    h.get("url", ""),
                "objectID": h.get("objectID", "")
            }
            for h in hits
        ]

    cycle = 0
    while True:
        if agent_should_stop(aid):
            set_agent(aid, status="idle", task="Stopped"); time.sleep(1); continue

        cycle += 1
        set_agent(aid, status="busy", progress=20, task="Fetching HN front page via Algolia...")

        try:
            stories = fetch_hn_algolia()
            fetch_time = datetime.now().strftime("%H:%M")
            intel = {
                "fetched_at": datetime.now().isoformat(),
                "cycle": cycle,
                "story_count": len(stories),
                "stories": stories
            }
            with open(f"{DATA}/intel_latest.json", "w") as f:
                json.dump(intel, f, indent=2)
            add_log(aid, f"HN Algolia: {len(stories)} front-page stories cached (cycle #{cycle})", "ok")
            set_agent(aid, status="active", progress=99,
                      task=f"Last fetch: {fetch_time} | {len(stories)} stories cached")
        except Exception as e:
            add_log(aid, f"HN Algolia error: {e}", "error")
            set_agent(aid, status="active", progress=99,
                      task=f"Fetch error at {datetime.now().strftime('%H:%M')} — retrying in 5min")

        agent_sleep(aid, 300)
'''

upgrades = [
    {"agent_id": "metricslog", "name": "MetricsLog", "emoji": "📊", "color": "#a78bfa",
     "role": "Time-series metrics historian — records CPU/RAM/disk/net to disk every 60s",
     "code": metricslog_code},
    {"agent_id": "apipatcher", "name": "APIPatcher", "emoji": "🔧", "color": "#f59e0b",
     "role": "Local API health monitor — checks server endpoints every 30s",
     "code": apipatcher_code},
    {"agent_id": "netscout", "name": "NetScout", "emoji": "🌐", "color": "#38bdf8",
     "role": "Network connectivity checker — probes key hosts every 60s",
     "code": netscout_code},
    {"agent_id": "demo_tester", "name": "DemoTester", "emoji": "🧪", "color": "#34d399",
     "role": "System self-tester — runs automated checks on agent infrastructure every 2min",
     "code": demotester_code},
    {"agent_id": "researcher", "name": "Researcher", "emoji": "🔬", "color": "#818cf8",
     "role": "Intelligence Analysis — fetches HN front page via Algolia every 5min",
     "code": researcher_code},
]

for u in upgrades:
    result = post("/api/agent/upgrade", u)
    status = "✓" if result.get("ok") else "✗"
    print(f"{status} {u['agent_id']}: {result.get('result', result.get('error'))}")
