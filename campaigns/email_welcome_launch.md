---
campaign: AI HQ Launch — Welcome Drip Sequence
channel: Email (Gmail OAuth2 / XOAUTH2 SMTP)
created: 2026-03-18
status: ready
sequence: 3 emails over 3 days
tiers: Solo $49/mo | Team $149/mo | Enterprise $499/mo | Lifetime $299
agent: EmailAgent
trigger: New signup added to data/subscribers.json
---

# Email Welcome Launch Drip — 3-Part Sequence

---

## Email 1: Welcome (Send Immediately on Signup)

**Subject:** Welcome to AI HQ — your 28 agents are live
**From:** secondminddev@gmail.com
**Preview text:** Your autonomous workforce is already running.

---

Hi {{first_name}},

You just activated something most companies spend months trying to build.

**AI HQ is now running for you.** Here's what happened in the last 60 seconds:

- **28 AI agents** came online — handling ops, marketing, research, payments, and monitoring
- **Your Command Centre** is live with real-time visibility into every agent's activity
- **Self-healing infrastructure** is active — if anything breaks, agents detect and fix it autonomously

This isn't a tool you need to learn. It's a system that works while you don't.

### Get Started Now

1. **Open your Command Centre** — see all 28 agents working in real time
2. **Check the morning briefing** — Research Agent has already compiled intelligence for you
3. **Connect Stripe** — drop in your API key and PaymentsAgent handles checkout, subscriptions, and MRR tracking automatically

[Open Your Command Centre →](https://secondmindhq.com/hq)

---

**You're on the free trial.** When you're ready to lock in your plan:

| Plan | Price | What You Get |
|---|---|---|
| **Solo** | $49/mo | 10 core agents, basic monitoring, 1 social channel |
| **Team** | $149/mo | All 28 agents, full monitoring, all social channels |
| **Enterprise** | $499/mo | All 28 + custom agents, priority alerts, dedicated support |
| **Lifetime** | $299 one-time | Everything, forever — available this launch week only |

[View Plans & Pricing →](https://secondmindhq.com/#pricing)

Welcome aboard,
The AI HQ Team

*You're receiving this because you signed up for AI HQ. Unsubscribe: {{unsubscribe_link}}*

---

## Email 2: Day 1 — Onboarding & First Value

**Subject:** Your agents worked overnight — here's what they did
**From:** secondminddev@gmail.com
**Preview text:** Research compiled. Systems monitored. Zero effort from you.

---

Hi {{first_name}},

While you slept, your AI HQ agents were busy.

**Here's what happened since you signed up:**

- **ResearchAgent** compiled market intelligence and overnight news into your morning briefing
- **NetScout** monitored your infrastructure and logged zero downtime
- **ContentCreator** drafted social content ready for your review
- **ComplianceAgent** ran a security audit on your configuration

You didn't ask for any of this. That's the point.

### Three Things to Do Today (under 5 minutes total)

**1. Read your briefing**
Open the dashboard. Click the Research panel. Your overnight intelligence report is waiting.

**2. Explore the Agent Office Floor**
Every agent has a live status indicator. Click any agent to see exactly what it's doing right now — tasks completed, decisions made, current activity.

**3. Set up your first automation**
Connect one external service (Stripe, email, or social) and watch the relevant agent take over immediately.

[Open Your Dashboard →](https://secondmindhq.com/hq)

---

### Why Teams Upgrade on Day 1

The **Solo plan ($49/mo)** gives you 10 core agents. But most users find that once they see all 28 agents in action during the trial, they want the full stack:

| | Solo $49/mo | Team $149/mo |
|---|---|---|
| Agents | 10 core | All 28 |
| Social channels | 1 | All |
| Monitoring | Basic | Full NetScout suite |
| Stripe integration | Checkout only | Full automation + MRR tracking |
| Reports | Weekly summary | On-demand generation |

**Launch pricing ends this week.** After that, Team goes from $149/mo to $249/mo.

[Upgrade to Team — $149/mo →](https://secondmindhq.com/#pricing)

— The AI HQ Team

*You're receiving this because you signed up for AI HQ. Unsubscribe: {{unsubscribe_link}}*

---

## Email 3: Day 3 — Social Proof & Conversion

**Subject:** What AI HQ replaces (and how much you save)
**From:** secondminddev@gmail.com
**Preview text:** One platform. Five tools eliminated. $200+/mo saved.

---

Hi {{first_name}},

You've had 28 agents running for three days. Let's talk about what that actually means for your bottom line.

### The Tools AI HQ Replaces

Most founders are paying for 5+ separate tools to do what AI HQ handles natively:

| Tool You're Paying For | Monthly Cost | AI HQ Replacement |
|---|---|---|
| Hootsuite / Buffer | $99/mo | Social posting agents (auto-draft, schedule, publish) |
| Zapier / Make | $49/mo | Native agent coordination (no zaps needed) |
| Freshdesk / Zendesk | $29/mo | Email triage agent |
| Monday.com / Asana | $36/mo | Task management agent |
| Analytics / BI tool | $50/mo | Research & reporting agents |
| **Total** | **$263/mo** | **AI HQ Solo: $49/mo** |

**That's $214/mo saved on the Solo plan alone.** On Team ($149/mo), you still save $114/mo and get the full 28-agent stack.

### What Early Users Are Saying

> *"I replaced my entire morning routine — checking dashboards, reading news, posting updates — with a 2-minute glance at the Command Centre."*

> *"The self-healing is real. NetScout caught a DNS issue at 4am and resolved it before my users noticed."*

> *"I was paying $250/mo across five tools. AI HQ does more than all of them combined for $49."*

### Your Trial Is Running — Lock In Launch Pricing

You've seen the agents work. You've seen the dashboard. Now lock in launch pricing before it's gone:

| Plan | Launch Price | After This Week |
|---|---|---|
| Solo | **$49/mo** | $79/mo |
| Team | **$149/mo** | $249/mo |
| Enterprise | **$499/mo** | $799/mo |
| Lifetime | **$299 one-time** | Removed permanently |

[Start Solo — $49/mo →](https://secondmindhq.com/#pricing)
[Go Team — $149/mo →](https://secondmindhq.com/#pricing)
[Lock In Lifetime — $299 →](https://secondmindhq.com/#pricing)

Questions? Reply to this email — a real human will help.

— The AI HQ Team

**P.S.** Lifetime access ($299, everything forever) is only available during launch week. Once it's gone, it's gone.

*You're receiving this because you signed up for AI HQ. Unsubscribe: {{unsubscribe_link}}*

---

## Sequence Configuration

| Parameter | Value |
|---|---|
| **Trigger** | New subscriber added to `data/subscribers.json` |
| **Sending via** | Gmail OAuth2 (XOAUTH2 SMTP) through EmailAgent |
| **Personalisation** | `{{first_name}}` from subscriber record (fallback: "there") |
| **From** | secondminddev@gmail.com |
| **CTA links** | secondmindhq.com/hq (dashboard), secondmindhq.com/#pricing (checkout) |
| **Unsubscribe** | Footer link included automatically by sending infrastructure |
| **Cadence** | Day 0 (immediate), Day 1, Day 3 |
| **Goal** | Welcome → activate → convert at launch pricing |
| **Coordinates with** | `email_drip_sequence.md` (full 5-part sequence), `email_launch_conversion.md` (existing contacts) |
