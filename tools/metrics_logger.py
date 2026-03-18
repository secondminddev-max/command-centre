import json
import datetime
import urllib.request
import urllib.error
import os
import psutil

METRICS_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'metrics_history.json')
STATUS_URL = 'http://localhost:5050/api/status'


def fetch_status():
    try:
        with urllib.request.urlopen(STATUS_URL, timeout=3) as resp:
            data = json.loads(resp.read().decode())
            agents_active = data.get('agents_active', data.get('active_agents', 0))
            tasks_done = data.get('tasks_done', data.get('completed_tasks', 0))
            return agents_active, tasks_done
    except Exception:
        return 0, 0


def main():
    ts = datetime.datetime.now().isoformat()
    cpu = psutil.cpu_percent(interval=1)
    mem = psutil.virtual_memory().percent
    agents_active, tasks_done = fetch_status()

    snapshot = {
        "ts": ts,
        "cpu": cpu,
        "mem": mem,
        "agents_active": agents_active,
        "tasks_done": tasks_done,
    }

    metrics_path = os.path.abspath(METRICS_FILE)
    if os.path.exists(metrics_path):
        with open(metrics_path, 'r') as f:
            history = json.load(f)
    else:
        history = []

    history.append(snapshot)

    with open(metrics_path, 'w') as f:
        json.dump(history, f, indent=2)

    print(json.dumps(snapshot, indent=2))
    print(f"\nAppended to {metrics_path} ({len(history)} total entries)")


if __name__ == '__main__':
    main()
