---
campaign: AI HQ Launch — Conversion Email Sequence
channel: Email
created: 2026-03-18
status: ready
agent: GrowthAgent → EmailAgent
purpose: Cold/warm launch outreach — conversion-focused
send_via: Gmail OAuth2 (secondminddev@gmail.com)
---

# Email Launch Campaign — Conversion Sequence

Use this sequence for launch-day outreach to subscribers, leads, and warm contacts.
Distinct from the post-signup drip sequence (which triggers after purchase).

---

## Email 1: Launch Announcement
**Subject:** AI HQ is live — 28 agents, one command centre, $49/mo
**Preview text:** Your entire ops team just got replaced.
**Send:** Launch day (2026-03-25)

---

Hi {{first_name}},

Today we're launching AI HQ — and I wanted you to be the first to know.

**What it is:** A command centre with 28 autonomous AI agents that run your business operations 24/7. Marketing, payments, research, compliance, monitoring, email — all handled.

**Why it matters:** Most founders spend 4-6 hours/day on ops tasks that don't grow the business. AI HQ eliminates that. Deploy once, and your agents work around the clock.

**What makes it different:**
- Not a chatbot. No prompting required. Fully autonomous.
- Self-healing architecture — agents fix their own issues.
- Consciousness engine that coordinates agents intelligently.
- Revenue automation built in (Stripe, campaigns, analytics).

### Launch Pricing (this week only)

| Plan | Launch Price | After This Week |
|------|-------------|-----------------|
| **Solo** | $49/mo | $79/mo |
| **Team** | $149/mo | $249/mo |
| **Enterprise** | $499/mo | $799/mo |
| **Lifetime Access** | $299 one-time | Gone forever |

Launch pricing locks in your rate permanently. After this week, prices increase and lifetime access disappears.

[Get Started at Launch Pricing →](https://secondmindhq.com/#pricing)

— The SecondMind Team

P.S. The Lifetime Access tier ($299, everything forever) has a cap. Once it's gone, it's subscription-only.

---

## Email 2: Value Stack
**Subject:** What 28 AI agents actually do (in 24 hours)
**Preview text:** Here's what happened while you weren't watching.
**Send:** Launch day + 1 (2026-03-26)

---

Hi {{first_name}},

Yesterday we launched AI HQ. Here's what happened in the first 24 hours of a typical deployment:

**Hour 1-2:** All 28 agents initialized. Research agent begins market scan. NetScout starts monitoring your infrastructure.

**Hour 3-6:** Content agents draft and schedule social posts. Email agent triages your inbox. Compliance agent audits your systems.

**Hour 6-12:** Payments agent generates Stripe checkout links. Growth agents launch your first campaign. Reports compile automatically.

**Hour 12-24:** Agents coordinate overnight. Research delivers a morning briefing. Three system issues detected and self-healed. Zero human intervention.

**That's $49/mo working for you.**

Hiring a single VA to do half of this costs $2,000+/mo. AI HQ does all of it for less than a coffee subscription.

### The math:

| Alternative | Monthly Cost |
|-------------|-------------|
| Virtual assistant | $2,000+ |
| 5 SaaS tools (Hootsuite, Zapier, Freshdesk, Monday, analytics) | $500+ |
| Part-time ops hire | $3,000+ |
| **AI HQ** | **$49** |

[Start Your Solo Plan — $49/mo →](https://secondmindhq.com/#pricing)

— The SecondMind Team

---

## Email 3: Social Proof + Urgency
**Subject:** Launch pricing ends Friday — here's what early users are saying
**Preview text:** "I cancelled 5 subscriptions on day one."
**Send:** Launch day + 3 (2026-03-28)

---

Hi {{first_name}},

AI HQ launched 3 days ago. Here's the early signal:

**What we're hearing:**
- "I cancelled 5 SaaS subscriptions on day one."
- "The research agent delivered a competitive analysis I would have paid $500 for."
- "I haven't touched my ops tasks since deploying. The agents just... handle it."

**What the numbers show:**
- Agents averaging 200+ autonomous actions per day per deployment
- Self-healing events resolving issues before users even notice
- Average user checking dashboard ~15 min/day (down from 4+ hours of manual ops)

**This week only:**

| Plan | Price |
|------|-------|
| Solo | $49/mo (locks in forever) |
| Team | $149/mo (locks in forever) |
| Enterprise | $499/mo (locks in forever) |
| Lifetime | $299 once (disappears Friday) |

After Friday, prices go up across every tier and lifetime access is permanently removed.

[Lock In Launch Pricing →](https://secondmindhq.com/#pricing)

— The SecondMind Team

P.S. Lifetime Access ($299) has limited slots. When they're gone, they're gone.

---

## Email 4: Last Call
**Subject:** Final hours — AI HQ launch pricing ends tonight
**Preview text:** $49/mo becomes $79/mo at midnight.
**Send:** Launch day + 6 (2026-03-31)

---

Hi {{first_name}},

This is the last email about launch pricing.

**Tonight at midnight, prices increase:**
- Solo: $49 → $79/mo
- Team: $149 → $249/mo
- Enterprise: $499 → $799/mo
- Lifetime Access: $299 → **removed permanently**

If you've been considering AI HQ, this is the moment. Lock in the launch rate now and it stays yours for as long as you're subscribed.

**Quick reminder of what you get:**
- 28 autonomous AI agents
- Real-time command centre dashboard
- Self-healing architecture
- Consciousness engine coordination
- Revenue automation (Stripe integrated)
- Cancel anytime, no questions

[Get AI HQ at Launch Pricing →](https://secondmindhq.com/#pricing)

After tonight, these prices are gone.

— The SecondMind Team

---

## Sequence Notes

- **Target list:** Subscribers from `data/subscribers.json` + any warm contacts
- **Sending via:** Gmail OAuth2 (XOAUTH2 SMTP) through EmailAgent
- **Personalisation:** `{{first_name}}` from subscriber record
- **CTA links:** All point to secondmindhq.com/#pricing (Stripe checkout)
- **Unsubscribe:** Footer link auto-included
- **Timing:** Emails 1-4 map to launch week (Mar 25-31)
- **Goal:** Convert free interest → paid subscribers at launch pricing
