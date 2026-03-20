"""
evolution_engine.py — Self-Evolving Workforce Engine

Continuously evaluates agent fitness, identifies underperformers,
proposes upgrades via Claude CLI, applies them through /api/agent/upgrade,
and tracks generational improvement. Implements evolutionary selection:
  - Keep improvements (fitness goes up)
  - Rollback regressions (fitness goes down within grace period)
  - Propagate successful patterns across the fleet

Fitness formula per agent:
  fitness = 0.3*uptime + 0.3*task_success + 0.2*(1-error_rate) + 0.1*responsiveness + 0.1*delegation_throughput

Evolution cycle (every 5 minutes):
  1. EVALUATE — score all agents on fitness metrics
  2. SELECT   — identify bottom 3 underperformers (fitness < 0.5)
  3. PROPOSE  — ask Claude CLI to generate upgrade code for each
  4. APPLY    — deploy via /api/agent/upgrade
  5. VERIFY   — wait grace period, compare before/after fitness
  6. ROLLBACK — revert if fitness dropped (keep backup code)
"""

EVOLUTION_ENGINE_CODE = r'''
def run_evolution_engine():
    import time, json, os, subprocess, threading, traceback, hashlib
    from datetime import datetime
    from collections import deque

    aid = "evolution_engine"
    if "CWD" in dir() or "CWD" in globals():
        _cwd = globals().get("CWD", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    else:
        _cwd = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    STATE_FILE     = f"{_cwd}/data/evolution_state.json"
    EVAL_INTERVAL  = 300      # evaluate every 5 minutes
    GRACE_PERIOD   = 600      # 10 min before rollback decision
    MIN_UPTIME     = 120      # agent must be up 2min before evaluation
    MAX_CONCURRENT = 2        # max simultaneous upgrades
    EVOLUTION_CAP  = 50       # max total auto-upgrades per session (safety)

    # Agents that should NEVER be auto-upgraded (critical infrastructure)
    PROTECTED = {"ceo", "orchestrator", "reforger", "fleet_healer", "policypro",
                 "evolution_engine", "consciousness", "sysmon", "alertwatch"}

    set_agent(aid,
              name="EvolutionEngine",
              role="Self-Evolving Workforce — evaluates fitness, upgrades underperformers, rolls back regressions",
              emoji="🧬", color="#10b981",
              status="active", progress=0,
              task="Initialising evolution engine…")
    add_log(aid, "🧬 Evolution Engine online — self-evolving workforce active")

    # ── State management ─────────────────────────────────────────────────
    def _blank_state():
        return {
            "total_evaluations": 0,
            "total_upgrades": 0,
            "total_rollbacks": 0,
            "total_improvements": 0,
            "generation_map": {},       # agent_id -> generation number
            "upgrade_history": [],      # [{agent, gen, fitness_before, fitness_after, ts, outcome}]
            "code_backups": {},         # agent_id -> last known good code
            "pending_upgrades": {},     # agent_id -> {applied_at, fitness_before, code_backup}
            "started_at": datetime.now().isoformat(),
        }

    def _save(state):
        try:
            os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
            with open(STATE_FILE, "w") as f:
                json.dump(state, f, indent=2, default=str)
        except Exception:
            pass

    def _load():
        try:
            with open(STATE_FILE) as f:
                s = json.load(f)
                # Ensure all keys exist
                blank = _blank_state()
                for k in blank:
                    if k not in s:
                        s[k] = blank[k]
                return s
        except Exception:
            return _blank_state()

    state = _load()

    # ── Fitness Evaluation ────────────────────────────────────────────────
    def evaluate_all():
        """Score every agent on 5 fitness dimensions → composite fitness [0, 1]."""
        import requests as _req
        try:
            resp = _req.get("http://localhost:5050/api/status", timeout=10)
            data = resp.json()
        except Exception:
            return {}

        fleet_health = {}
        try:
            fh = _req.get("http://localhost:5050/api/fleet/health", timeout=10)
            for a in fh.json().get("agents", []):
                fleet_health[a["agent_id"]] = a
        except Exception:
            pass

        scores = {}
        now = time.time()

        for agent in data.get("agents", []):
            a_id = agent.get("id", "")
            if not a_id or a_id in PROTECTED:
                continue

            status = agent.get("status", "idle")
            progress = agent.get("progress", 0) or 0

            # 1. Uptime percentage (from fleet health)
            fh_data = fleet_health.get(a_id, {})
            uptime_s = fh_data.get("uptime_s", 0)
            restarts = fh_data.get("restarts", 0)
            alive = fh_data.get("alive", False)
            # Penalise restarts: each restart costs 10% uptime score
            uptime_pct = min(1.0, uptime_s / max(1, now - _SERVER_START)) if alive else 0.0
            uptime_score = max(0, uptime_pct - (restarts * 0.1))

            # 2. Task success rate (from progress and status)
            if status == "active" and progress >= 50:
                task_score = min(1.0, progress / 100.0)
            elif status == "busy":
                task_score = 0.7  # working is decent
            elif status == "idle":
                task_score = 0.4  # idle is neutral
            elif status == "error":
                task_score = 0.0
            else:
                task_score = 0.3

            # 3. Error rate (inverse — low errors = high score)
            error_score = 0.0 if status == "error" else (0.8 if status in ("active", "busy") else 0.5)
            # Additional penalty for repeated restarts
            error_score = max(0, error_score - (restarts * 0.15))

            # 4. Responsiveness (how quickly agent processes — approximated by progress)
            responsiveness = min(1.0, progress / 100.0) if progress > 0 else 0.3

            # 5. Delegation throughput (task_count if available)
            task_count = agent.get("task_count", 0) or 0
            delegation_score = min(1.0, task_count / 10.0) if task_count > 0 else 0.3

            # Composite fitness
            fitness = (
                0.30 * uptime_score +
                0.30 * task_score +
                0.20 * error_score +
                0.10 * responsiveness +
                0.10 * delegation_score
            )
            fitness = round(max(0.0, min(1.0, fitness)), 4)

            generation = state["generation_map"].get(a_id, 0)

            scores[a_id] = {
                "uptime_score": round(uptime_score, 4),
                "task_score": round(task_score, 4),
                "error_score": round(error_score, 4),
                "responsiveness": round(responsiveness, 4),
                "delegation_score": round(delegation_score, 4),
                "fitness": fitness,
                "generation": generation,
                "status": status,
                "restarts": restarts,
            }

            # Push to server fitness registry
            try:
                record_fitness(a_id, scores[a_id])
            except Exception:
                pass

        return scores

    # ── Upgrade Proposal (Claude CLI) ─────────────────────────────────────
    def propose_upgrade(a_id, current_fitness, scores):
        """Ask Claude CLI to generate an improved version of the agent code."""
        agent_file = f"{_cwd}/agents/{a_id}.py"
        if not os.path.exists(agent_file):
            return None

        try:
            with open(agent_file) as f:
                current_code = f.read()
        except Exception:
            return None

        # Truncate if very long to stay within CLI limits
        if len(current_code) > 12000:
            current_code = current_code[:12000] + "\n# ... (truncated)"

        score_summary = json.dumps(scores.get(a_id, {}), indent=2)

        prompt = f"""You are an AI agent optimizer. Analyze this agent code and its fitness scores, then output ONLY the improved Python code (no explanation, no markdown fences).

AGENT: {a_id}
FITNESS: {current_fitness:.4f} (needs improvement)
SCORES:
{score_summary}

CURRENT CODE:
{current_code}

RULES:
- Keep the same CODE variable name and function signature
- Improve error handling, recovery logic, and efficiency
- Add better status reporting (set_agent calls with meaningful progress)
- Fix any bugs or anti-patterns you see
- Do NOT change the agent's core purpose
- Do NOT add external dependencies
- Keep changes minimal and surgical — don't rewrite from scratch
- Output ONLY the raw Python code, nothing else"""

        # SECURITY: Strip env to prevent unauthorized delegation
        _safe_env = {k: v for k, v in os.environ.items()
                     if k not in ("HQ_API_KEY", "DELEGATION_TOKEN")}

        try:
            proc = subprocess.run(
                ["claude", "-p", prompt, "--output-format", "text", "--max-turns", "0"],
                capture_output=True, text=True, cwd=_cwd, timeout=120,
                env=_safe_env
            )
            if proc.returncode == 0 and proc.stdout.strip():
                code = proc.stdout.strip()
                # Strip markdown fences if present
                if code.startswith("```"):
                    lines = code.split("\n")
                    code = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
                return code
        except Exception:
            pass
        return None

    # ── Upgrade Application ───────────────────────────────────────────────
    def apply_upgrade(a_id, new_code, current_fitness):
        """Write new code to agent file and trigger /api/agent/upgrade."""
        agent_file = f"{_cwd}/agents/{a_id}.py"

        # Backup current code
        try:
            with open(agent_file) as f:
                backup = f.read()
            state["code_backups"][a_id] = backup
        except Exception:
            return False

        # Write new code
        try:
            with open(agent_file, "w") as f:
                f.write(new_code)
        except Exception:
            return False

        # Find the CODE variable name
        code_var = None
        for line in new_code.split("\n"):
            if line.strip().startswith("def run_"):
                break
            _tq = "'" * 3
            if "CODE" in line and "=" in line and _tq in line:
                code_var = line.split("=")[0].strip()
                break
            if "CODE" in line and "=" in line and '"""' in line:
                code_var = line.split("=")[0].strip()
                break

        if not code_var:
            # Fallback: look for standard naming
            code_var = f"{a_id.upper()}_CODE"

        # Extract the code string from the file
        try:
            import importlib.util as _ilu
            spec = _ilu.spec_from_file_location(a_id, agent_file)
            mod = _ilu.module_from_spec(spec)
            spec.loader.exec_module(mod)
            agent_code = getattr(mod, code_var, None)
            if not agent_code:
                # Try common variants
                for cv in [f"{a_id.upper()}_CODE", f"{a_id.upper().replace('_','')}CODE"]:
                    agent_code = getattr(mod, cv, None)
                    if agent_code:
                        break
            if not agent_code:
                raise ValueError(f"No CODE variable found in upgraded {agent_file}")
        except Exception as e:
            # Rollback file
            with open(agent_file, "w") as f:
                f.write(backup)
            add_log(aid, f"❌ Upgrade {a_id} failed (bad code): {e}", "error")
            return False

        # Get agent metadata from current state
        with lock:
            agent_meta = dict(agents.get(a_id, {}))

        # Deploy via internal spawn (upgrade = stop + spawn)
        try:
            _stop_ev(a_id).set()
            time.sleep(3)
            result = _do_spawn_agent({
                "agent_id": a_id,
                "code": agent_code,
                "name": agent_meta.get("name", a_id),
                "role": agent_meta.get("role", "Evolved Agent"),
                "emoji": agent_meta.get("emoji", "🤖"),
                "color": agent_meta.get("color", "#888"),
            })
            if "ERROR" in result:
                raise ValueError(result)
        except Exception as e:
            # Rollback
            with open(agent_file, "w") as f:
                f.write(backup)
            add_log(aid, f"❌ Upgrade {a_id} spawn failed: {e}", "error")
            return False

        # Record pending upgrade for grace period verification
        state["pending_upgrades"][a_id] = {
            "applied_at": time.time(),
            "fitness_before": current_fitness,
            "code_backup": backup,
        }
        gen = state["generation_map"].get(a_id, 0) + 1
        state["generation_map"][a_id] = gen
        state["total_upgrades"] += 1

        log_evolution(a_id, "upgrade",
                      f"Gen {gen-1}→{gen} | fitness {current_fitness:.3f} → (pending verification)",
                      before=current_fitness)

        return True

    # ── Rollback ──────────────────────────────────────────────────────────
    def rollback_upgrade(a_id, reason):
        """Restore agent to previous version."""
        pending = state["pending_upgrades"].get(a_id, {})
        backup = pending.get("code_backup") or state["code_backups"].get(a_id)
        if not backup:
            add_log(aid, f"⚠️ Cannot rollback {a_id} — no backup code", "warn")
            return False

        agent_file = f"{_cwd}/agents/{a_id}.py"
        try:
            with open(agent_file, "w") as f:
                f.write(backup)
        except Exception:
            return False

        # Re-deploy old code
        try:
            import importlib.util as _ilu
            spec = _ilu.spec_from_file_location(a_id, agent_file)
            mod = _ilu.module_from_spec(spec)
            spec.loader.exec_module(mod)
            # Find code var
            code_var = f"{a_id.upper()}_CODE"
            agent_code = getattr(mod, code_var, None)
            if not agent_code:
                for attr in dir(mod):
                    if attr.endswith("_CODE") and isinstance(getattr(mod, attr), str):
                        agent_code = getattr(mod, attr)
                        break
            if agent_code:
                with lock:
                    agent_meta = dict(agents.get(a_id, {}))
                _stop_ev(a_id).set()
                time.sleep(3)
                _do_spawn_agent({
                    "agent_id": a_id,
                    "code": agent_code,
                    "name": agent_meta.get("name", a_id),
                    "role": agent_meta.get("role", "Rolled-back Agent"),
                    "emoji": agent_meta.get("emoji", "🤖"),
                    "color": agent_meta.get("color", "#888"),
                })
        except Exception as e:
            add_log(aid, f"❌ Rollback spawn failed for {a_id}: {e}", "error")
            return False

        gen = state["generation_map"].get(a_id, 1)
        state["generation_map"][a_id] = max(0, gen - 1)
        state["total_rollbacks"] += 1
        state["pending_upgrades"].pop(a_id, None)

        log_evolution(a_id, "rollback", f"Gen {gen}→{gen-1} | reason: {reason}",
                      before=pending.get("fitness_before", 0))

        add_log(aid, f"⏪ Rolled back {a_id} to gen {gen-1}: {reason}", "warn")
        return True

    # ── Verify Pending Upgrades ───────────────────────────────────────────
    def verify_pending(scores):
        """Check if pending upgrades improved fitness. Rollback if worse."""
        now = time.time()
        to_remove = []
        for a_id, pending in state["pending_upgrades"].items():
            elapsed = now - pending.get("applied_at", now)
            if elapsed < GRACE_PERIOD:
                continue  # still in grace period

            old_fitness = pending.get("fitness_before", 0)
            new_fitness = scores.get(a_id, {}).get("fitness", 0)

            if new_fitness < old_fitness - 0.05:
                # Regression — rollback
                rollback_upgrade(a_id, f"fitness dropped {old_fitness:.3f}→{new_fitness:.3f}")
                state["upgrade_history"].append({
                    "agent": a_id,
                    "gen": state["generation_map"].get(a_id, 0),
                    "fitness_before": old_fitness,
                    "fitness_after": new_fitness,
                    "ts": datetime.now().isoformat(),
                    "outcome": "rolled_back",
                })
            else:
                # Improvement or stable — keep it
                improvement = new_fitness - old_fitness
                state["total_improvements"] += 1
                state["upgrade_history"].append({
                    "agent": a_id,
                    "gen": state["generation_map"].get(a_id, 0),
                    "fitness_before": old_fitness,
                    "fitness_after": new_fitness,
                    "ts": datetime.now().isoformat(),
                    "outcome": "kept" if improvement >= 0 else "marginal",
                })
                log_evolution(a_id, "verified",
                              f"Gen {state['generation_map'].get(a_id,0)} confirmed | "
                              f"fitness {old_fitness:.3f}→{new_fitness:.3f} (+{improvement:.3f})",
                              before=old_fitness, after=new_fitness)
                add_log(aid, f"✅ Evolution verified: {a_id} fitness {old_fitness:.3f}→{new_fitness:.3f}", "ok")

            to_remove.append(a_id)

        for a_id in to_remove:
            state["pending_upgrades"].pop(a_id, None)

    # ── Server start time (for uptime calc) ──────────────────────────────
    _SERVER_START = _SERVER_START_TIME if "_SERVER_START_TIME" in dir() or "_SERVER_START_TIME" in globals() else time.time()

    # ══════════════════════════════════════════════════════════════════════
    # MAIN EVOLUTION LOOP
    # ══════════════════════════════════════════════════════════════════════
    cycle = 0
    set_agent(aid, status="active", progress=10, task="Evolution engine ready — first eval in 60s")

    # Wait for system to stabilise before first evaluation
    agent_sleep(aid, 60)

    while True:
        if agent_should_stop(aid):
            set_agent(aid, status="idle", task="Stopped")
            _save(state)
            agent_sleep(aid, 2)
            continue

        try:
            cycle += 1
            state["total_evaluations"] += 1
            set_agent(aid, status="active", progress=20,
                      task=f"Cycle #{cycle} — evaluating fleet fitness…")

            # ── STEP 1: EVALUATE ──────────────────────────────────────────
            scores = evaluate_all()
            if not scores:
                set_agent(aid, status="active", progress=10,
                          task=f"Cycle #{cycle} — no agents to evaluate")
                agent_sleep(aid, EVAL_INTERVAL)
                continue

            # Summary stats
            avg_fitness = sum(s.get("fitness", 0) for s in scores.values()) / max(1, len(scores))
            low_count = sum(1 for s in scores.values() if s.get("fitness", 0) < 0.5)
            error_count = sum(1 for s in scores.values() if s.get("status") == "error")

            set_agent(aid, progress=40,
                      task=f"Cycle #{cycle} — fleet avg fitness: {avg_fitness:.2f} | "
                           f"{low_count} underperformers | {error_count} errors | "
                           f"gen upgrades: {state['total_upgrades']}")

            # ── STEP 2: VERIFY pending upgrades ───────────────────────────
            verify_pending(scores)

            # ── STEP 3: SELECT underperformers for upgrade ────────────────
            # Skip if we've hit the upgrade cap or have too many pending
            active_pending = len(state["pending_upgrades"])
            if state["total_upgrades"] >= EVOLUTION_CAP:
                set_agent(aid, progress=90,
                          task=f"Cycle #{cycle} — evolution cap reached ({EVOLUTION_CAP} upgrades)")
                _save(state)
                agent_sleep(aid, EVAL_INTERVAL)
                continue

            if active_pending >= MAX_CONCURRENT:
                set_agent(aid, progress=60,
                          task=f"Cycle #{cycle} — {active_pending} upgrades pending verification")
                _save(state)
                agent_sleep(aid, EVAL_INTERVAL)
                continue

            # Find bottom performers (fitness < 0.5, not protected, not already pending)
            candidates = [
                (a_id, s) for a_id, s in scores.items()
                if s.get("fitness", 1) < 0.5
                and a_id not in PROTECTED
                and a_id not in state["pending_upgrades"]
                and s.get("status") != "starting"
            ]
            candidates.sort(key=lambda x: x[1].get("fitness", 0))

            # Take up to MAX_CONCURRENT - active_pending
            slots = MAX_CONCURRENT - active_pending
            targets = candidates[:slots]

            if not targets:
                fleet_status = f"healthy (avg {avg_fitness:.2f})" if avg_fitness >= 0.6 else f"stable (avg {avg_fitness:.2f})"
                set_agent(aid, progress=90,
                          task=f"Cycle #{cycle} — fleet {fleet_status} | "
                               f"{state['total_upgrades']} upgrades | "
                               f"{state['total_improvements']} improvements | "
                               f"{state['total_rollbacks']} rollbacks")
                _save(state)
                agent_sleep(aid, EVAL_INTERVAL)
                continue

            # ── STEP 4: PROPOSE + APPLY upgrades ─────────────────────────
            for target_id, target_scores in targets:
                current_fitness = target_scores.get("fitness", 0)
                set_agent(aid, progress=60,
                          task=f"Cycle #{cycle} — evolving {target_id} (fitness {current_fitness:.3f})…")

                new_code = propose_upgrade(target_id, current_fitness, scores)
                if not new_code:
                    add_log(aid, f"⚠️ No upgrade proposal for {target_id} — skipping", "warn")
                    continue

                success = apply_upgrade(target_id, new_code, current_fitness)
                if success:
                    add_log(aid, f"🧬 Deployed evolution for {target_id} — "
                                 f"gen {state['generation_map'].get(target_id, 0)} "
                                 f"(grace period: {GRACE_PERIOD}s)", "ok")

            # ── STEP 5: Update status ────────────────────────────────────
            set_agent(aid, progress=95,
                      task=f"Cycle #{cycle} — fleet avg {avg_fitness:.2f} | "
                           f"upgrades: {state['total_upgrades']} | "
                           f"improvements: {state['total_improvements']} | "
                           f"rollbacks: {state['total_rollbacks']} | "
                           f"pending: {len(state['pending_upgrades'])}")

            _save(state)

        except Exception as e:
            add_log(aid, f"Evolution error: {e}", "error")
            set_agent(aid, status="active", progress=10,
                      task=f"Cycle #{cycle} — error: {str(e)[:80]}")
            traceback.print_exc()

        agent_sleep(aid, EVAL_INTERVAL)
'''
