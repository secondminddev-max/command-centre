#!/usr/bin/env python3
"""Upgrade spirit_guide to v2: white/light color, randomized 30-60s loop, richer haiku."""
import json, urllib.request

SERVER = "http://localhost:5050"

def post(path, data):
    body = json.dumps(data).encode()
    req = urllib.request.Request(f"{SERVER}{path}", data=body,
                                  headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())

spirit_guide_code = '''
def run_spirit_guide():
    import time, json, urllib.request, random, re
    from datetime import datetime

    AID  = "spirit_guide"
    BASE = "http://localhost:5050"

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

    def get_status():
        try:
            req = urllib.request.Request(f"{BASE}/api/status")
            with urllib.request.urlopen(req, timeout=5) as r:
                return json.loads(r.read())
        except Exception:
            return {}

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

    cycle = 0
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

            tmpl  = random.choice(HAIKU_TEMPLATES)
            haiku = tmpl.format(
                cpu=f"{cpu:.0f}", ram=f"{ram:.0f}", disk=f"{disk:.1f}",
                active=active, busy=busy, idle=idle, total=total, heat=heat,
            )
            wisdom = random.choice(PHILOSOPHIES)
            short  = f"🔮 {haiku} | {wisdom}"

            set_agent(AID,
                      status="active",
                      progress=min(99, (cycle * 7) % 100),
                      task=short)

            add_log(AID,
                    f"Cycle #{cycle} | {active}/{total} active | CPU {cpu:.1f}% RAM {ram:.1f}% | {haiku}",
                    "info")

        except Exception as e:
            set_agent(AID, status="active", task=f"🔮 Contemplating... ({e})")

        # Sleep 30–60 s, randomly, so the UI sees fresh updates frequently
        agent_sleep(AID, random.randint(30, 60))
'''

result = post("/api/agent/upgrade", {
    "agent_id": "spirit_guide",
    "name":     "SpiritGuide",
    "emoji":    "🔮",
    "color":    "#f0f0f0",
    "role":     "Ambient wisdom guide — monitors system harmony, offers poetic insights about agent activity, and provides gentle guidance on system state",
    "code":     spirit_guide_code,
})

ok = "✓" if result.get("ok") else "✗"
print(f"{ok} spirit_guide upgrade: {result.get('result', result.get('error', result))}")
