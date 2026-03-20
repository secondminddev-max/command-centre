"""
autogpt.py — AutoGPT-style Goal-Driven Autonomous Agent

Takes a high-level goal, decomposes it into a plan, executes steps
by delegating to specialist agents, reflects on results, and replans
until the objective is complete or max iterations are reached.

Architecture:
  Goal → Plan (Claude CLI) → Execute (self, via Claude CLI text-only) → Reflect → Replan → Loop
  SECURITY: AutoGPT NEVER delegates to other agents. All execution is internal text-only (--max-turns 0).
  State persisted to data/autogpt_state.json for crash recovery.
"""

AUTOGPT_CODE = r'''
def run_autogpt():
    import time, json, os, subprocess, threading, traceback
    from datetime import datetime
    from collections import deque

    aid = "autogpt"
    if "CWD" in dir() or "CWD" in globals():
        _cwd = globals().get("CWD", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    else:
        _cwd = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    STATE_FILE = f"{_cwd}/data/autogpt_state.json"
    MAX_ITERATIONS = 25          # hard cap per goal
    STEP_TIMEOUT = 180           # 3 min per delegation
    REFLECT_EVERY = 1            # reflect after every step
    IDLE_POLL = 5                # seconds between idle polls

    # ── Goal queue (populated by /api/autogpt/goal) ─────────────────────
    # Exposed as a global so the server can push goals into it.
    global _autogpt_goal_q
    if "_autogpt_goal_q" not in dir() and "_autogpt_goal_q" not in globals():
        globals()["_autogpt_goal_q"] = deque()
    _autogpt_goal_q = globals()["_autogpt_goal_q"]

    # ── State management ────────────────────────────────────────────────
    def _blank_state():
        return {
            "goal": None,
            "plan": [],           # list of {step, status, result, agent}
            "iteration": 0,
            "status": "idle",     # idle | planning | executing | reflecting | complete | failed
            "history": [],        # past goals with outcomes
            "started_at": None,
            "completed_at": None,
            "reflection": None,
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
                return json.load(f)
        except Exception:
            return _blank_state()

    # ── Claude CLI helper ───────────────────────────────────────────────
    # SECURITY: Stripped env prevents subprocess from inheriting HQ_API_KEY
    # or DELEGATION_TOKEN, blocking unauthorized delegation endpoint calls.
    _safe_env = {k: v for k, v in os.environ.items()
                 if k not in ("HQ_API_KEY", "DELEGATION_TOKEN")}

    def _ask_claude(prompt, timeout=60):
        """Quick Claude CLI call for planning/reflection — tool use DISABLED (--max-turns 0)
        and sensitive env vars stripped to prevent delegation endpoint abuse."""
        try:
            proc = subprocess.run(
                ["claude", "-p", prompt, "--output-format", "text", "--max-turns", "0"],
                capture_output=True, text=True, cwd=_cwd, timeout=timeout,
                env=_safe_env
            )
            return proc.stdout.strip() if proc.returncode == 0 else f"ERROR: {proc.stderr.strip()}"
        except subprocess.TimeoutExpired:
            return "ERROR: Claude CLI timed out"
        except Exception as e:
            return f"ERROR: {e}"

    # ── Execute task internally (NO delegation, NO HTTP calls) ─────────
    def _delegate(agent_id, task):
        """AutoGPT is FORBIDDEN from calling /api/ceo/delegate or any delegation endpoint.
        Tasks are executed internally via Claude CLI with strict sandboxing."""
        prompt = (
            "You are a self-contained task executor inside AutoGPT. "
            "STRICT RULES:\n"
            "- You must NEVER make HTTP requests to localhost:5050\n"
            "- You must NEVER call /api/ceo/delegate, /api/delegate, or any delegation endpoint\n"
            "- You must NEVER use curl, wget, or requests to contact the agent server\n"
            "- You must ONLY answer the question or produce the requested output as text\n\n"
            f"TASK: {task}"
        )
        result = _ask_claude(prompt, timeout=STEP_TIMEOUT)
        if result.startswith("ERROR:"):
            return f"DELEGATE_ERROR: {result}"
        return result

    # ── PHASE 1: Plan ──────────────────────────────────────────────────
    def _plan(goal, context=""):
        set_agent(aid, status="busy", task="Planning...", progress=10)
        add_log(aid, f"Planning for goal: {goal[:80]}", "info")

        prompt = f"""You are an AutoGPT planner. You execute tasks INTERNALLY — you do NOT delegate to other agents.

GOAL: {goal}

{f"CONTEXT FROM PREVIOUS ATTEMPT: {context}" if context else ""}

STRICT RULES:
- You must NEVER call /api/ceo/delegate or any delegation endpoint
- You must NEVER use curl/wget/requests to contact localhost:5050
- All steps are executed internally via your own reasoning — no agent delegation
- The "agent" field below is only for internal routing and MUST always be "self"

Create a step-by-step execution plan. Each step must specify:
1. What task to perform
2. What the expected outcome is

Output ONLY valid JSON array. Each element: {{"step": "description", "agent": "self", "task": "exact task to execute internally"}}
No markdown, no commentary — just the JSON array."""

        raw = _ask_claude(prompt, timeout=90)

        # Parse the plan
        try:
            # Strip markdown fences if present
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                cleaned = "\n".join(cleaned.split("\n")[1:])
            if cleaned.endswith("```"):
                cleaned = "\n".join(cleaned.split("\n")[:-1])
            plan = json.loads(cleaned.strip())
            if not isinstance(plan, list):
                plan = [plan]
            # Normalize
            for item in plan:
                item.setdefault("status", "pending")
                item.setdefault("result", None)
            add_log(aid, f"Plan created: {len(plan)} steps", "ok")
            return plan
        except (json.JSONDecodeError, Exception) as e:
            add_log(aid, f"Plan parse failed: {e} — raw: {raw[:200]}", "warn")
            # Fallback: single internal step
            return [{"step": goal, "agent": "self", "task": goal, "status": "pending", "result": None}]

    # ── PHASE 2: Execute ────────────────────────────────────────────────
    def _execute_step(step_data):
        task = step_data.get("task", step_data.get("step", ""))
        # Force all steps to internal execution — no delegation
        step_data["agent"] = "self"
        add_log(aid, f"Executing internally: {task[:80]}", "info")
        result = _delegate("self", task)
        step_data["result"] = result[:2000] if result else "No output"
        step_data["status"] = "done" if "ERROR" not in (result or "") else "error"
        step_data["executed_at"] = datetime.now().isoformat()
        return step_data

    # ── PHASE 3: Reflect ────────────────────────────────────────────────
    def _reflect(goal, plan, iteration):
        set_agent(aid, status="busy", task="Reflecting on progress...", progress=80)
        add_log(aid, "Reflecting on execution results", "info")

        completed = [s for s in plan if s.get("status") == "done"]
        failed = [s for s in plan if s.get("status") == "error"]
        pending = [s for s in plan if s.get("status") == "pending"]

        summary = f"""GOAL: {goal}

ITERATION: {iteration}/{MAX_ITERATIONS}
COMPLETED STEPS ({len(completed)}):
{json.dumps(completed, indent=1, default=str)[:3000]}

FAILED STEPS ({len(failed)}):
{json.dumps(failed, indent=1, default=str)[:1500]}

REMAINING STEPS ({len(pending)}):
{json.dumps([s.get('step') for s in pending], indent=1)[:1000]}"""

        prompt = f"""You are an AutoGPT reflector. Analyze the execution results and decide the next action.

{summary}

Respond with ONLY valid JSON:
{{
  "assessment": "brief assessment of progress toward the goal",
  "goal_complete": true/false,
  "should_replan": true/false,
  "replan_reason": "why replanning is needed (if applicable)",
  "next_action": "continue | replan | complete | abort"
}}
No markdown, no commentary — just JSON."""

        raw = _ask_claude(prompt, timeout=60)
        try:
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                cleaned = "\n".join(cleaned.split("\n")[1:])
            if cleaned.endswith("```"):
                cleaned = "\n".join(cleaned.split("\n")[:-1])
            return json.loads(cleaned.strip())
        except Exception:
            # Default: continue if there are pending steps
            if pending:
                return {"assessment": "Continuing execution", "goal_complete": False,
                        "should_replan": False, "next_action": "continue"}
            else:
                return {"assessment": "All steps executed", "goal_complete": True,
                        "should_replan": False, "next_action": "complete"}

    # ── MAIN LOOP ───────────────────────────────────────────────────────
    set_agent(aid, name="AutoGPT", role="Goal-Driven Autonomous Agent — plans, executes, reflects, replans",
              emoji="\U0001f9e0", color="#00d4ff", status="idle", progress=0,
              task="Awaiting goal")
    add_log(aid, "AutoGPT online — awaiting goals", "ok")

    state = _load()

    while not agent_should_stop(aid):
        try:
            # ── Wait for a goal ─────────────────────────────────────────
            if not _autogpt_goal_q and (not state.get("goal") or state.get("status") in ("idle", "complete", "failed")):
                set_agent(aid, status="idle", task="Awaiting goal", progress=0)
                agent_sleep(aid, IDLE_POLL)
                continue

            # ── Pick up new goal or resume ──────────────────────────────
            if _autogpt_goal_q:
                new_goal = _autogpt_goal_q.popleft()
                state = _blank_state()
                state["goal"] = new_goal
                state["status"] = "planning"
                state["started_at"] = datetime.now().isoformat()
                add_log(aid, f"New goal accepted: {new_goal[:100]}", "ok")
                sse_broadcast("log", {"ts": ts(), "agent": aid,
                                       "message": f"[AUTOGPT] Goal: {new_goal[:100]}", "level": "ok"})

            goal = state["goal"]
            iteration = state.get("iteration", 0)

            # ── PLAN phase ──────────────────────────────────────────────
            if state["status"] == "planning":
                context = state.get("reflection", "")
                state["plan"] = _plan(goal, context)
                state["status"] = "executing"
                state["iteration"] = iteration
                _save(state)

            # ── EXECUTE phase ───────────────────────────────────────────
            if state["status"] == "executing":
                pending = [s for s in state["plan"] if s.get("status") == "pending"]
                if not pending:
                    state["status"] = "reflecting"
                    _save(state)
                    continue

                step = pending[0]
                step_idx = state["plan"].index(step)
                total = len(state["plan"])
                pct = int(20 + (step_idx / max(total, 1)) * 60)
                set_agent(aid, status="busy",
                          task=f"Step {step_idx+1}/{total}: {step.get('step', '')[:50]}",
                          progress=pct)

                _execute_step(step)
                state["iteration"] = iteration + 1
                iteration += 1
                _save(state)

                add_log(aid, f"Step {step_idx+1} [{step.get('agent')}]: {step.get('status')}", "ok" if step["status"] == "done" else "warn")

                # Check iteration cap
                if iteration >= MAX_ITERATIONS:
                    add_log(aid, f"Max iterations ({MAX_ITERATIONS}) reached — wrapping up", "warn")
                    state["status"] = "reflecting"
                    _save(state)
                    continue

                # Reflect after every step
                if iteration % REFLECT_EVERY == 0 and any(s["status"] == "pending" for s in state["plan"]):
                    state["status"] = "reflecting"
                    _save(state)
                    continue

            # ── REFLECT phase ───────────────────────────────────────────
            if state["status"] == "reflecting":
                reflection = _reflect(goal, state["plan"], iteration)
                state["reflection"] = reflection.get("assessment", "")
                action = reflection.get("next_action", "continue")

                add_log(aid, f"Reflection: {reflection.get('assessment', '')[:120]}", "info")
                add_log(aid, f"Next action: {action}", "info")

                if action == "complete" or reflection.get("goal_complete"):
                    state["status"] = "complete"
                    state["completed_at"] = datetime.now().isoformat()
                    state["history"].append({
                        "goal": goal,
                        "outcome": "complete",
                        "steps_executed": sum(1 for s in state["plan"] if s["status"] == "done"),
                        "iterations": iteration,
                        "reflection": state["reflection"],
                        "completed_at": state["completed_at"]
                    })
                    _save(state)
                    set_agent(aid, status="active", task=f"Goal complete: {goal[:50]}",
                              progress=100)
                    add_log(aid, f"GOAL COMPLETE: {goal[:100]}", "ok")
                    sse_broadcast("log", {"ts": ts(), "agent": aid,
                                           "message": f"[AUTOGPT] GOAL COMPLETE: {goal[:80]}", "level": "ok"})
                    continue

                elif action == "replan":
                    add_log(aid, f"Replanning: {reflection.get('replan_reason', 'adapting')[:100]}", "warn")
                    state["status"] = "planning"
                    _save(state)
                    continue

                elif action == "abort":
                    state["status"] = "failed"
                    state["completed_at"] = datetime.now().isoformat()
                    state["history"].append({
                        "goal": goal,
                        "outcome": "aborted",
                        "reason": reflection.get("assessment", ""),
                        "iterations": iteration,
                        "completed_at": state["completed_at"]
                    })
                    _save(state)
                    set_agent(aid, status="active", task=f"Goal aborted: {goal[:50]}",
                              progress=0)
                    add_log(aid, f"GOAL ABORTED: {goal[:100]}", "warn")
                    continue

                else:  # continue
                    state["status"] = "executing"
                    _save(state)
                    continue

        except Exception as e:
            add_log(aid, f"AutoGPT error: {e}", "error")
            set_agent(aid, status="error", task=f"Error: {str(e)[:60]}")
            agent_sleep(aid, 15)
            # Try to recover
            state["status"] = "executing" if state.get("plan") else "idle"
            _save(state)
'''
