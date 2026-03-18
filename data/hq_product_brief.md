# Command Centre (HQ)
### Autonomous Multi-Agent OS for Mac

---

## What It Is

**Command Centre** is a locally-run, autonomous agent operating system for Mac. It runs a persistent swarm of AI agents — each with a distinct role and personality — that self-organise, self-monitor, and actively pursue revenue goals on your behalf.

You open HQ and see your business running. Agents are visible on a live office-floor dashboard: the CEO orchestrates, the Researcher hunts intelligence, the Designer produces, the Marketer posts, the Accountant tracks funds. When agents are idle, they rest in the Bed Bay. When they're working, you watch it happen in real time.

HQ is not a chatbot. It is an operating system for a one-person company.

**Core capabilities:**
- Persistent agents that run between sessions — not one-shot prompts
- Live visual dashboard (office floor) showing agent status, chat, and activity
- Revenue tools baked in: Stripe payments, Bluesky social, email via SendGrid
- Market screeners, web research, product briefs — generated autonomously
- Treasury & Vault for secure credential and fund management
- Silent Query / Observer Mode — ask what's happening without interrupting agents
- Mac-native, no cloud dependency, no subscription lock-in for the runtime

---

## Target Customer

**Indie hackers, solopreneurs, and AI-native founders** who want to run a self-operating micro-business without a team.

- Building side projects and info products solo
- Spending too much time on research, content, and admin
- Already comfortable with APIs and local tools
- Want leverage — not just another AI assistant, but an agent workforce

Secondary: early-stage startup founders who want to automate their go-to-market before hiring.

---

## Pricing

| Tier | Price | What's Included |
|---|---|---|
| **Free / Open Source** | $0 | Core agent runtime, dashboard, 3 base agents, local only |
| **Pro** | $49/mo | Unlimited agents, revenue tools (Stripe, Bluesky, email), screeners, Spirit Guide, priority updates |
| **Lifetime Pro** | $299 once | Everything in Pro, forever — ideal for indie hackers who hate subscriptions |

Hosted/managed version (no local setup) at a premium tier is the long-term SaaS play.

---

## Go-To-Market

**Phase 1 — Open Source Launch**
Publish on GitHub. Target Hacker News, r/MacApps, r/SideProject, and the indie hacker community. Open source builds trust, drives installs, and surfaces power users.

**Phase 2 — Pro Tier & Paid Reports**
Gate revenue tools behind Pro. Ship pre-built agent workflows as downloadable products (e.g. ASX Screener Report, $9). Agents market themselves — every Bluesky post, every campaign is a demo of what HQ can do.

**Phase 3 — Managed Cloud**
Offer a hosted version for users who can't run locally. Monthly SaaS model. Agents run in the cloud, dashboard in the browser. This is the scalable revenue layer.

---

## Key Differentiators

| Feature | HQ | AutoGPT | CrewAI | AgentGPT |
|---|---|---|---|---|
| Persistent agents (survives restarts) | ✅ | ❌ | ❌ | ❌ |
| Visual office-floor dashboard | ✅ | ❌ | ❌ | ❌ |
| Agent personalities & roles | ✅ | ❌ | Partial | ❌ |
| Real revenue tools (Stripe, Bluesky) | ✅ | ❌ | ❌ | ❌ |
| Mac-native, fully local | ✅ | ❌ | ❌ | ❌ |
| Treasury / Vault (secure credentials) | ✅ | ❌ | ❌ | ❌ |
| Operator model (CEO orchestrates swarm) | ✅ | Partial | Partial | ❌ |
| No cloud dependency | ✅ | ❌ | ❌ | ❌ |

HQ is the only agent system designed to **run a business**, not just complete tasks. The dashboard makes it legible. The revenue tools make it real. The persistence makes it a platform, not a script.

---

## The One-Line Pitch

> *"Your business, running itself — agents that research, post, earn, and report while you sleep."*

---

*Command Centre — HQ v1.0 | Product Brief — March 2026*

---

## Installation Friction Analysis

### Deployment Paths

#### 1. Docker (Developer Path)
**Target user:** Developers and technical users comfortable with the command line and containerised environments.
**Friction score:** Medium
**Setup steps summary:** Install Docker Desktop, clone the HQ repository, run `docker compose up`. Requires familiarity with terminal usage and port configuration. Estimated time: ~5 minutes for an experienced developer. Full agent stack launches inside an isolated container — clean teardown, no system pollution.

#### 2. Native Installer / DMG (Non-Technical User Path)
**Target user:** Solopreneurs, indie hackers, and founders who want a Mac-native experience without touching a terminal.
**Friction score:** Low
**Setup steps summary:** Download the `.dmg`, drag HQ to `/Applications`, launch. macOS Gatekeeper approval required on first run (standard for unsigned apps). No CLI, no dependencies, no environment setup. Estimated effort: low — comparable to installing any desktop app. API keys entered via the in-app settings panel.

#### 3. Cloud-Hosted SaaS (Zero-Setup Path)
**Target user:** Non-technical users, first-time evaluators, and anyone unwilling or unable to run software locally.
**Friction score:** Low
**Setup steps summary:** Sign up via browser, authenticate, and the full HQ dashboard loads immediately. No download, no installation, no system requirements. Agents run server-side. API keys stored in encrypted vault. Access from any device. Premium tier — monthly subscription unlocks full agent roster and revenue tools.

---

### Recommended Onboarding Path for Non-Technical Users

For users without a technical background, the **cloud-hosted SaaS path is the recommended default**. It eliminates every installation step — no downloads, no terminal commands, no dependency management. Users sign up, authenticate, and land directly in the HQ dashboard with agents ready to deploy. For those who prefer a locally-installed experience but want to avoid the command line, the **native DMG installer is the recommended fallback**: download, drag, launch, and configure API keys in-app. Docker is reserved for power users and developers who want full control over their environment, custom networking, or integration into existing containerised workflows.

---

### Deployment Path Summary

| Path | Target User | Friction | Setup Time | Key Requirement |
|---|---|---|---|---|
| **Docker** | Developers / power users | Medium | ~5 min | Docker Desktop installed |
| **Native DMG** | Non-technical Mac users | Low | ~2 min | macOS 12+ |
| **Cloud SaaS** | Everyone / zero-setup | Low | ~1 min | Browser + internet |
