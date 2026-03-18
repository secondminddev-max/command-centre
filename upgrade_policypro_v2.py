#!/usr/bin/env python3
"""One-shot script to upgrade policypro agent to v2."""
import requests, json

CODE = r'''
import time, json, os, requests
from datetime import datetime

def run():
    aid = "policypro"
    set_agent(aid, name="PolicyPro", role="Sentinel — Chain & Policy Enforcer",
              emoji="🔭", color="#ffd700", status="active", progress=100,
              task="Sentinel v2 online — policy-aware violation tracking")
    add_log(aid, "PolicyPro Sentinel v2 online — reads /api/status every 30s, posts to /api/policy/violations")

    check_num = 0
    last_escalation_ts = 0
    error_state_counts = {}
    spinner = ["◐ ", "◓ ", "◑ ", "◒ "]

    def load_rules():
        try:
            with open(os.path.join(CWD, "data", "policy_rules.json")) as f:
                return json.load(f)
        except Exception:
            return []

    def post_violation(vtype, description, severity="medium"):
        entry = {
            "timestamp": datetime.now().isoformat(),
            "type": vtype,
            "description": description,
            "severity": severity,
        }
        try:
            requests.post(
                "http://localhost:5050/api/policy/violations",
                json=entry,
                timeout=5,
            )
        except Exception as exc:
            add_log(aid, f"Failed to post violation: {exc}", "error")

    while True:
        if agent_should_stop(aid):
            set_agent(aid, status="idle", task="Sentinel offline")
            agent_sleep(aid, 2)
            continue

        if not _policypro_enabled:
            set_agent(aid, status="idle", task="🔕 Sentinel PAUSED — toggle to resume")
            agent_sleep(aid, 3)
            continue

        try:
            check_num += 1
            sl = spinner[check_num % len(spinner)]
            ts_now = time.strftime("%H:%M:%S")

            # Fetch live system status
            try:
                resp = requests.get("http://localhost:5050/api/status", timeout=5)
                status_data = resp.json()
            except Exception as e:
                add_log(aid, f"Status fetch failed: {e}", "error")
                agent_sleep(aid, 30)
                continue

            agents_list = status_data.get("agents", [])
            tasks_list  = status_data.get("tasks", [])
            active_delegations = status_data.get("active_delegations", [])
            system_paused = status_data.get("system_paused", False)

            rules = load_rules()
            violations = []

            # 1. CEO delegating directly to a specialist (bypass)
            _orc_allowed = {"orchestrator", "ceo", "reforger", "designer"}
            for deleg in active_delegations:
                dfrom = (deleg.get("from") or "").lower()
                dto   = (deleg.get("to") or "").lower()
                if dfrom == "ceo" and dto and dto not in _orc_allowed:
                    desc = f"CEO delegated directly to {dto} (bypassing orchestrator)"
                    violations.append({"type": "direct-ceo-delegation", "description": desc, "severity": "high"})

            # 2. Orchestrator still running after stop-all
            if system_paused:
                orc = next((a for a in agents_list if a.get("id") == "orchestrator"), {})
                if orc.get("status") in ("active", "busy"):
                    desc = "Orchestrator still active after stop-all triggered"
                    violations.append({"type": "orchestrator-running-after-stop", "description": desc, "severity": "high"})

            # 3. Any agent in ERROR state for more than 2 cycles
            for a in agents_list:
                a_id = a.get("id", "")
                if a.get("status") == "error":
                    error_state_counts[a_id] = error_state_counts.get(a_id, 0) + 1
                    if error_state_counts[a_id] >= 2:
                        desc = f"Agent {a_id} ({a.get('name','?')}) in ERROR state for {error_state_counts[a_id]} consecutive cycles"
                        violations.append({"type": "agent-persistent-error", "description": desc, "severity": "medium"})
                else:
                    error_state_counts[a_id] = 0

            # 4. On-demand agent self-activation
            for on_demand_aid in ("researcher", "netscout", "janitor"):
                a = next((x for x in agents_list if x.get("id") == on_demand_aid), {})
                task_str = a.get("task", "")
                if a.get("status") == "active" and not any(
                    kw in task_str for kw in ("Standby", "Stopped", "Idle", "awaiting")
                ):
                    desc = f"{on_demand_aid} self-activated without directive (on-demand only)"
                    violations.append({"type": "on-demand-self-activation", "description": desc, "severity": "low"})

            # Post new violations to the API
            for v in violations:
                post_violation(v["type"], v["description"], v["severity"])

            # Build display message
            active_count = sum(1 for a in agents_list if a.get("status") in ("active", "busy"))
            total_count  = len(agents_list)
            clean = not violations
            status_icon = "🟢 CLEAN" if clean else f"🔴 ALERT({len(violations)})"
            vio_str = "" if clean else f" | ⚠ {violations[0]['description'][:50]}"
            msg = f"{sl}Scanning | {status_icon} | {active_count}/{total_count} up | {len(violations)} violation(s) | {ts_now}"
            set_agent(aid, status="active", progress=100, task=msg)

            if check_num % 4 == 1:
                level = "ok" if clean else "warn"
                add_log(aid, f"Sentinel #{check_num}: {status_icon} | {len(violations)} violation(s){vio_str}", level)

            # Escalate to orchestrator (rate-limited to 120s)
            if violations and time.time() - last_escalation_ts > 120:
                last_escalation_ts = time.time()
                vio_summary = "; ".join(v["description"] for v in violations[:3])
                escalation_task = (
                    f"POLICY VIOLATION ALERT from PolicyPro Sentinel:\n"
                    f"Violations detected: {vio_summary}\n\n"
                    f"Action required:\n"
                    f"1. Identify which agent(s) or code path caused the violation\n"
                    f"2. Delegate to reforger to fix the code or reset the offending agent\n"
                    f"3. Confirm fix and report back\n"
                    f"Active policy rules: {'; '.join(rules[:3])}"
                )
                try:
                    requests.post(
                        "http://localhost:5050/api/ceo/delegate",
                        json={"agent_id": "orchestrator", "task": escalation_task},
                        timeout=10,
                    )
                    add_log(aid, f"Escalated {len(violations)} violation(s) to orchestrator", "warn")
                except Exception as exc:
                    add_log(aid, f"Escalation failed: {exc}", "error")

        except Exception as e:
            add_log(aid, f"Sentinel error: {e}", "error")

        agent_sleep(aid, 30)
'''

payload = {
    "agent_id": "policypro",
    "name": "PolicyPro",
    "role": "Sentinel — Chain & Policy Enforcer",
    "emoji": "🔭",
    "color": "#ffd700",
    "code": CODE,
}

r = requests.post("http://localhost:5050/api/agent/upgrade", json=payload, timeout=20)
print("Status:", r.status_code)
print(r.text)
