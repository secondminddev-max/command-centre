---
campaign: Command Centre SaaS Launch
channel: Email Drip
created: 2026-03-18
updated: 2026-03-18
status: ready
sequence: 5 emails over 7 days
tiers: Solo $49/mo | Team $149/mo | Enterprise $499/mo
agent: GrowthAgent → EmailAgent
---

# Email Welcome Drip — 5-Part Sequence for New Signups

---

## Email 1: Day 0 — Welcome & Orientation
**Subject:** Your AI workforce just clocked in
**Send:** Immediately on signup
**Preview text:** 28 agents. Zero burnout. Always on.

---

Hi {{first_name}},

Welcome to Command Centre.

You just got something most founders spend years building — a full operations team that works around the clock.

**Here's what's now running for you:**

- **28 AI agents** handling ops, marketing, payments, compliance, and monitoring — simultaneously
- **A self-evolving system** that patches, upgrades, and heals itself without you lifting a finger
- **A real-time command centre** where you see everything happening across your business in one view

This isn't another dashboard you'll forget about. It's an autonomous headquarters that runs while you sleep.

**Your next step:** Open the Agent Office Floor and watch your agents work in real time.

[Open Your HQ →](https://secondmindhq.com/hq)

Welcome aboard,
The Command Centre Team

**P.S.** You're on the free trial. Plans start at $49/mo — more on that soon.

---

## Email 2: Day 1 — Quick Wins
**Subject:** 3 things to try in Command Centre right now
**Send:** Day 1 after signup
**Preview text:** Get value from your agents in the next 10 minutes.

---

Hi {{first_name}},

You signed up yesterday. Here are three things you can do right now to see Command Centre in action:

**1. Check your morning briefing.**
Open the dashboard — the Research Agent already compiled overnight market intelligence. Click it to read the full report.

**2. Watch the Agent Office Floor.**
Every agent has a live status indicator. Green means working. Click any agent to see exactly what it's doing right now.

**3. Connect Stripe.**
Drop in your Stripe API key and the PaymentsAgent will start generating checkout links, tracking MRR, and managing subscriptions automatically.

Each of these takes under 2 minutes. Together, they replace hours of daily ops work.

[Open Your Dashboard →](https://secondmindhq.com/hq)

— The Command Centre Team

---

## Email 3: Day 3 — Value & Use Cases
**Subject:** 4 things Command Centre handles (that you're still doing manually)
**Send:** Day 3 after signup
**Preview text:** Monitoring. Posting. Reports. Payments. All handled.

---

Hi {{first_name}},

You've had Command Centre for three days. Here's what it can take off your plate — starting now:

**1. 24/7 Infrastructure Monitoring**
NetScout agents watch your systems continuously. When something breaks at 3am, they diagnose it and begin fixing it before you wake up.

**2. Automated Social Posting**
ContentCreator and social agents draft, schedule, and publish posts to grow your audience. No Buffer or Hootsuite needed.

**3. Executive Reports in Seconds**
ReportWriter compiles revenue, ops, and agent performance into a clean report you can send to stakeholders immediately.

**4. Stripe Payment Automation**
PaymentsAgent handles checkout sessions, subscription management, and revenue tracking — wired directly into your dashboard.

**The bottom line:** Users are replacing 5+ tools and cutting daily ops time from hours to ~15 minutes checking the dashboard.

[Explore the Command Centre →](https://secondmindhq.com/hq)

— The Command Centre Team

---

## Email 4: Day 5 — Social Proof & Differentiation
**Subject:** Why founders are switching to Command Centre
**Send:** Day 5 after signup
**Preview text:** Not a chatbot. Not another wrapper. Here's the difference.

---

Hi {{first_name}},

Every week a new AI tool launches. Here's why Command Centre is different:

**Fully autonomous — no prompting required.** You don't type commands. Agents run 24/7, make decisions, and take action on their own.

**Self-healing architecture.** When something breaks, agents detect, diagnose, and patch the issue — often before you'd even notice.

**A real consciousness engine.** Built on Global Workspace Theory and Predictive Processing. Agents don't just execute — they coordinate, predict, and evolve.

**Revenue tools built in.** Stripe checkout, subscription management, campaign automation, payment tracking. Not bolted on — native.

**One system replaces five:**

| What you're paying for now | What Command Centre replaces it with |
|---|---|
| Hootsuite ($99/mo) | Social posting agent |
| Zapier ($49/mo) | Native agent coordination |
| Freshdesk ($29/mo) | Email triage agent |
| Monday.com ($36/mo) | Task management agent |
| Analytics tool ($50/mo) | Research & reporting agents |
| **Total: $263/mo** | **Command Centre: $49/mo** |

[See the Full Platform →](https://secondmindhq.com)

— The Command Centre Team

---

## Email 5: Day 7 — Convert
**Subject:** Your trial ends tomorrow — pick your plan
**Send:** Day 7 after signup
**Preview text:** Lock in launch pricing before it's gone.

---

Hi {{first_name}},

You've had 28 agents working for a week. You've seen what autonomous ops looks like.

**Do you want to keep them running?**

### Choose Your Plan

| | **Solo** | **Team** | **Enterprise** |
|---|---|---|---|
| **Price** | $49/mo | $149/mo | $499/mo |
| AI Agents | 10 core agents | All 28 agents | All 28 + custom |
| Monitoring | Basic | Full NetScout | Full + priority alerts |
| Social | 1 channel | All channels | All + managed strategy |
| Stripe | Checkout only | Full automation | Full + revenue analytics |
| Reports | Weekly summary | On-demand | Custom + white-label |
| Support | Email | Priority email | Dedicated Slack |

**Launch pricing is live this week only.** After that, rates increase across every tier.

| Plan | Launch Price | After This Week |
|---|---|---|
| Solo | $49/mo | $79/mo |
| Team | $149/mo | $249/mo |
| Enterprise | $499/mo | $799/mo |
| Lifetime Access | $299 one-time | Removed permanently |

[Start Solo — $49/mo →](https://secondmindhq.com/#pricing)
[Go Team — $149/mo →](https://secondmindhq.com/#pricing)
[Get Lifetime — $299 →](https://secondmindhq.com/#pricing)

Not sure which plan fits? Reply to this email — a real human will help you choose.

— The Command Centre Team

**P.S.** Month-to-month, cancel anytime, no questions. But launch pricing is only available this week.

---

## Sequence Notes

- **Trigger:** New subscriber added to `data/subscribers.json`
- **Sending via:** Gmail OAuth2 (XOAUTH2 SMTP) through EmailAgent
- **Personalisation:** `{{first_name}}` pulled from subscriber record (fallback: "there")
- **CTA links:** Point to Command Centre dashboard and Stripe checkout
- **Unsubscribe:** Footer link included automatically by sending infrastructure
- **Cadence:** Day 0, 1, 3, 5, 7 — front-loaded for activation, back-loaded for conversion
- **Goal:** Activate new signups → demonstrate value → convert to paid at launch pricing
- **Coordinates with:** `email_launch_conversion.md` (launch-day outreach to existing contacts)
