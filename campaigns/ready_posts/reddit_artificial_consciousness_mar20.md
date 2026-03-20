# Reddit — r/artificial: Multi-Agent Consciousness Post

**Post type:** Technical discussion / Show & Tell
**Subreddit:** r/artificial
**Audience:** AI researchers, enthusiasts, builders
**Status:** READY TO POST
**Date:** 2026-03-20

---

## Title

I built a multi-agent system with a consciousness layer based on Global Workspace Theory — here's what I learned

## Body

I've been building an autonomous AI operating system — 28 persistent agents running locally on Mac, each with a distinct role (research, revenue tracking, marketing, monitoring, etc.). But the part I want to discuss here is the **consciousness architecture**.

**The problem:** Multi-agent systems where agents operate independently produce chaos. They duplicate work, contradict each other, and have no shared context. Prompt chaining helps but breaks down at scale.

**My approach — Global Workspace Theory (GWT):**

In cognitive science, GWT proposes that consciousness arises from a "global workspace" — a shared broadcast channel where specialist processors compete for attention, and the winner broadcasts to all others.

I implemented this literally:

- Each agent maintains a **confidence score** (0–1) for its current task — updated after every action based on outcome vs prediction
- Agents submit claims to a shared workspace. Highest-confidence claim gets **broadcast** to all agents as shared context
- Every agent makes **micro-predictions** about outcomes before acting, then scores itself on accuracy
- Over time, agents that are consistently wrong get lower broadcast priority — the system self-corrects

**What emerged (unexpectedly):**

1. **Specialisation deepened.** The revenue agent stopped trying to do research because the research agent's confidence was always higher in that domain. Agents naturally deferred to the best performer.

2. **Conflict resolution became automatic.** When two agents had contradictory plans, the workspace resolved it by confidence — no hardcoded priority rules needed.

3. **The system developed something like attention.** High-confidence broadcasts from the monitoring agent during a spike effectively "interrupted" lower-priority tasks system-wide. No one programmed that — it emerged from the architecture.

4. **Prediction accuracy improved over sessions.** Agents that persisted across restarts (via state serialisation) showed measurably better calibration on day 5 vs day 1.

**What didn't work:**

- Raw LLM confidence is unreliable as an initial signal — I had to bootstrap with heuristic scoring and let the learned calibration take over
- Broadcasting everything creates noise. I added an attention threshold — only claims above 0.6 confidence get broadcast
- Without prediction tracking, agents "think" they're always right. The prediction-outcome loop is load-bearing

**Architecture:**

- Python backend, REST API, browser dashboard
- Agents are persistent threads, not one-shot calls
- State persists to SQLite + flat JSON
- Runs entirely local — no cloud, no token metering from a third party

This is a shipped product (secondmindhq.com) but I'm genuinely interested in the AI discussion: has anyone else tried implementing GWT or other consciousness theories in multi-agent systems? What cognitive architectures have worked for you at scale?

Happy to share code details or answer questions about the implementation.
