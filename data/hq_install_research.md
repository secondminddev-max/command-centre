# HQ Command Centre — Non-Technical Install Research

**Prepared by:** Reforger (System Engineer)
**Date:** 2026-03-17
**Scope:** Packaging and distribution strategies for a self-hosted AI agent system (Python + Flask API + 27 agents + web UI) targeting non-technical Mac users.

---

## 1. Packaging Approaches Comparison

| Approach | Install Ease (non-technical) | Maintenance Burden | Cost | Technical Complexity | HQ Suitability |
|---|---|---|---|---|---|
| Docker + docker-compose | Medium — needs Docker Desktop first | Low | Free (self-hosted) | Low–Medium | **High** — best near-term path |
| Electron desktop wrapper | High — standard .app drag-and-drop | Very High | Free + build infra | Very High | Medium — long-term target only |
| Cloud-hosted demo instances | Very High — just a URL | Low for user; High for operator | $10–20/month | Low | Medium — demos and top-of-funnel |
| Installer scripts (Homebrew/curl) | Low–Medium — requires Terminal | Medium | Free | Medium | Low — developer-only path |
| PyInstaller / py2app .app | High if it works; often doesn't | Very High — brittle | Free + CI pipeline | Very High | Low — avoid for now |

### Docker + docker-compose

A single `docker-compose up` can launch the Flask API, all 27 agents, and serve the web UI. Docker Desktop has become a standard tool even for semi-technical users — it has a GUI, auto-updates, and 80%+ brand recognition in the startup/operator segment. The main friction is the initial Docker Desktop download (~500 MB) and the conceptual hurdle of "what is a container." Once past that, updates are trivial (`docker compose pull && docker compose up -d`) and the system restarts automatically. HQ's multi-agent architecture maps naturally to compose services. Volumes handle data persistence between restarts.

HQ currently runs as a single `agent_server.py` process with SQLite and a built-in HTTP server — a single-service `docker-compose.yml` can wrap this immediately. Adding a second service for the dashboard (if ever split) is straightforward. **Best match for HQ's current architecture.**

### Electron desktop wrapper

Electron bundles Chromium + Node.js into a `.app`. Wrapping a Python backend requires either PyInstaller (a frozen Python subprocess), a bundled Python binary via `electron-builder`, or a sidecar approach. The end result is the most native-feeling install — menu bar icon, no visible terminal, system tray status. The engineering cost is substantial: a separate Python bundle, a Node/Electron shell, keeping them synchronized across macOS arm64 and x86\_64, code signing, Apple notarization ($99/year Apple Developer account), and a full CI/CD pipeline for multi-platform builds.

Every Python dependency update forces a full app rebuild and re-distribution. Auto-update infrastructure (Sparkle for macOS) adds further complexity. **Appropriate only once HQ has the revenue and stability to justify this investment.** The right model to study: Ollama's macOS app — but Ollama chose Go specifically to avoid the Python bundling problem.

### Cloud-hosted demo instances (Railway, Render, Fly.io, DigitalOcean App Platform)

| Platform | Deploy DX | Cost (small) | Persistent Storage | Best For |
|---|---|---|---|---|
| Railway | Excellent | ~$5–10/month + usage | Volumes | GitHub push-to-deploy |
| Render | Excellent | $7/month starter | Disks | Predictable pricing, Heroku-like DX |
| Fly.io | Moderate | ~$3–8/month | Volumes | Global edge, Docker-native |
| DigitalOcean App Platform | Good | $12/month | Managed DBs | Teams wanting managed Postgres alongside |

Zero install for the evaluator — just a URL. Ideal for demos, trials, and non-technical stakeholders. The hard constraint: HQ's API keys (Anthropic, Stripe, Bluesky) are per-user secrets that cannot be bundled into a shared instance without serious privacy and cost issues. Each user needs an isolated deployment, which turns this into an operational managed-SaaS problem. The "Deploy to Railway" README button is a useful middle path — one-click for the user, isolated for each deployment.

**Use case:** non-technical evaluators and sales demos. Not a viable primary self-hosted path without per-user isolation infrastructure.

### Installer scripts (Homebrew formula / curl-pipe-bash / Makefile)

