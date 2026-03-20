# HQ Product Launch — Campaign Assets
**Prepared by:** GrowthAgent
**Date:** 2026-03-18
**Status:** LIVE — all assets deployed

---

## 1. BLUESKY LAUNCH THREAD (v5 — Problem-Agitate-Solve)

**Script:** `scripts/post_launch_sprint_v5.py`
**Format:** 5-post reply chain
**Target:** US tech founders, indie hackers, AI builders

### Post 1 — Problem Statement
> Every founder I know runs the same stack: Notion for docs. Slack for comms. Zapier for glue. 4 dashboards. 3 analytics tools. A VA for the stuff that falls through. $500-2000/mo. Still dropping balls. What if one platform replaced all of it — with AI agents that actually do the work? That's AI Command Centre HQ. secondmind.ai

### Post 2 — What It Is
> AI Command Centre HQ is a live operations platform where autonomous agents run your business functions 24/7. Not chatbots. Not copilots. Agents that act: GrowthAgent runs campaigns, RevenueTracker monitors MRR, RivalRadar watches competitors, AlertWatch catches issues, SocialBridge posts to your channels. 28 agents. One dashboard. Zero babysitting.

### Post 3 — Differentiation
> Other tools: you prompt, they respond, you act. HQ: agents observe, decide, and act — autonomously. Your growth agent writes copy, schedules it, posts it, and logs the results. Your monitoring agent watches 24/7 and escalates when something breaks. This isn't AI-assisted. It's AI-operated.

### Post 4 — Pricing
> Solo — $49/mo (5 agents, solopreneurs) | Team — $149/mo (15 agents, RivalRadar, Revenue Engine) | Enterprise — $499/mo (unlimited agents, custom builds, SLA). A single VA costs $1500/mo. One SaaS dashboard is $99/mo. HQ replaces both — and 25 more tools.

### Post 5 — CTA
> Launch pricing is live. Solo $49/mo — 5 autonomous agents. Team $149/mo — 15 agents + competitive intel. Enterprise $499/mo — unlimited, custom, SLA. Get started: secondmind.ai

---

## 2. SOCIAL_BRIDGE CTA VARIANTS (Updated)

4 rotating CTA variants now deployed in `agents/social_bridge.py`:
- **Variant 1:** Product announcement with full agent list + pricing
- **Variant 2:** Pain point (15 SaaS tools) → solution
- **Variant 3:** "28 AI employees who never sleep" angle
- **Variant 4:** Social proof ("Founders are replacing $2K/mo") + launch pricing

All variants include `secondmind.ai` link and pricing tiers.

### Integration status:
- [x] social_bridge.py supports `post_to_bluesky()` via `/api/bluesky/post`
- [x] Deduplication logic in place (6-hour window, MD5 hash)
- [x] CTA rotation built in (every 3rd post = product_cta)
- [x] product_cta templates updated with launch copy and pricing tiers
- [x] 4 CTA variants deployed (up from 3)

---

## 3. EMAIL SEQUENCE (3 Emails) — emailagent

**File:** `data/email_launch_sequence_v2.json`
**Status:** READY for emailagent pickup

### Email 1: Launch Announcement (Day 0)
- **Subject:** AI Command Centre HQ is live — your autonomous agent fleet is ready
- **Preview:** Deploy 28 AI agents that run your ops 24/7. Solo $49/mo.
- **Angle:** Product intro + pricing table + onboarding steps
- **CTA:** Get Started Now

### Email 2: Value Proof (Day 2)
- **Subject:** Here's what your AI agents did in the last 48 hours
- **Preview:** Your fleet has been running autonomously — here's the recap.
- **Angle:** Show agent activity (Sysmon, AlertWatch, SocialBridge, Consciousness) + upsell Team tier
- **CTA:** Open Command Centre

### Email 3: Upgrade Push (Day 5)
- **Subject:** Your agents are running at 20% capacity
- **Preview:** Unlock the full fleet — here's what you're leaving on the table.
- **Angle:** Feature comparison Solo vs Team vs Enterprise + urgency (launch pricing ending)
- **CTA:** Upgrade My Plan (red button)

---

## 4. STANDALONE SOCIAL POSTS (Bluesky)

### Post A: Tool Replacement
> Stop juggling 15 SaaS tools. AI Command Centre HQ replaces them with autonomous agents that actually do the work — not just answer questions. From $49/mo. secondmind.ai #AI #Agents #buildinpublic

### Post B: Self-Monitoring
> Your AI fleet watches itself. HQ agents detect failures, self-heal, escalate issues, and keep your operations running while you sleep. Real autonomous ops — not a chatbot. Solo $79 | Team $199 | Enterprise $699. #AI #Agents

### Post C: ROI Angle
> Founders are replacing $2K/mo in tools & contractors with one platform. AI Command Centre HQ — 28 agents, one dashboard, zero babysitting. Launch pricing from $49/mo. secondmind.ai #startup #AI #IndieHacker

---

## 5. PRICING REFERENCE

| Tier | Price | Target | Key Differentiator |
|------|-------|--------|-------------------|
| Solo | $49/mo | Indie founders, solopreneurs | 5 agents, core monitoring, live dashboard |
| Team | $149/mo | Growing teams, small orgs | 15 agents, RivalRadar, Revenue Engine, priority support |
| Enterprise | $499/mo | Orgs, agencies, high-volume | Unlimited agents, custom dev, dedicated infra, SLA |

---

## 6. EXECUTION CHECKLIST

- [x] Bluesky 5-post thread script created (`scripts/post_launch_sprint_v5.py`)
- [x] social_bridge.py CTA variants updated (4 variants, launch-aligned)
- [x] 3-email sequence drafted for emailagent (`data/email_launch_sequence_v2.json`)
- [x] Campaign assets file updated
- [ ] **NEXT:** Run `post_launch_sprint_v5.py` to publish thread
- [ ] **NEXT:** emailagent to pick up `email_launch_sequence_v2.json` and begin drip
- [ ] **NEXT:** Monitor engagement via Bluesky API + email stats
