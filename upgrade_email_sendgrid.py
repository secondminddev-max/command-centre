#!/usr/bin/env python3
"""
Upgrade email agents to use SendGrid SMTP as primary transport.

emailagent: full SendGrid SMTP implementation (smtp.sendgrid.net:587, TLS)
            - Reads SENDGRID_API_KEY (password) and SENDGRID_FROM_EMAIL (sender) from env
            - Logs clear warning if key not set; stays idle rather than crashing
            - Exposes /api/email/send API (already in server)

emailer:    consolidated — redirects incoming queue items to emailagent's queue
            and stays idle, preventing double-processing of email_queue.json
"""
import json, urllib.request

SERVER = "http://localhost:5050"

def post(path, data):
    body = json.dumps(data).encode()
    req  = urllib.request.Request(f"{SERVER}{path}", data=body,
                                  headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read())

# ── EmailAgent: SendGrid SMTP primary ─────────────────────────────────────────
emailagent_code = open("/Users/secondmind/claudecodetest/agents/emailagent.py").read()

# ── Emailer: consolidated stub — defers to emailagent ────────────────────────
emailer_code = '''
def run_emailer():
    import time, json, os
    aid = "emailer"
    CWD = "/Users/secondmind/claudecodetest"
    # emailer is consolidated into emailagent. It monitors the emailagent queue
    # depth and reports it, but does NOT consume messages — emailagent is the sole
    # processor of email_queue.json to prevent double-dispatch race conditions.
    QUEUE_FILE = os.path.join(CWD, "data", "email_queue.json")
    set_agent(aid, name="EmailAgent",
              role="Email dispatch agent \u2014 consolidated into emailagent (single queue processor)",
              emoji="\U0001f4e7", color="#22D3EE", status="idle", progress=0,
              task="Consolidated \u2014 emailagent handles all dispatch")
    add_log(aid, "emailer consolidated: all email dispatch handled by emailagent", "ok")
    cycle = 0
    while not agent_should_stop(aid):
        cycle += 1
        try:
            queue = json.load(open(QUEUE_FILE)) if os.path.exists(QUEUE_FILE) else []
            depth = len(queue)
        except Exception:
            depth = 0
        set_agent(aid, status="idle", progress=0,
                  task=f"Consolidated \u2014 emailagent handles dispatch | queue depth: {depth} | cycle #{cycle}")
        agent_sleep(aid, 30)
    set_agent(aid, status="idle", task="Stopped")
'''

upgrades = [
    {
        "agent_id": "emailagent",
        "name":     "EmailAgent",
        "emoji":    "\U0001f4e7",
        "color":    "#00cc88",
        "role":     "Email Gateway \u2014 sends notifications, reports, and alerts via SendGrid SMTP",
        "code":     emailagent_code,
    },
    {
        "agent_id": "emailer",
        "name":     "EmailAgent",
        "emoji":    "\U0001f4e7",
        "color":    "#22D3EE",
        "role":     "Email dispatch agent \u2014 consolidated into emailagent (single queue processor)",
        "code":     emailer_code,
    },
]

for u in upgrades:
    print(f"Upgrading {u['agent_id']}...", end=" ", flush=True)
    result = post("/api/agent/upgrade", u)
    status = "\u2713" if result.get("ok") else "\u2717"
    print(f"{status} {result.get('result', result.get('error', result))}")

print("\nDone. Verify with:")
print("  curl http://localhost:5050/api/email/status")
print("  curl -s http://localhost:5050/api/status | python3 -c \"import json,sys; [print(a['id'],a['status'],a['task'][:60]) for a in json.load(sys.stdin)['agents'] if 'email' in a['id']]\"")
