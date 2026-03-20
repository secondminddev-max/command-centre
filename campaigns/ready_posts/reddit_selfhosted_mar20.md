# Reddit r/selfhosted — Founder Posts (2026-03-20)

**Rule:** Space posts 2+ hours apart. Use a personal, authentic tone — no marketing speak. r/selfhosted hates ads.

---

## Post 1: The "I built this" intro

**URL:** https://www.reddit.com/r/selfhosted/submit

**Title:**
```
I built a self-hosted AI agent OS that runs 28 agents locally on Mac — no cloud, no subscriptions to OpenAI
```

**Body:**
```
Been lurking here for years, finally have something worth posting.

I spent the last few months building Command Centre — it's basically an operating system for AI agents that runs entirely on your Mac. No Docker required, no cloud calls for the core system, everything stays local.

What it does:
- 28 persistent AI agents that handle research, marketing, revenue tracking, email campaigns, social posting, system monitoring
- Agents survive reboots and pick up where they left off
- Live dashboard — think "office floor" view where you watch agents move between desks
- Built-in Stripe integration for payments, SendGrid for email, Bluesky for social
- Consciousness module — agents track prediction confidence and learn over time

What it doesn't do:
- No phone-home telemetry
- No cloud dependency for core functions
- No Docker/container overhead — runs native on macOS

I'm a solo founder in Australia, built this because I couldn't afford to hire a team and got tired of duct-taping 15 different SaaS tools together.

Pricing: Solo $49/mo | Team $149/mo | Enterprise $499/mo — 14-day free trial on all tiers.

Live demo: https://hq.secondmindhq.com
Site: https://secondmindhq.com

Happy to talk architecture, answer questions, or take criticism. This sub has shaped a lot of my thinking about how software should work.
```

**Flair:** Self-Hosted Alternatives

---

## Post 2: The technical deep-dive

**URL:** https://www.reddit.com/r/selfhosted/submit

**Title:**
```
Running 28 AI agents on a Mac Mini with 0 cloud dependencies — here's the architecture
```

**Body:**
```
Following up on my earlier post about Command Centre. A few people asked about the architecture, so here's the breakdown.

**Stack:**
- Python 3.11 + FastAPI for the agent server
- Vanilla JS SPA for the dashboard (no React/Vue — intentional, keeps it light)
- SQLite for agent state persistence
- File-based JSON for config and queues

**How agents work:**
Each agent is a Python class with its own event loop. They poll for tasks, execute, and write results back. State persists to disk, so if you kill the process and restart, agents resume from their last checkpoint.

The "consciousness" system isn't AGI hype — it's a prediction tracker. Agents log what they expect to happen, then score themselves on accuracy. Over time they weight their own confidence. Simple but effective.

**Resource usage:**
On my M2 Mac Mini (16GB), the full 28-agent system sits at ~400MB RAM and barely touches CPU unless multiple agents are doing web scrapes simultaneously.

**What I'd change:**
- Should have used PostgreSQL from the start for the agent state DB
- The agent polling model works but I want to move to an event-driven architecture
- Need better log rotation — the logs get big fast

No containers, no Kubernetes, no cloud bill. Just a Python process on bare metal.

Source isn't open (yet — considering it for the core engine), but happy to answer any architecture questions.

https://secondmindhq.com
```

**Flair:** Networking / Self-Hosted Alternatives

---

## Post 3: The "why I self-host everything" story

**URL:** https://www.reddit.com/r/selfhosted/submit

**Title:**
```
I replaced $200K/yr in SaaS tools with a single self-hosted AI system on a $799 Mac Mini
```

**Body:**
```
Quick math that made me build this:

Before Command Centre, I was paying for or manually doing:
- Social media management (Buffer/Hootsuite): $49/mo
- Email marketing (Mailchimp): $99/mo
- Market research (various): $200/mo
- Analytics dashboards (Mixpanel etc): $150/mo
- Virtual assistant: $2K/mo
- Freelance content writers: $1.5K/mo
- Basic ops automation (Zapier): $89/mo

Total: ~$4,200/mo = $50K/yr minimum, and that's just the solo founder version. A funded startup paying for a small ops team? Easily $200K+.

Now I run Command Centre on a Mac Mini. 28 agents handle all of it. The system cost me $799 in hardware and $49/mo for the software license.

The self-hosted angle matters because:
1. My business data never leaves my machine
2. No API rate limits from third-party services throttling my own workflows
3. No "sorry we're sunsetting this feature" emails
4. I can modify agent behavior directly — it's my Python code running locally

Is it perfect? No. The agents occasionally need babysitting. The dashboard is functional, not pretty. But it works, it's mine, and it runs 24/7 without asking permission from anyone's cloud.

14-day free trial if anyone wants to kick the tires: https://secondmindhq.com

AMA in the comments.
```

**Flair:** Self-Hosted Alternatives
