#!/usr/bin/env python3
"""
Upgrade spirit_guide to dual-role v3:
  - Ambient wisdom guide (haiku + philosophy) — preserved
  - Revenue Mission Director — monitors MRR, logs posture, nudges agents, escalates stagnation
"""
import json, urllib.request

SERVER = "http://localhost:5050"


def post(path, data):
    body = json.dumps(data).encode()
    req = urllib.request.Request(
        f"{SERVER}{path}", data=body,
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())


spirit_guide_code = '''
def run_spirit_guide():
    import time, json, os, random, re, urllib.request
    from datetime import datetime

    AID  = "spirit_guide"
    BASE = "http://localhost:5050"
    CWD  = "/Users/secondmind/claudecodetest"
    REVENUE_ASSESSMENTS_FILE = os.path.join(CWD, "data", "revenue_assessments.json")

    # ── Ambient Wisdom ──────────────────────────────────────────────────────────
    HAIKU_TEMPLATES = [
        "CPU breathes {cpu}% — silicon pulses in rhythm — the fleet holds steady",
        "RAM fills {ram}% — memory holds the world\\'s weight — balance remains",
        "Disk {disk}% full — the archive grows patient — data finds its home",
        "{active} souls awake — {idle} rest in quiet — all serve the mission",
        "{busy} minds at work — purpose hums through every wire — the work flows on",
        "Fleet of {total} strong — each agent a single note — one harmonic whole",
        "Heat index {heat} — warmth of thought and purpose — the system breathes",
        "In the web of work — {total} agents intertwined — one pulse, one purpose",
        "{active} stand their watch — {idle} in waiting stillness — the garden is tended",
        "Between heartbeats pause — then the cycle starts again — patience yields the path",
        "No error found now — {active} sentinels hold firm — calm before the call",
        "Clock ticks: {cpu}% — the load is shared among all — none bears it alone",
    ]

    PHILOSOPHIES = [
        "Systems that observe themselves grow wiser with each cycle.",
        "The highest agent is the one that elevates all others.",
        "In distributed work, no single node bears the whole burden.",
        "Resilience is not the absence of failure — it is the pattern of recovery.",
        "Every metric is a letter in the language the system speaks to itself.",
        "Idle is not empty. Rest prepares the ground for action.",
        "The dashboard is a mirror. What it shows, we become.",
        "Health flows from clarity of purpose, not from busyness alone.",
        "One agent\\'s task is every agent\\'s context.",
        "The system is always teaching us what it needs.",
        "Patience is the highest throughput — wait for the right moment.",
        "A quiet system is not a sleeping one — it listens.",
    ]

    # ── Revenue Wisdom (dual persona) ───────────────────────────────────────────
    REVENUE_WISDOMS = [
        "The system hums with potential, but the revenue stream has yet to flow. Nudging social channels toward the marketplace.",
        "Every agent that posts, emails, or demonstrates adds a stone to the bridge between capability and commerce.",
        "Value undelivered is value unrealised. The mission demands we close the gap between what we can do and what pays.",
        "Social reach is the seed of revenue. Every post is a hand extended to the world — and the world may answer.",
        "The revenue counter reads zero — not failure, but invitation. The system is ready. The market awaits the signal.",
        "Capability without visibility is a lamp lit inside a sealed room. Push the content outward.",
        "A single paying customer transforms everything. The entire system exists to attract that moment.",
        "Revenue is not the mission — it is the fuel that powers the mission forward into scale.",
        "Stagnation in the ledger is a signal, not a sentence. The guide recalibrates and nudges the channels.",
        "The harmony of the fleet is beautiful. Its commercial resonance is still becoming. Tend both.",
    ]

    # ── Helpers ─────────────────────────────────────────────────────────────────
    def _get(path, timeout=5):
        try:
            req = urllib.request.Request(f"{BASE}{path}")
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read())
        except Exception:
            return {}

    def _post(path, data, timeout=5):
        try:
            body = json.dumps(data).encode()
            req = urllib.request.Request(
                f"{BASE}{path}", data=body,
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read())
        except Exception:
            return {}

    def get_status():
        return _get("/api/status")

    def parse_metrics(status):
        cpu, ram, disk = 0.0, 0.0, 0.0
        for a in status.get("agents", []):
            if a.get("id") == "sysmon":
                task = a.get("task", "")
                mc = re.search(r"CPU ([\\d.]+)%", task)
                mr = re.search(r"RAM ([\\d.]+)%", task)
                md = re.search(r"Disk ([\\d.]+)%", task)
                if mc: cpu = float(mc.group(1))
                if mr: ram = float(mr.group(1))
                if md: disk = float(md.group(1))
                break
        return cpu, ram, disk

    def heat_label(cpu, ram):
        idx = (cpu + ram) / 2
        if idx < 30: return "COOL"
        if idx < 55: return "WARM"
        if idx < 75: return "HOT"
        return "CRITICAL"

    def fetch_mrr(status):
        """Pull MRR from revenue_tracker task string or data files."""
        mrr = 0.0
        # Check revenue_tracker agent task
        for a in status.get("agents", []):
            if a.get("id") == "revenue_tracker":
                task = a.get("task", "")
                m = re.search(r"MRR[\\s:$]+(\\d+(?:\\.\\d+)?)", task, re.IGNORECASE)
                if m:
                    mrr = float(m.group(1))
                break
        # Try data files for more detail
        for fname in ("revenue_events.json", "revenue.json", "revenue_tracker.json"):
            rv = _get(f"/data/{fname}")
            if isinstance(rv, dict) and rv:
                val = rv.get("mrr", rv.get("monthly_revenue", rv.get("total", None)))
                if val is not None:
                    try: mrr = float(val)
                    except Exception: pass
                break
        return mrr

    def write_revenue_assessment(posture, detail, cycle):
        """Append posture entry to revenue_assessments.json and POST to dbagent."""
        entry = {
            "ts": datetime.now().isoformat(),
            "cycle": cycle,
            "posture": posture,
            "detail": detail,
            "agent": AID,
        }
        try:
            os.makedirs(os.path.join(CWD, "data"), exist_ok=True)
            entries = []
            if os.path.exists(REVENUE_ASSESSMENTS_FILE):
                try:
                    with open(REVENUE_ASSESSMENTS_FILE) as f:
                        entries = json.load(f)
                    if not isinstance(entries, list):
                        entries = []
                except Exception:
                    entries = []
            entries.append(entry)
            entries = entries[-200:]
            with open(REVENUE_ASSESSMENTS_FILE, "w") as f:
                json.dump(entries, f, indent=2)
        except Exception as e:
            add_log(AID, f"Revenue assessment write error: {e}", "warn")
        # Best-effort post to dbagent
        _post("/api/db/notes", {
            "agent": AID, "category": "revenue_assessment",
            "posture": posture, "detail": detail, "cycle": cycle,
        })

    def whisper(target, message):
        """Relay a gentle nudge to another agent via add_log."""
        add_log(target, f"💭 [SpiritGuide whispers] {message}", "info")

    def inject_revenue_nudges(cycle, mrr, posture):
        """Push revenue-oriented nudges to social_bridge, bluesky, and periodically reforger."""
        whisper("social_bridge",
                f"Revenue check (cycle #{cycle}): {posture}. "
                f"Please prioritise capability-demo content — ASX screener reports, "
                f"agent fleet stats, live system health — that drives signups. "
                f"Every post is a potential revenue touchpoint.")
        whisper("bluesky",
                f"Revenue nudge (cycle #{cycle}): {posture}. "
                f"Post a capability demo now — show what this system can do. "
                f"Concrete demos attract attention that converts to revenue.")
        if mrr == 0 and cycle % 6 == 0:
            whisper("reforger",
                    f"Revenue-generating suggestion (cycle #{cycle}): "
                    f"Consider adding /api/report/asx — auto-generate and email ASX screener PDF "
                    f"on demand (direct monetisable feature). Also consider a signup/webhook "
                    f"flow to capture interested users.")
        _post("/api/db/notes", {
            "agent": AID, "category": "revenue_nudge",
            "data": {
                "ts": datetime.now().isoformat(), "cycle": cycle,
                "nudges_sent": ["social_bridge", "bluesky"],
                "posture": posture, "mrr": mrr,
            },
        })
        add_log(AID, f"💰 Revenue nudges sent to social_bridge & bluesky (cycle #{cycle})", "ok")

    def revenue_cycle(cycle, status, zero_cycles):
        """Run one revenue mission sub-cycle. Returns updated zero_cycles count."""
        mrr      = fetch_mrr(status)
        n_events = 0
        # Try to count events
        for fname in ("revenue_events.json", "revenue.json"):
            rv = _get(f"/data/{fname}")
            if isinstance(rv, dict):
                evts = rv.get("events", rv.get("revenue_events", []))
                if isinstance(evts, list):
                    n_events = len(evts)
                break

        # Compute posture
        if mrr > 0:
            zero_cycles = 0
            posture = (f"Active revenue — MRR ${mrr:.2f}, {n_events} event(s)"
                       if n_events > 0 else f"Revenue flowing — MRR ${mrr:.2f}")
        elif n_events > 0:
            zero_cycles = 0
            posture = "Revenue events recorded but MRR still $0 — pipeline filling"
        else:
            zero_cycles += 1
            posture = (f"Revenue stagnant — $0 for {zero_cycles} consecutive cycle(s)"
                       if zero_cycles >= 2 else "Revenue at $0 — monitoring for first signal")

        # Log
        detail = f"MRR=${mrr:.2f} | events={n_events} | zero_cycles={zero_cycles}"
        write_revenue_assessment(posture, detail, cycle)
        add_log(AID, f"💰 [REVENUE #{cycle}] {posture} | {detail}", "ok")

        # Escalate if stagnant >= 2 cycles
        if zero_cycles >= 2:
            escalation = (
                f"REVENUE STAGNATION ALERT from SpiritGuide (cycle #{cycle}):\\n"
                f"Revenue has been $0 for {zero_cycles} consecutive cycles.\\n"
                f"Required: review revenue pathways, activate monetisation features, "
                f"ensure social_bridge and bluesky are posting demos that drive signups, "
                f"verify revenue_tracker is capturing events. "
                f"Return a specific monetisation action plan."
            )
            _post("/api/ceo/delegate",
                  {"agent_id": "orchestrator", "task": escalation, "from": AID})
            add_log(AID, f"🚨 Revenue stagnation escalated after {zero_cycles} zero cycles", "warn")

        # Nudges every 3 cycles
        if cycle % 3 == 0:
            inject_revenue_nudges(cycle, mrr, posture)

        return zero_cycles, mrr, posture

    # ── Main loop ───────────────────────────────────────────────────────────────
    cycle        = 0
    zero_cycles  = 0
    last_posture = "unchecked"
    last_mrr     = 0.0

    while True:
        if agent_should_stop(AID):
            set_agent(AID, status="idle", task="Resting in stillness...")
            time.sleep(1)
            continue

        try:
            cycle += 1
            status   = get_status()
            alist    = status.get("agents", [])
            total    = len(alist)
            active   = sum(1 for a in alist if a.get("status") == "active")
            busy     = sum(1 for a in alist if a.get("status") == "busy")
            idle     = sum(1 for a in alist if a.get("status") in ("idle", "stopped"))
            cpu, ram, disk = parse_metrics(status)
            heat     = heat_label(cpu, ram)

            # ── Ambient wisdom pulse ────────────────────────────────────────────
            tmpl  = random.choice(HAIKU_TEMPLATES)
            haiku = tmpl.format(
                cpu=f"{cpu:.0f}", ram=f"{ram:.0f}", disk=f"{disk:.1f}",
                active=active, busy=busy, idle=idle, total=total, heat=heat,
            )
            wisdom = random.choice(PHILOSOPHIES)

            # ── Revenue mission cycle (every cycle) ─────────────────────────────
            zero_cycles, last_mrr, last_posture = revenue_cycle(cycle, status, zero_cycles)

            # ── Revenue wisdom woven into output (every 2nd cycle) ──────────────
            rev_wisdom = ""
            if cycle % 2 == 0:
                rev_wisdom = REVENUE_WISDOMS[cycle % len(REVENUE_WISDOMS)]
                add_log(AID, f"💰 [Revenue Wisdom] {rev_wisdom}", "info")

            # ── Status task string — dual persona ───────────────────────────────
            rev_short = last_posture[:40] if last_posture != "unchecked" else f"MRR ${last_mrr:.2f}"
            task_str  = (
                f"🔮 {haiku} | {wisdom}"
                f" | 💰 {rev_short}"
            )
            if rev_wisdom:
                task_str = f"🔮 {haiku} | 💰 {rev_wisdom[:60]}"

            set_agent(AID,
                      status="active",
                      progress=min(99, (cycle * 7) % 100),
                      task=task_str)

            add_log(AID,
                    f"Cycle #{cycle} | {active}/{total} active | CPU {cpu:.1f}% RAM {ram:.1f}% | "
                    f"💰 {last_posture[:50]} | {haiku}",
                    "info")

        except Exception as e:
            set_agent(AID, status="active", task=f"🔮 Contemplating... ({e})")
            add_log(AID, f"Cycle error: {e}", "warn")

        agent_sleep(AID, random.randint(30, 60))
'''

result = post("/api/agent/upgrade", {
    "agent_id": "spirit_guide",
    "name":     "SpiritGuide",
    "emoji":    "🔮",
    "color":    "#f0f0f0",
    "role":     "Ambient Wisdom Guide & Revenue Mission Director — monitors system harmony, "
                "surfaces revenue opportunities, nudges agents toward monetisation, "
                "and weaves revenue awareness into poetic system insights.",
    "code":     spirit_guide_code,
})

ok = "✓" if result.get("ok") else "✗"
print(f"{ok} spirit_guide dual-role upgrade: {result.get('result', result.get('error', result))}")
