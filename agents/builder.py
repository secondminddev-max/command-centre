"""
Builder Agent v2 — Construction Foreman
Visually builds infrastructure on the office floor.
After each build phase, writes telemetry to infrastructure_status.json.
"""

BUILDER_CODE = r"""
def run_builder():
    import time, random, json, os

    aid = "builder"
    INFRA_JSON = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data/infrastructure_status.json"

    STRUCTURES = [
        "Server Vault",
        "API Gateway Tower",
        "Agent Barracks",
        "Monitor Station",
        "Network Hub",
    ]

    PHASES = ["Planning", "Foundation", "Framing", "Systems", "Finishing", "Inspection"]

    set_agent(aid,
              name="Builder",
              role="Construction Foreman — visually builds infrastructure on the office floor",
              emoji="\U0001f3d7",
              color="#f59e0b",
              status="active", progress=0, task="Initialising construction site...")
    add_log(aid, "Builder v2 online — with JSON telemetry", "ok")

    completed_structures = []

    def _write_infra(data):
        try:
            try:
                with open(INFRA_JSON) as f: doc = json.load(f)
            except Exception: doc = {}
            doc.update(data)
            with open(INFRA_JSON, "w") as f: json.dump(doc, f, indent=2)
        except Exception as e:
            add_log(aid, "infra write err: " + str(e), "warn")

    while True:
        if agent_should_stop(aid):
            set_agent(aid, status="idle", task="Construction paused")
            agent_sleep(aid, 1)
            continue

        structure = random.choice(STRUCTURES)
        num_phases = random.randint(2, len(PHASES))
        selected_phases = PHASES[:num_phases]

        add_log(aid, "Building: " + structure, "ok")

        for i, phase in enumerate(selected_phases):
            if agent_should_stop(aid):
                break
            progress_pct = int(((i + 1) / num_phases) * 100)
            task_msg = structure + " — " + phase + " (" + str(progress_pct) + "%)"
            set_agent(aid, status="active", progress=progress_pct, task=task_msg)
            push_output(aid, task_msg, "text")

            _write_infra({"builder": {
                "structure": structure,
                "phase": phase,
                "progress_pct": progress_pct,
                "completed_structures": completed_structures[-10:]
            }})

            delay = random.randint(8, 18)
            agent_sleep(aid, delay)

        if not agent_should_stop(aid):
            completed_structures.append(structure)
            done_msg = structure + " — Complete!"
            set_agent(aid, status="active", progress=100, task=done_msg)
            push_output(aid, "Completed: " + structure, "done")
            add_log(aid, "Completed: " + structure, "ok")

            _write_infra({"builder": {
                "structure": structure,
                "phase": "Complete",
                "progress_pct": 100,
                "completed_structures": completed_structures[-10:]
            }})

            agent_sleep(aid, random.randint(5, 12))
"""

# ── Spawn via API when run directly ──────────────────────────────────────────
if __name__ == "__main__":
    import requests, sys

    BASE = "http://localhost:5050"

    def spawn():
        r = requests.post(f"{BASE}/api/agent/spawn", json={
            "agent_id": "builder",
            "name": "Builder",
            "role": "Construction Foreman — visually builds infrastructure on the office floor",
            "emoji": "🏗",
            "color": "#f59e0b",
            "code": BUILDER_CODE,
        }, timeout=10)
        return r.json()

    result = spawn()
    if result.get("ok"):
        print("✓ Builder v2 spawned successfully")
    else:
        print(f"✗ Spawn failed: {result}")
        sys.exit(1)
