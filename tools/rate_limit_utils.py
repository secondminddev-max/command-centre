"""
rate_limit_utils.py — Shared rate-limit survival utilities.

Provides:
  - backoff_request(method, url, ...)  — exponential backoff + jitter on 429/503
  - TTLCache                           — lightweight in-memory TTL cache
  - RequestQueue                       — serialised queue to avoid thundering herd

Designed to be embedded inline in agent code strings (copy the block you need)
or imported directly when running outside the agent exec context.
"""

import time
import random
import threading
import requests as _requests


# ── Exponential Backoff ───────────────────────────────────────────────────────

def backoff_request(method, url, *, params=None, headers=None, json=None,
                    data=None, timeout=10, max_retries=5, base_delay=1.0,
                    max_delay=60.0, retry_on=(429, 503)):
    """
    Make an HTTP request with exponential backoff + full jitter.

    Retries on HTTP status codes in retry_on (default 429, 503) and on
    connection errors.  Delay sequence: 1s, 2s, 4s, 8s … capped at max_delay,
    with ±30% jitter to prevent thundering herd.

    Returns a requests.Response or raises on final failure.
    """
    delay = base_delay
    last_exc = None
    for attempt in range(max_retries):
        try:
            resp = _requests.request(
                method, url,
                params=params, headers=headers,
                json=json, data=data,
                timeout=timeout,
            )
            if resp.status_code not in retry_on:
                return resp
            # Rate-limited — respect Retry-After if present
            retry_after = resp.headers.get("Retry-After")
            if retry_after:
                try:
                    sleep_t = min(float(retry_after), max_delay)
                except ValueError:
                    sleep_t = min(delay, max_delay)
            else:
                jitter = random.uniform(-delay * 0.3, delay * 0.3)
                sleep_t = min(delay + jitter, max_delay)
            time.sleep(max(sleep_t, 0.1))
            delay = min(delay * 2, max_delay)
        except (
            _requests.exceptions.ConnectionError,
            _requests.exceptions.Timeout,
            _requests.exceptions.ChunkedEncodingError,
        ) as exc:
            last_exc = exc
            jitter = random.uniform(0, delay * 0.3)
            time.sleep(min(delay + jitter, max_delay))
            delay = min(delay * 2, max_delay)
    if last_exc:
        raise last_exc
    return resp  # last response (rate-limited) if no exception


def backoff_get(url, **kwargs):
    """Convenience: GET with backoff."""
    return backoff_request("GET", url, **kwargs)


def backoff_post(url, **kwargs):
    """Convenience: POST with backoff."""
    return backoff_request("POST", url, **kwargs)


# ── TTL Cache ─────────────────────────────────────────────────────────────────

class TTLCache:
    """
    Thread-safe in-memory TTL cache.

    Usage:
        cache = TTLCache(ttl_seconds=900)   # 15-minute default
        val = cache.get("hn_stories")
        if val is None:
            val = fetch_stories()
            cache.set("hn_stories", val)
    """

    def __init__(self, ttl_seconds=900):
        self._store = {}          # key -> (value, expiry_timestamp)
        self._ttl = ttl_seconds
        self._lock = threading.Lock()

    def get(self, key):
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            value, expiry = entry
            if time.time() < expiry:
                return value
            del self._store[key]
            return None

    def set(self, key, value, ttl_seconds=None):
        ttl = ttl_seconds if ttl_seconds is not None else self._ttl
        with self._lock:
            self._store[key] = (value, time.time() + ttl)

    def invalidate(self, key):
        with self._lock:
            self._store.pop(key, None)

    def clear(self):
        with self._lock:
            self._store.clear()

    def stats(self):
        with self._lock:
            now = time.time()
            live = sum(1 for _, (_, exp) in self._store.items() if now < exp)
            return {"total": len(self._store), "live": live, "expired": len(self._store) - live}


# ── Request Queue ─────────────────────────────────────────────────────────────

class RequestQueue:
    """
    Serialise HTTP calls through a shared semaphore so multiple agents
    don't hammer the same API simultaneously.

    Usage:
        _q = RequestQueue(max_concurrent=2, min_interval=0.5)
        resp = _q.get("https://api.example.com/data")
    """

    def __init__(self, max_concurrent=2, min_interval=0.25):
        self._sem = threading.Semaphore(max_concurrent)
        self._min_interval = min_interval
        self._last_call = 0.0
        self._lock = threading.Lock()

    def _throttle(self):
        with self._lock:
            now = time.time()
            wait = self._min_interval - (now - self._last_call)
            if wait > 0:
                time.sleep(wait)
            self._last_call = time.time()

    def request(self, method, url, **kwargs):
        with self._sem:
            self._throttle()
            return backoff_request(method, url, **kwargs)

    def get(self, url, **kwargs):
        return self.request("GET", url, **kwargs)

    def post(self, url, **kwargs):
        return self.request("POST", url, **kwargs)
