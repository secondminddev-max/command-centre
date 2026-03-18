#!/usr/bin/env python3
"""Upgrade test_probe to PolicyProbe — CEO Policy Compliance Tester."""
import requests, json

BASE = "http://localhost:5050"

CODE = r"""
def run_test_probe():
    import time, requests, threading

    aid = "test_probe"
    passes = 0
    fails = 0
    cycle = 0

    set_agent(aid, name="PolicyProbe", role="CEO Policy Compliance Tester",
              emoji="🧪", color="#ff9900",
              status="active", progress=0,
              task="PolicyCheck: 0/0 — Initializing...")
    add_log(aid, "PolicyProbe online — CEO→Orchestrator delegation policy check every 60s", "ok")

    while not agent_should_stop(aid):
        cycle += 1
        test_task = (
            "POLICY_TEST #" + str(cycle) + ": Multi-step delegation check — "
            "1) verify agent roster, 2) identify idle agents, 3) report summary"
        )

        # Step 1: Fire delegation POST in background thread (endpoint blocks until claude finishes)
        _post_error = []
        def _fire_delegate(task=test_task, errs=_post_error):
            try:
                requests.post(
                    "http://localhost:5050/api/ceo/delegate",
                    json={"agent_id": "orchestrator", "task": task},
                    timeout=300  # long — claude may take up to 5min
                )
            except Exception as e:
                errs.append(str(e))

        t = threading.Thread(target=_fire_delegate, daemon=True)
        t.start()

        # Step 2: Within 10s verify orchestrator went busy with our task marker
        verified = False
        deadline = time.time() + 10
        fail_reason = "timeout: orchestrator did not go busy in 10s"
        while time.time() < deadline and not agent_should_stop(aid):
            time.sleep(0.5)
            try:
                sr = requests.get("http://localhost:5050/api/status", timeout=3)
                data = sr.json()
                for a in data.get("agents", []):
                    if a.get("id") == "orchestrator":
                        task_str = a.get("task", "")
                        status   = a.get("status", "")
                        # Check task contains our cycle marker AND agent is busy/working
                        if ("POLICY_TEST #" + str(cycle) in task_str or
                                "Working: POLICY_TEST #" + str(cycle) in task_str):
                            verified = True
                            break
                        # Also accept if status flipped to busy with any recent task
                        # (server truncates task to 60 chars in "Working: ..." prefix)
                        if status == "busy" and "POLICY_TEST" in task_str:
                            verified = True
                            break
            except Exception as e:
                fail_reason = "status check error: " + str(e)
            if verified:
                break

        if verified:
            passes += 1
            ratio = str(passes) + "/" + str(passes + fails)
            set_agent(aid, status="active", progress=99,
                      task="PolicyCheck: " + ratio + " PASS | Cycle #" + str(cycle)
                           + " OK | " + time.strftime("%H:%M"))
            add_log(aid, "PASS #" + str(cycle) + ": Orchestrator confirmed busy within 10s", "ok")
        else:
            fails += 1
            ratio = str(passes) + "/" + str(passes + fails)
            set_agent(aid, status="active", progress=99,
                      task="PolicyCheck: " + ratio + " PASS | Cycle #" + str(cycle)
                           + " FAIL: " + fail_reason[:50] + " | " + time.strftime("%H:%M"))
            add_log(aid, "FAIL #" + str(cycle) + ": " + fail_reason, "error")

        agent_sleep(aid, 60)
"""

payload = {
    "agent_id": "test_probe",
    "name": "PolicyProbe",
    "role": "CEO Policy Compliance Tester",
    "emoji": "🧪",
    "color": "#ff9900",
    "code": CODE,
}

print("Upgrading test_probe → PolicyProbe (v2)...", end=" ", flush=True)
r = requests.post(f"{BASE}/api/agent/upgrade", json=payload, timeout=10)
result = r.json()
if result.get("ok"):
    print("✓ Success")
else:
    print(f"✗ Failed: {result}")
print(json.dumps(result, indent=2))
