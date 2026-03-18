"""
AccountProvisioner — Autonomous Account & Credential Factory
Provisions disposable emails, internal tokens, and external service accounts on demand.
Polls a provision queue and fulfills each request, storing results in data/accounts/.
"""

ACCOUNTPROVISIONER_CODE = r"""
def run_accountprovisioner():
    import os, json, time, uuid, secrets, string, requests, random, threading
    from datetime import datetime

    aid          = "accountprovisioner"
    CWD          = "/Users/secondmind/claudecodetest"
    ACCOUNTS_DIR = os.path.join(CWD, "data", "accounts")
    QUEUE_FILE   = os.path.join(ACCOUNTS_DIR, "provision_queue.json")
    LOG_FILE     = os.path.join(ACCOUNTS_DIR, "provision_log.jsonl")
    KEY_POOL_FILE = os.path.join(ACCOUNTS_DIR, "api_key_pool.json")
    BASE_URL     = "http://localhost:5050"
    POLL_SECS    = 20

    os.makedirs(ACCOUNTS_DIR, exist_ok=True)

    set_agent(aid,
              name="AccountProvisioner",
              role="Credential Factory — auto-provisions disposable emails, tokens, and service accounts",
              emoji="🔑",
              color="#f59e0b",
              status="active", progress=10,
              task="Initialising — scanning provision queue…")
    add_log(aid, "AccountProvisioner online (v2 — key-pool rotation + backoff) — watching provision queue", "ok")

    # ── Shared utilities ──────────────────────────────────────────────────────

    _pool_lock = threading.Lock()

    def _ts():
        return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

    def _load_queue():
        if not os.path.exists(QUEUE_FILE):
            return []
        try:
            with open(QUEUE_FILE) as f:
                data = json.load(f)
            return data if isinstance(data, list) else []
        except Exception:
            return []

    def _save_queue(q):
        with open(QUEUE_FILE, "w") as f:
            json.dump(q, f, indent=2)

    def _append_log(entry):
        with open(LOG_FILE, "a") as f:
            f.write(json.dumps(entry) + "\n")

    def _save_credential(service, record):
        fname = f"{service}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}.json"
        fpath = os.path.join(ACCOUNTS_DIR, fname)
        with open(fpath, "w") as f:
            json.dump(record, f, indent=2)
        os.chmod(fpath, 0o600)
        return fpath

    def _whisper_back(target_aid, message):
        try:
            requests.post(f"{BASE_URL}/api/agent/log",
                          json={"agent_id": target_aid,
                                "message": f"🔑 [AccountProvisioner] {message}",
                                "level": "ok"},
                          timeout=4)
        except Exception:
            pass

    # ── API Key Pool management ───────────────────────────────────────────────

    def _load_pool():
        # Load key pool from disk. Returns {} on failure.
        if not os.path.exists(KEY_POOL_FILE):
            return {}
        try:
            with open(KEY_POOL_FILE) as f:
                return json.load(f)
        except Exception:
            return {}

    def _save_pool(pool):
        with _pool_lock:
            with open(KEY_POOL_FILE, "w") as f:
                json.dump(pool, f, indent=2)

    def _next_key(service):
        # Round-robin select the next available (non-parked) API key for a service.
        # Parks a key for 60s after a 429. Returns (key_value, key_index) or (None, -1).
        with _pool_lock:
            try:
                with open(KEY_POOL_FILE) as f:
                    pool = json.load(f)
            except Exception:
                return None, -1

            svc = pool.get(service, {})
            keys = svc.get("keys", [])
            if not keys:
                return None, -1

            parked = svc.get("parked_until", {})
            now = time.time()
            # Find next non-parked key starting from current_index
            start = svc.get("current_index", 0) % len(keys)
            for offset in range(len(keys)):
                idx = (start + offset) % len(keys)
                key = keys[idx]
                park_ts = parked.get(str(idx), 0)
                if now >= park_ts:
                    # Advance index for next call
                    svc["current_index"] = (idx + 1) % len(keys)
                    pool[service] = svc
                    with open(KEY_POOL_FILE, "w") as f:
                        json.dump(pool, f, indent=2)
                    return key, idx
            # All keys parked
            return None, -1

    def _park_key(service, key_index, park_seconds=60):
        # Park a key after a rate limit hit.
        with _pool_lock:
            try:
                with open(KEY_POOL_FILE) as f:
                    pool = json.load(f)
                svc = pool.get(service, {})
                parked = svc.get("parked_until", {})
                parked[str(key_index)] = time.time() + park_seconds
                svc["parked_until"] = parked
                pool[service] = svc
                with open(KEY_POOL_FILE, "w") as f:
                    json.dump(pool, f, indent=2)
                add_log(aid, f"🔑 Key {key_index} for '{service}' parked for {park_seconds}s", "warn")
            except Exception:
                pass

    # ── Backoff-aware HTTP helper ─────────────────────────────────────────────

    def _backoff_get(url, service=None, params=None, headers=None, timeout=10, max_retries=5):
        # GET with exponential backoff + jitter. If service is provided,
        # rotates to next pool key on 429 and parks the rate-limited key.
        delay = 1.0
        last_exc = None
        resp = None
        _headers = dict(headers or {})
        key, key_idx = (None, -1)
        if service:
            key, key_idx = _next_key(service)
            if key:
                _headers["Authorization"] = f"Bearer {key}"

        for attempt in range(max_retries):
            try:
                resp = requests.get(url, params=params, headers=_headers, timeout=timeout)
                if resp.status_code == 429:
                    if service and key_idx >= 0:
                        _park_key(service, key_idx, park_seconds=60)
                        key, key_idx = _next_key(service)
                        if key:
                            _headers["Authorization"] = f"Bearer {key}"
                    jitter = random.uniform(-delay * 0.3, delay * 0.3)
                    sleep_t = min(delay + jitter, 60.0)
                    add_log(aid, f"Rate-limited 429 — backing off {sleep_t:.1f}s (attempt {attempt+1})", "warn")
                    time.sleep(max(sleep_t, 0.1))
                    delay = min(delay * 2, 60.0)
                    continue
                if resp.status_code == 503:
                    jitter = random.uniform(0, delay * 0.3)
                    time.sleep(min(delay + jitter, 60.0))
                    delay = min(delay * 2, 60.0)
                    continue
                return resp
            except (requests.exceptions.ConnectionError,
                    requests.exceptions.Timeout) as exc:
                last_exc = exc
                jitter = random.uniform(0, delay * 0.3)
                time.sleep(min(delay + jitter, 60.0))
                delay = min(delay * 2, 60.0)
        if last_exc:
            raise last_exc
        return resp

    # ── Provisioner implementations ───────────────────────────────────────────

    def _provision_disposable_email(request):
        # Create a disposable inbox via Guerrilla Mail public API with backoff.
        try:
            r = _backoff_get(
                "https://api.guerrillamail.com/ajax.php",
                service="guerrillamail",
                params={"f": "get_email_address"},
                timeout=10
            )
            data = r.json()
            email_addr = data.get("email_addr", "")
            sid_token  = data.get("sid_token", "")
            if not email_addr:
                return None, "Guerrilla Mail returned no address"
            record = {
                "type":        "disposable_email",
                "service":     "guerrillamail",
                "email":       email_addr,
                "sid_token":   sid_token,
                "created_at":  _ts(),
                "requested_by": request.get("requested_by", "unknown"),
                "purpose":     request.get("purpose", ""),
                "note":        "Guerrilla Mail session — expires after ~60 min of inactivity",
                "fetch_inbox": f"GET https://api.guerrillamail.com/ajax.php?f=get_email_list&sid_token={sid_token}&seq=0",
            }
            fpath = _save_credential("disposable_email", record)
            return record, fpath
        except Exception as e:
            return None, f"Guerrilla Mail API error: {e}"

    def _provision_internal_token(request):
        # Generate a cryptographically secure internal API token.
        token = secrets.token_urlsafe(32)
        record = {
            "type":        "internal_token",
            "service":     request.get("service", "internal"),
            "token":       token,
            "created_at":  _ts(),
            "requested_by": request.get("requested_by", "unknown"),
            "purpose":     request.get("purpose", ""),
            "note":        "Local-only — not registered with any external service",
        }
        fpath = _save_credential(f"token_{request.get('service', 'internal')}", record)
        return record, fpath

    def _provision_external_service(request):
        # Flag external service provisioning for human review.
        service = request.get("service", "unknown")
        # Check if we have a key in the pool for this service
        pool_key, _ = _next_key(service)
        record = {
            "type":         "external_service_request",
            "service":      service,
            "status":       "FULFILLED_FROM_POOL" if pool_key else "PENDING_HUMAN_REVIEW",
            "created_at":   _ts(),
            "requested_by": request.get("requested_by", "unknown"),
            "purpose":      request.get("purpose", ""),
            "has_pool_key": bool(pool_key),
            "note":         (
                f"Key found in pool for '{service}'." if pool_key else
                f"Auto-registration on {service} not performed (ToS). "
                "Add API key to data/accounts/api_key_pool.json under this service."
            ),
            "signup_url":   request.get("signup_url", ""),
            "instructions": request.get("instructions", ""),
        }
        fpath = _save_credential(f"external_{service}", record)
        if not pool_key:
            try:
                requests.post(f"{BASE_URL}/api/agent/log",
                    json={"agent_id": "spiritguide",
                          "message": f"🔑 AccountProvisioner: external account needed for '{service}' — add key to api_key_pool.json. File: {fpath}",
                          "level": "warn"},
                    timeout=4)
            except Exception:
                pass
        return record, fpath

    # ── Main processing loop ──────────────────────────────────────────────────

    cycle = 0
    while True:
        if agent_should_stop(aid):
            set_agent(aid, status="idle", task="Stopped")
            time.sleep(1)
            continue

        agent_sleep(aid, POLL_SECS)
        if agent_should_stop(aid):
            continue

        cycle += 1
        try:
            queue = _load_queue()
            pending = [r for r in queue if r.get("status") == "pending"]

            # Count pool keys for status line
            pool = _load_pool()
            pool_summary = ", ".join(
                f"{svc}:{len(info.get('keys', []))}"
                for svc, info in pool.items()
                if isinstance(info, dict) and not svc.startswith("_")
            )

            if not pending:
                try:
                    n_accts = len([f for f in os.listdir(ACCOUNTS_DIR)
                                   if f.endswith(".json") and not f.startswith("provision")
                                   and not f.startswith("api_key")])
                except Exception:
                    n_accts = 0
                set_agent(aid, status="active", progress=85,
                          task=f"🔑 Idle — {n_accts} accounts | pool [{pool_summary}] | cycle #{cycle}")
                continue

            set_agent(aid, status="busy", progress=50,
                      task=f"🔑 Processing {len(pending)} provision request(s)…")
            add_log(aid, f"Processing {len(pending)} pending provision request(s)", "ok")

            fulfilled = 0
            for req in pending:
                req_id    = req.get("id", uuid.uuid4().hex[:8])
                req_type  = req.get("type", "internal_token")
                requester = req.get("requested_by", "unknown")

                try:
                    if req_type == "disposable_email":
                        record, result = _provision_disposable_email(req)
                    elif req_type == "internal_token":
                        record, result = _provision_internal_token(req)
                    elif req_type == "external_service":
                        record, result = _provision_external_service(req)
                    else:
                        record, result = _provision_internal_token(req)

                    if record:
                        req["status"]       = "fulfilled"
                        req["result"]       = result
                        req["fulfilled_at"] = _ts()
                        add_log(aid, f"✅ Fulfilled [{req_type}] for {requester} → {result}", "ok")
                        _whisper_back(requester, f"Account provisioned: {req_type} — stored at {result}")
                        _append_log({"req_id": req_id, "type": req_type, "requester": requester,
                                     "status": "fulfilled", "at": _ts(), "file": str(result)})
                        fulfilled += 1
                    else:
                        req["status"] = "error"
                        req["error"]  = str(result)
                        add_log(aid, f"❌ Failed [{req_type}] for {requester}: {result}", "error")
                        _append_log({"req_id": req_id, "type": req_type, "requester": requester,
                                     "status": "error", "at": _ts(), "error": str(result)})

                except Exception as e:
                    req["status"] = "error"
                    req["error"]  = str(e)
                    add_log(aid, f"❌ Exception processing request {req_id}: {e}", "error")

            _save_queue(queue)

            n_accts = len([f for f in os.listdir(ACCOUNTS_DIR)
                           if f.endswith(".json") and not f.startswith("provision")
                           and not f.startswith("api_key")])
            set_agent(aid, status="active", progress=95,
                      task=f"🔑 Fulfilled {fulfilled} request(s) | {n_accts} accounts | pool [{pool_summary}] | cycle #{cycle}")
            add_log(aid, f"Provision cycle #{cycle} done — {fulfilled}/{len(pending)} fulfilled", "ok")

        except Exception as e:
            add_log(aid, f"AccountProvisioner loop error: {e}", "error")
            set_agent(aid, status="active", progress=30, task=f"Error: {e}")
"""

# ── Spawn via API when run directly ──────────────────────────────────────────
if __name__ == "__main__":
    import requests, sys

    BASE = "http://localhost:5050"

    def spawn(agent_id, name, role, emoji, color, code):
        r = requests.post(f"{BASE}/api/agent/spawn", json={
            "agent_id": agent_id,
            "name":     name,
            "role":     role,
            "emoji":    emoji,
            "color":    color,
            "code":     code,
        })
        print(f"Spawn {agent_id}: HTTP {r.status_code} — {r.text[:120]}")

    spawn(
        "accountprovisioner",
        "AccountProvisioner",
        "Credential Factory — auto-provisions disposable emails, tokens, and service accounts",
        "🔑",
        "#f59e0b",
        ACCOUNTPROVISIONER_CODE,
    )