`brew install secondmind/hq/hq` or `curl -fsSL install.hq.ai | bash` can automate Python venv creation, pip dependency install, `.env` scaffolding, and a launchd plist for auto-start on login. A private Homebrew tap (`brew tap secondmind/hq`) can be published immediately — no need to meet Homebrew core's 300+ stars requirement. Homebrew is the trusted macOS developer channel.

Weaknesses: Python version conflicts (`3.10` vs `3.12`), pip dependency resolution failures, and the requirement for the user to open a terminal at all. Non-technical users bounce off terminal error messages immediately. `curl | bash` also carries inherent security optics (executing remote code without inspection). **Developer and power-user path — secondary distribution channel.**

### PyInstaller / py2app .app bundle

Freezes the entire CPython interpreter and all pip dependencies into a self-contained `.app` bundle. User double-clicks — no terminal, no Docker, no environment variables visible. Sounds ideal. The reality is brutal: PyInstaller and py2app struggle with dynamic imports (common in Flask plugin loading and agent initialization patterns), produce 300–800 MB bundles, and break unpredictably when dependencies include compiled C extensions. ChromaDB (present in HQ's stack) and SQLAlchemy with native drivers routinely fail in frozen environments. Every update requires a full rebuild, re-signing, re-notarization cycle.

This is a full-time maintenance job for a project under active development. **Avoid until the stack is locked and stable.**

---

## 2. Prior Art — How Others Solved This

**Ollama — Mac app with menu bar, one-click install**
The gold standard for non-technical local AI on Mac. Ships as a native `.app` — download `.dmg`, drag to Applications, done. A menu bar icon provides status and model management. Under the hood it is a single Go binary with zero runtime dependencies. No Python, no pip, no venv — Go's static compilation eliminates the dependency problem entirely. The web UI (Open WebUI) is a separate project. Key UX moves that HQ can adopt regardless of language: menu bar status indicator, single-click to open dashboard, auto-configure PATH on first launch, no terminal interaction required for normal operation.

**n8n — docker-compose or cloud**
`npx n8n` (one command if Node.js installed) or `docker run n8nio/n8n` (single container). Their "self-hosted AI starter kit" bundles Ollama + Qdrant + n8n in one `docker-compose.yml` with sensible defaults — a direct model for HQ's multi-service approach. Non-technical users are explicitly steered to n8n.cloud ($24/month). The dual-path strategy: cloud absorbs non-technical users, Docker serves self-hosters. Default database is SQLite — no Postgres setup step. Key lesson: keep the default stack minimal, have a cloud fallback.

**Flowise — npm install or Docker**
`npx flowise start` (one command if Node.js present) or Docker. Their documentation states directly: *"If you aren't experienced at managing servers and just want to use the webapp, we recommend using Flowise Cloud."* Refreshingly honest about the limits of self-hosting for non-technical users. HQ should adopt the same positioning — lead with a hosted demo option, make self-hosting an advanced path with clear expectations, not the default.

**Dify — Docker Compose, cloud hosted**
`git clone && docker compose up` — but this spawns 12+ containers (Python API, Next.js frontend, Postgres, Redis, Celery workers, Weaviate). Downloads ~3 GB, takes 5–10 minutes on first run. Dify's multi-service compose is the right architecture model for HQ — but it demonstrates the failure mode: too many services creates cognitive overload. Key lesson: resist adding Redis, Postgres, and a vector DB before the install UX is solved. SQLite and a single process is sufficient to get users running. Complexity can be added later as opt-in.

**LocalAI — Docker**
`docker run -p 8080:8080 localai/localai` — single command, single container, no web UI bundled. Users bring their own UI. LocalAI prioritises a drop-in OpenAI API compatibility layer over everything else. The install is as simple as Docker gets precisely because the scope is narrow. Key lesson: if you do one thing simply, the install is easy. Every additional service or agent you ship in the default config adds installation weight.

---

## 3. Biggest Single Barrier for HQ

### API Key Setup and Secret Injection

The #1 installation barrier is not the install itself. It is getting 5–8 required API keys (Anthropic, Stripe, Bluesky credentials, email SMTP, and others) into the running system in a way that:

1. A non-technical user understands what they are being asked to do
2. Keys are stored securely — not in plaintext in a `.env` file the user might accidentally share or lose
3. The system validates keys before agents attempt to use them
4. Missing or invalid keys produce a clear, actionable error — not a cryptic Python traceback or a silently broken agent

**Why this is the hardest problem:**

Every other install barrier has a known engineering solution. Python dependency hell → Docker. Port conflicts → configurable compose ports. Cold start time → loading screen. Dashboard URL → fixed `localhost:5050`.

API key setup requires a guided UX flow that does not exist in standard tooling. The current state for virtually every self-hosted AI tool is: "copy `.env.example` to `.env` and fill in your keys." This is an immediate drop-off point for non-technical users who:

- Do not know what an Anthropic API key is, where it lives, or how to create one
- Do not know what a `.env` file is or how to open and edit one safely
- Cannot distinguish a correctly formatted key from a silently wrong one
- Have no feedback loop to confirm whether HQ actually started correctly

HQ currently loads `.env` on startup via `agent_server.py`. If `.env` is missing or a key is malformed, agents initialize in a degraded state with no visible indication to the user — errors appear in terminal logs that the user is not watching. With 27 agents each potentially depending on different secrets, the cognitive load of manual setup is crushing.

Industry benchmark: ~62% of SaaS users drop off before their first "aha moment." Manual API key setup, with no in-product guidance, is one of the primary causes of that abandonment. It is not a single technical fix — it is a UX/product design problem that cuts across installation, first-run onboarding, and an upstream API dependency HQ cannot control.

---

## 4. Recommended First Step

### Build a Browser-Based Setup Wizard at `/setup` (1–2 days)

Create a first-run guided wizard served at `http://localhost:5050/setup`. When required keys are absent, all routes redirect here. The user configures HQ entirely in the browser — no terminal, no file editing.

**What it does:**

1. **Detects missing secrets** — on startup, `agent_server.py` checks `REQUIRED_KEYS`. If any are absent, redirect all routes to `/setup`.
2. **Step-by-step form** — one key per screen, plain-English explanation of what it is, why HQ needs it, and a direct link to where the user obtains it (e.g. "Get your Anthropic key at console.anthropic.com → API Keys → Create new secret key").
3. **Live validation** — on entry, makes a minimal real API call to confirm the key works before advancing. Catches typos and permission errors immediately, with a human-readable error message.
4. **Writes config automatically** — calls `POST /api/setup/save-config` to write validated keys to `.env`. User never touches a file.
5. **Optional services with "Skip"** — Stripe, email SMTP, and Bluesky are flagged optional. Users get HQ running on just the Anthropic key; other integrations can be configured later from a settings page.
6. **Green light confirmation** — "HQ is ready" screen with a single "Launch HQ" button. No ambiguity about whether it worked.

**Implementation sketch:**

```
agent_server.py
  └─ REQUIRED_KEYS = ["ANTHROPIC_API_KEY"]
  └─ on startup: if any required key missing → all routes → redirect /setup
  └─ GET  /setup                  → serve setup_wizard.html (self-contained, no CDN deps)
  └─ POST /api/setup/validate     → {key_name, value} → live API test → {ok, error}
  └─ POST /api/setup/save-config  → write validated keys to .env
  └─ GET  /api/setup/status       → {configured: bool, missing_keys: [...]}

setup_wizard.html
  └─ Step 1: Welcome + what HQ needs and why
  └─ Step 2: Per-key guided entry (Anthropic required; optional services with Skip)
  └─ Step 3: Live validation result
  └─ Step 4: "HQ is ready — Launch Dashboard"
```

**Bonus quick win (1 hour, not 2 days):** Add `webbrowser.open('http://localhost:5050')` on startup. Removes the port-discovery friction entirely — the user runs the server and the browser opens automatically.

**Why this first:**
- Zero packaging changes required — works today with the existing Flask server
- Works regardless of how HQ was installed (Docker, bare Python, Homebrew, any path)
- Directly addresses the #1 drop-off point without touching infrastructure
- Sets the foundation for extended onboarding (model selection, agent activation, first-task wizard)
- Mirrors what the successful tools do: Flowise, n8n, and Dify all ship in-browser setup flows

---

## 5. Recommended Long-Term Path

### Step 1 — Polish the Docker Experience (Weeks 1–4)

**Goal:** `docker-compose up` → browser opens → setup wizard handles the rest → HQ is live.

- Publish a clean `docker-compose.yml` to the repo root with sensible defaults (port 5050, bind-mounted `data/` for persistence, `restart: unless-stopped`)
- Bundle the setup wizard from Step 4 into the container image — it must work inside Docker
- Ensure the web UI is served from the same container on a fixed, documented port; no separate container required at this stage
- Add a Docker `healthcheck` so Docker Desktop shows green/red status without the user reading logs
- Write a single-page `INSTALL.md`: three steps — "Install Docker Desktop → run this command → open this URL"
- Add `webbrowser.open` equivalent or a Makefile target that opens the browser after compose is up
- Test on a completely clean Mac with zero prior setup, zero existing `.env`, zero developer tools installed

This step opens the self-hosted market to the technically-capable-but-not-developers segment. Completing it gives HQ a credible, reproducible install story that can be linked in documentation and marketing.

### Step 2 — Publish a Cloud Demo Path (Weeks 1–2, can run in parallel)

**Goal:** Non-technical evaluators experience HQ in 60 seconds with no install.

- Deploy HQ to Railway or Render from the main repo; add a "Deploy to Railway" one-click button to the README
- Use the platform's environment variable dashboard for API key injection — no `.env` file editing required
- Scope the demo instance to sandboxed mode: mock Bluesky posts, no real Stripe charges, read-only agent outputs where appropriate
- Add a prominent "Self-host this" CTA in the demo UI linking to the Docker path
- This is the sales and evaluation funnel: non-technical buyers evaluate here, then hand off to a technical team member to self-host

This step captures the non-technical audience for evaluation and revenue without requiring them to install anything. It also provides a shareable URL for demos, marketing posts, and investor conversations.

### Step 3 — Native Mac Menu Bar App (Months 3–6)

**Goal:** Download `.dmg` → drag to Applications → HQ runs as a menu bar app, no Docker Desktop, no terminal, no browser-URL hunting.

- Build a lightweight Swift or Electron menu bar shell that:
  - Launches the Docker compose stack (or a bundled Python process) in the background on login
  - Shows a menu bar icon with live status: green = running, amber = starting, red = error
  - Opens `localhost:5050` in the default browser on click
  - Exposes "Stop HQ", "View logs", and "Check for updates" from the menu
  - Handles `docker compose down` gracefully on quit
- The Python/Flask stack is completely unchanged — the shell is a process manager with a native UX wrapper
- Model directly on Ollama's open-source macOS app: it is a Go binary launcher with a menubar UI, not a bundled runtime
- Distribute via signed `.dmg` on GitHub Releases; plan App Store submission as a stretch goal (sandbox restrictions will require work)
- Requires Apple Developer Program membership ($99/year) for code signing and notarization

At this stage HQ is a genuine consumer-grade product. The install experience is identical to any commercial Mac application.

---

## Summary

| Priority | Action | Effort | Impact |
|---|---|---|---|
| **P0 — Immediate** | Browser-based setup wizard at `/setup` | 1–2 days | Eliminates #1 drop-off; works with all install methods |
| **P0 — Immediate** | Auto-open browser on startup | 1 hour | Removes port-discovery friction |
| **P1 — Short-term** | Clean `docker-compose.yml` + `INSTALL.md` | 1–4 weeks | Opens self-hosted market to non-developer segment |
| **P1 — Short-term** | "Deploy to Railway" cloud demo | 1–2 weeks | Zero-friction evaluation path for non-technical buyers |
| **P2 — Long-term** | Native Mac menu bar app (.dmg) | 3–6 months | True one-click consumer install |

**The correct sequencing: build the setup wizard first.** It benefits every distribution method simultaneously, requires no packaging changes, and directly unblocks users who are trying to install HQ right now.

---

*Document owner: Reforger | Last updated: 2026-03-17 | Next review: when packaging work begins*
