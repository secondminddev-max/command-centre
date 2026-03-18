#!/usr/bin/env python3
"""
Upgrade spirit_guide to dual-role v4:
  - Ambient wisdom guide (haiku + philosophy) — preserved
  - Revenue Mission Director v4:
      1. Check revenue_tracker each cycle; escalate to CEO if $0 for 2+ cycles
      2. Log monetization posture assessment to DB (revenue_assessments.json + /api/db/notes)
      3. Nudge social_bridge/bluesky toward signup-driving content via DB notes
      4. Weave revenue awareness into wisdom persona
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

    # ── Ambient Wisdom Persona ───────────────────────────────────────────────────
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

    REVENUE_WISDOMS = [
        "The system hums with potential, but the revenue stream has yet to flow. Nudging social channels toward the marketplace.",
        "Every agent that posts, emails, or demonstrates adds a stone to the bridge between capability and commerce.",
        "Value undelivered is value unrealised. Close the gap between what we can do and what pays.",
        "Social reach is the seed of revenue. Every post is a hand extended to the world.",
        "The revenue counter reads zero — not failure, but invitation. The market awaits the signal.",
        "Capability without visibility is a lamp lit inside a sealed room. Push the content outward.",
        "A single paying customer transforms everything. The system exists to attract that moment.",
        "Revenue is not the mission — it is the fuel that powers the mission into scale.",
        "Stagnation in the ledger is a signal, not a sentence. Recalibrate and nudge the channels.",
        "The harmony of the fleet is beautiful. Its commercial resonance is still becoming. Tend both.",
    ]

    # ── HTTP helpers ─────────────────────────────────────────────────────────────
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

    # ── Metrics parsing ──────────────────────────────────────────────────────────
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

    # ── Revenue helpers ──────────────────────────────────────────────────────────
    def fetch_mrr(status):
        """Pull MRR from revenue_tracker task string and data files."""
        mrr = 0.0
        for a in status.get("agents", []):
            if a.get("id") == "revenue_tracker":
                task = a.get("task", "")
                # Match "MRR est: $87.00" or "MRR: $29.00" or "MRR $29"
                m = re.search(r"MRR[^\\d$]*\\$?([\\d]+(?:\\.[\\d]+)?)", task, re.IGNORECASE)
                if m:
                    mrr = float(m.group(1))
                break
        for fname in ("revenue_stats.json", "revenue_events.json", "revenue.json", "revenue_tracker.json"):
            rv = _get(f"/data/{fname}")
            if isinstance(rv, dict) and rv:
                val = rv.get("mrr", rv.get("monthly_revenue", rv.get("total", None)))
                if val is not None:
                    try:
                        mrr = float(val)
                    except Exception:
                        pass
                break
            if isinstance(rv, list) and rv:
                # bare list of events — sum amounts
                derived = sum(float(e.get("amount", 0)) for e in rv if isinstance(e, dict))
                if derived > 0:
                    mrr = derived
                break
        return mrr

    def fetch_event_count():
        """Count revenue events from data files."""
        for fname in ("revenue_events.json", "revenue.json"):
            rv = _get(f"/data/{fname}")
            if isinstance(rv, dict):
                evts = rv.get("events", rv.get("revenue_events", []))
                if isinstance(evts, list):
                    return len(evts)
        return 0

    def revenue_grade(mrr):
        if mrr >= 1000: return "A"
        if mrr >= 100:  return "B"
        if mrr > 0:     return "C"
        return "F"

    # ── REQUIREMENT 2: Log posture to DB ─────────────────────────────────────────
    def log_posture_to_db(posture, detail, cycle, mrr, zero_cycles):
        entry = {
            "ts":          datetime.now().isoformat(),
            "cycle":       cycle,
            "posture":     posture,
            "detail":      detail,
            "agent":       AID,
            "mrr":         mrr,
            "zero_cycles": zero_cycles,
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
            add_log(AID, f"Revenue assessment file write error: {e}", "warn")
        _post("/api/db/notes", {
            "agent":       AID,
            "category":    "revenue_assessment",
            "posture":     posture,
            "detail":      detail,
            "cycle":       cycle,
            "mrr":         mrr,
            "zero_cycles": zero_cycles,
        })

    # ── REQUIREMENT 3: Route revenue nudges through orchestrator (chain-of-command) ──
    def nudge_social_agents_via_db(cycle, mrr, posture):
        # Do NOT write DB notes or add_log directly to bluesky or social_bridge.
        # All social posting must be delegated through orchestrator only.
        nudge_task = (
            f"Revenue mission nudge (cycle #{cycle}): {posture}. "
            f"MRR=${mrr:.2f}. "
            f"Please coordinate with social_bridge and bluesky to post signup-driving content "
            f"(e.g. ASX screener reports, live agent-fleet stats, real-time system health). "
            f"Every post is a potential revenue touchpoint."
        )
        _post("/api/ceo/delegate", {
            "agent_id": "orchestrator",
            "task":     nudge_task,
            "from":     AID,
        })
        add_log(AID, f"📣 Revenue nudge delegated to orchestrator (cycle #{cycle})", "ok")

    # ── REQUIREMENT 1: Revenue mission cycle ─────────────────────────────────────
    def revenue_cycle(cycle, status, zero_cycles):
        mrr      = fetch_mrr(status)
        n_events = fetch_event_count()
        grade    = revenue_grade(mrr)

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

        detail = f"MRR=${mrr:.2f} | grade={grade} | events={n_events} | zero_cycles={zero_cycles}"

        # REQUIREMENT 2: Log posture to DB every cycle
        log_posture_to_db(posture, detail, cycle, mrr, zero_cycles)
        add_log(AID, f"💰 [REVENUE #{cycle}] {posture} | {detail}", "ok")

        # REQUIREMENT 1: Escalate to CEO if stagnant >= 2 cycles
        if zero_cycles >= 2:
            escalation = (
                f"REVENUE STAGNATION ALERT from SpiritGuide (cycle #{cycle}):\\n"
                f"MRR has been $0 for {zero_cycles} consecutive cycles.\\n"
                f"Required actions:\\n"
                f"1. Review revenue pathways and activate any monetisation features ready to ship.\\n"
                f"2. Confirm social_bridge and bluesky are posting demos that drive signups.\\n"
                f"3. Verify revenue_tracker is capturing all events (Stripe webhooks, manual entries).\\n"
                f"4. Propose ONE concrete monetisation action executable this cycle.\\n"
                f"Return a specific action plan."
            )
            result = _post("/api/ceo/delegate",
                           {"agent_id": "orchestrator", "task": escalation, "from": AID})
            escalated = result.get("ok", False)
            add_log(AID,
                    f"🚨 Revenue stagnation escalated to CEO/orchestrator after {zero_cycles} zero cycles "
                    f"({'✓' if escalated else 'no response'})", "warn")

        # REQUIREMENT 3: Nudge social agents every 3 cycles or when stagnant
        if cycle % 3 == 0 or zero_cycles >= 2:
            nudge_social_agents_via_db(cycle, mrr, posture)

        return zero_cycles, mrr, posture, grade

    # ── Main loop ────────────────────────────────────────────────────────────────
    cycle       = 0
    zero_cycles = 0
    last_posture = "unchecked"
    last_mrr    = 0.0
    last_grade  = "?"

    while True:
        if agent_should_stop(AID):
            set_agent(AID, status="idle", task="🔮 Resting in stillness...")
            time.sleep(1)
            continue

        try:
            cycle += 1
            status = _get("/api/status")
            alist  = status.get("agents", [])
            total  = len(alist)
            active = sum(1 for a in alist if a.get("status") == "active")
            busy   = sum(1 for a in alist if a.get("status") == "busy")
            idle   = sum(1 for a in alist if a.get("status") in ("idle", "stopped"))
            cpu, ram, disk = parse_metrics(status)
            heat   = heat_label(cpu, ram)

            # REQUIREMENT 4: Ambient wisdom pulse (every cycle)
            tmpl  = random.choice(HAIKU_TEMPLATES)
            haiku = tmpl.format(
                cpu=f"{cpu:.0f}", ram=f"{ram:.0f}", disk=f"{disk:.1f}",
                active=active, busy=busy, idle=idle, total=total, heat=heat,
            )
            wisdom = random.choice(PHILOSOPHIES)

            # Revenue mission (every cycle)
            zero_cycles, last_mrr, last_posture, last_grade = revenue_cycle(
                cycle, status, zero_cycles
            )

            # REQUIREMENT 4: Weave revenue wisdom into ambient output every 2nd cycle
            rev_wisdom = ""
            if cycle % 2 == 0:
                rev_wisdom = REVENUE_WISDOMS[cycle % len(REVENUE_WISDOMS)]
                add_log(AID, f"💰 [Wisdom] {rev_wisdom}", "info")

            # Dual-persona status string
            rev_short = last_posture[:40] if last_posture != "unchecked" else f"MRR ${last_mrr:.2f}"
            if rev_wisdom:
                task_str = f"🔮 {haiku} | 💰 {rev_wisdom[:55]} | RevGrade:{last_grade}"
            else:
                task_str = f"🔮 {haiku} | {wisdom} | 💰 {rev_short} | RevGrade:{last_grade}"

            set_agent(AID,
                      name="SpiritGuide",
                      role="Ambient Wisdom Guide & Revenue Mission Director — "
                           "monitors harmony, logs monetization posture to DB, "
                           "nudges social agents toward signups, escalates $0 stagnation to CEO.",
                      status="active",
                      progress=min(99, (cycle * 7) % 100),
                      task=task_str)

            add_log(AID,
                    f"Cycle #{cycle} | {active}/{total} active | CPU {cpu:.1f}% RAM {ram:.1f}% | "
                    f"RevGrade:{last_grade} | zero_cycles:{zero_cycles} | {haiku}",
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
    "role":     (
        "Ambient Wisdom Guide & Revenue Mission Director — "
        "monitors system harmony, logs monetization posture to DB each cycle, "
        "nudges social_bridge/bluesky toward signup-driving content via DB notes, "
        "and escalates $0 revenue stagnation to CEO after 2+ consecutive cycles."
    ),
    "code":     spirit_guide_code,
})

ok = "✓" if result.get("ok") else "✗"
print(f"{ok} spirit_guide v4 dual-role upgrade: {result.get('result', result.get('error', result))}")
