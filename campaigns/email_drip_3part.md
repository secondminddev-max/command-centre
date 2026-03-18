---
campaign: AI HQ New Signup Drip — 3 Part
channel: Email Drip
created: 2026-03-18
status: draft
sequence: 3 emails over 5 days
tiers: Solo $49/mo | Team $149/mo | Enterprise $499/mo
agent: EmailAgent
trigger: New signup at secondmindhq.com
---

# 3-Part Launch Email Drip — New Signups

---

## Email 1: Day 0 — Welcome
**Subject:** Welcome to AI HQ — your autonomous workforce is live
**Preview text:** 28 agents. Zero burnout. Always on.
**Send:** Immediately on signup

---

Hi {{first_name}},

Welcome to AI HQ — you just activated something most founders spend years trying to build.

**Here's what's now running for you:**

- **28 AI agents** handling operations, marketing, payments, compliance, and monitoring — simultaneously, around the clock
- **A self-evolving system** that patches, upgrades, and heals itself without you lifting a finger
- **A real-time command centre** where you see everything happening across your business in one view

This isn't another SaaS dashboard you'll forget about in a week. It's an autonomous headquarters that works while you sleep.

**Key features to explore right away:**

1. **Agent Office Floor** — watch every agent working in real time with live status indicators
2. **Morning Briefing** — your Research Agent compiles overnight intelligence automatically
3. **Stripe Integration** — connect your Stripe key and PaymentsAgent starts managing checkout, subscriptions, and MRR tracking instantly

**Your next step:** Log in and explore the command centre.

[Open Your HQ →](https://secondmindhq.com/hq)

Welcome aboard,
The AI HQ Team

P.S. You're on a free trial — plans start at just $49/mo. We'll share more on that soon.

---

## Email 2: Day 2 — Onboarding
**Subject:** Set up your first agent in 3 minutes
**Preview text:** A quick walkthrough to get real value from AI HQ today.
**Send:** Day 2 after signup

---

Hi {{first_name}},

You've had AI HQ for two days. Let's make sure you're getting the most out of it.

Here's a quick walkthrough to set up your first agent and start seeing results:

### Step 1: Open the Agent Office Floor

Log into your dashboard and click **Agent Office Floor**. You'll see all 28 agents with live status indicators — green means active and working.

[Open Agent Office Floor →](https://secondmindhq.com/hq)

### Step 2: Pick an agent to configure

Here are three high-impact agents to start with:

| Agent | What it does | Setup time |
|---|---|---|
| **PaymentsAgent** | Manages Stripe checkout, subscriptions, and revenue tracking | ~2 min (paste Stripe API key) |
| **ContentCreator** | Drafts and schedules social posts to grow your audience | ~1 min (connect Bluesky) |
| **ResearchAgent** | Compiles overnight market intelligence into a morning briefing | Already running — just read it |

### Step 3: Click the agent → follow the setup prompt

Each agent has a configuration panel. Click the agent name, fill in any required API keys or preferences, and hit **Activate**. That's it — the agent starts working immediately.

### Pro tips from power users

- **Check the morning briefing daily.** ResearchAgent compiles it overnight — it's the fastest way to stay informed.
- **Connect Stripe early.** PaymentsAgent can generate checkout links, track MRR, and manage subscriptions from day one.
- **Watch the live feed.** The Agent Office Floor shows what every agent is doing in real time. It's the fastest way to understand the system.
- **Let agents coordinate.** AI HQ agents share context through a Global Workspace — the more agents you activate, the smarter the whole system gets.

### Need help?

Reply to this email — a real human will get back to you within 24 hours.

— The AI HQ Team

---

## Email 3: Day 5 — Upsell
**Subject:** You're running 28 agents — here's how to unlock their full power
**Preview text:** Team and Enterprise plans are live. Launch pricing won't last.
**Send:** Day 5 after signup

---

Hi {{first_name}},

You've had AI HQ running for five days. By now your agents have been monitoring systems, compiling research, drafting content, and managing operations — all without you lifting a finger.

Here's the question: **are you ready to unlock the full platform?**

### What you're replacing

| Tool you're paying for now | AI HQ replaces it with |
|---|---|
| Hootsuite ($99/mo) | Social posting agents |
| Zapier ($49/mo) | Native agent coordination |
| Freshdesk ($29/mo) | Email triage agent |
| Monday.com ($36/mo) | Task management agent |
| Analytics tool ($50/mo) | Research & reporting agents |
| **Total: ~$263/mo** | **AI HQ from $49/mo** |

That's up to **5.4x cost savings** — before counting the hours you get back every week.

### ROI by the numbers

- **12+ hours/week** saved on ops tasks that agents now handle autonomously
- **$3,000+/year** in tool consolidation savings on Team plan
- **24/7 coverage** — agents don't sleep, don't take holidays, don't burn out
- **Self-healing architecture** — issues are detected and patched automatically, often before you'd notice

### Choose your plan

| | **Solo** | **Team** | **Enterprise** |
|---|---|---|---|
| **Price** | $49/mo | **$149/mo** | **$499/mo** |
| AI Agents | 10 core agents | All 28 agents | All 28 + custom agents |
| Monitoring | Basic | Full NetScout suite | Full + priority alerts |
| Social channels | 1 channel | All channels | All + managed strategy |
| Stripe integration | Checkout only | Full automation | Full + revenue analytics |
| Reports | Weekly summary | On-demand generation | Custom + white-label |
| Support | Email | Priority email | Dedicated Slack channel |

### Why Team ($149/mo) is the sweet spot

Most founders choose Team because it unlocks **all 28 agents** and **full Stripe automation** — the two features that drive the most value. You get the complete autonomous system instead of a limited subset.

### Why Enterprise ($499/mo) makes sense at scale

If you're managing multiple products, need custom agents built for your workflow, or want white-label reports for stakeholders — Enterprise pays for itself in the first month. Dedicated Slack support means zero wait times.

### Launch pricing is live — but not for long

| Plan | Launch Price | Regular Price |
|---|---|---|
| Solo | $49/mo | $79/mo |
| Team | **$149/mo** | $249/mo |
| Enterprise | **$499/mo** | $799/mo |

Lock in launch pricing now — it increases permanently after launch week.

[Start Solo — $49/mo →](https://secondmindhq.com/#pricing)
[Upgrade to Team — $149/mo →](https://secondmindhq.com/#pricing)
[Go Enterprise — $499/mo →](https://secondmindhq.com/#pricing)

Not sure which tier fits? Reply to this email and we'll help you choose.

— The AI HQ Team

P.S. All plans are month-to-month, cancel anytime. But launch pricing is only available this week.

---

## Sequence Notes

- **Trigger:** New subscriber added to `data/subscribers.json` via secondmindhq.com signup
- **Sending via:** Gmail OAuth2 (XOAUTH2 SMTP) through EmailAgent
- **Personalisation:** `{{first_name}}` from subscriber record (fallback: "there")
- **CTA links:** Command centre dashboard + Stripe checkout pricing anchor
- **Unsubscribe:** Footer link included automatically by sending infrastructure
- **Cadence:** Day 0, Day 2, Day 5 — activation-first, conversion-close
- **Goal:** Activate → onboard → convert to paid (target: Team $149/mo tier)
