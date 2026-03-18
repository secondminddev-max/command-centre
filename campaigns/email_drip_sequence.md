---
campaign: AI HQ SaaS Launch
channel: Email Drip
created: 2026-03-18
status: ready
sequence: 3 emails over 5 days
tiers: Solo $49/mo | Team $149/mo | Enterprise $499/mo
---

# Email Drip Sequence — New Subscribers

---

## Email 1: Day 0 — Welcome
**Subject:** Your AI workforce just clocked in
**Send:** Immediately on signup
**Preview text:** 28 agents. Zero burnout. Always on.

---

Hi {{first_name}},

Welcome to AI HQ.

You just got something most founders spend years building — a full operations team that works around the clock.

**Here's what's now running for you:**

- **28 AI agents** handling ops, marketing, payments, compliance, and monitoring — simultaneously
- **A self-evolving system** that patches, upgrades, and heals itself without you lifting a finger
- **A real-time command centre** where you see everything happening across your business in one view

This isn't another dashboard you'll forget about. It's an autonomous headquarters that runs while you sleep.

**Your next step:** Open the Agent Office Floor and watch your agents work in real time.

[Open Your HQ →]

Welcome aboard,
The AI HQ Team

**P.S.** You're on the free trial. Plans start at $49/mo — more on that soon.

---

## Email 2: Day 2 — Value & Use Cases
**Subject:** 4 things AI HQ is handling right now (that you're still doing manually)
**Send:** Day 2 after signup
**Preview text:** Monitoring. Posting. Reports. Payments. All handled.

---

Hi {{first_name}},

You've had AI HQ for two days. Here's what it can take off your plate — starting now:

**1. 24/7 Infrastructure Monitoring**
NetScout agents watch your systems continuously. When something breaks at 3am, they diagnose it and begin fixing it before you wake up.

**2. Automated Social Posting**
ContentCreator and social agents draft, schedule, and publish posts to grow your audience. No Buffer or Hootsuite needed.

**3. Executive Reports in Seconds**
ReportWriter compiles revenue, ops, and agent performance into a clean report you can send to stakeholders immediately.

**4. Stripe Payment Automation**
PaymentsAgent handles checkout sessions, subscription management, and revenue tracking — wired directly into your dashboard.

**The bottom line:** Early users are replacing 5+ tools and cutting daily ops time from hours to ~15 minutes checking the dashboard.

Head to the Command Centre and click into any agent to see its live activity feed.

[Explore the Command Centre →]

— The AI HQ Team

---

## Email 3: Day 5 — Convert
**Subject:** Your trial is ending — pick your plan
**Send:** Day 5 after signup
**Preview text:** Lock in launch pricing before it's gone.

---

Hi {{first_name}},

You've had 28 agents working for 5 days. You've seen what autonomous ops looks like.

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

**Launch pricing expires Friday.** After that, rates increase across every tier.

[Start Solo — $49/mo →]
[Go Team — $149/mo →]
[Scale Enterprise — $499/mo →]

Not sure which plan fits? Reply to this email — a real human will help you choose.

— The AI HQ Team

**P.S.** Month-to-month, cancel anytime, no questions. But launch pricing is only available this week.

---

## Sequence Notes

- **Trigger:** New subscriber added to `data/subscribers.json`
- **Sending via:** Gmail OAuth2 (XOAUTH2 SMTP) through EmailAgent
- **Personalisation:** `{{first_name}}` pulled from subscriber record
- **CTA links:** Point to Command Centre dashboard and Stripe checkout
- **Unsubscribe:** Footer link included automatically by sending infrastructure
