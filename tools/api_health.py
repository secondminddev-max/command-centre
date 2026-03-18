#!/usr/bin/env python3
"""API Health Checker - tests 8 public APIs and saves results."""

import json
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

APIS = [
    {
        "name": "HN Firebase API",
        "url": "https://hacker-news.firebaseio.com/v0/topstories.json?limitToFirst=1&orderBy=%22$key%22",
        "key": "hn_firebase",
    },
    {
        "name": "GitHub API",
        "url": "https://api.github.com",
        "key": "github",
    },
    {
        "name": "Open-Meteo API",
        "url": "https://api.open-meteo.com/v1/forecast?latitude=51.5&longitude=-0.1&current_weather=true",
        "key": "open_meteo",
    },
    {
        "name": "Wikipedia API",
        "url": "https://en.wikipedia.org/api/rest_v1/page/summary/Python_(programming_language)",
        "key": "wikipedia",
    },
    {
        "name": "JSONPlaceholder",
        "url": "https://jsonplaceholder.typicode.com/todos/1",
        "key": "jsonplaceholder",
    },
    {
        "name": "httpbin.org",
        "url": "https://httpbin.org/get",
        "key": "httpbin",
    },
    {
        "name": "Local API",
        "url": "http://localhost:5050/api/status",
        "key": "local_api",
    },
]


def check_api(api: dict) -> dict:
    start = time.monotonic()
    try:
        req = urllib.request.Request(api["url"], headers={"User-Agent": "api-health-checker/1.0"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            elapsed_ms = round((time.monotonic() - start) * 1000, 1)
            status_code = resp.status
            ok = 200 <= status_code < 300
            return {
                "name": api["name"],
                "key": api["key"],
                "url": api["url"],
                "status": "ok" if ok else "error",
                "status_code": status_code,
                "response_time_ms": elapsed_ms,
                "error": None,
            }
    except urllib.error.HTTPError as e:
        elapsed_ms = round((time.monotonic() - start) * 1000, 1)
        return {
            "name": api["name"],
            "key": api["key"],
            "url": api["url"],
            "status": "error",
            "status_code": e.code,
            "response_time_ms": elapsed_ms,
            "error": str(e.reason),
        }
    except Exception as e:
        elapsed_ms = round((time.monotonic() - start) * 1000, 1)
        return {
            "name": api["name"],
            "key": api["key"],
            "url": api["url"],
            "status": "down",
            "status_code": None,
            "response_time_ms": elapsed_ms,
            "error": str(e),
        }


def main():
    print("Running API health checks...\n")
    results = []
    for api in APIS:
        result = check_api(api)
        results.append(result)
        status_icon = "✓" if result["status"] == "ok" else "✗"
        print(f"  {status_icon} {result['name']:<22} {result['status_code'] or 'N/A':<6} {result['response_time_ms']:>7} ms  {result['status']}")

    output = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "total": len(results),
        "ok": sum(1 for r in results if r["status"] == "ok"),
        "down": sum(1 for r in results if r["status"] != "ok"),
        "results": results,
    }

    out_path = Path("os.path.dirname(os.path.abspath(__file__))/data/api_health.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(output, indent=2))

    print(f"\nSummary: {output['ok']}/{output['total']} APIs healthy")
    print(f"Results saved to {out_path}")


if __name__ == "__main__":
    main()
