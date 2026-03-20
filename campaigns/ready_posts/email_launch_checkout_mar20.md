# Email Campaign — Launch Announcement with Checkout Links (2026-03-20)

**Send via:** Email queue → data/email_queue.json
**From:** hello@secondmindhq.com
**Subject line options (A/B test):**
- A: "Command Centre is live — your AI workforce starts today"
- B: "28 AI agents. Your Mac. $49/mo. Live now."

---

## Email 1: Launch Announcement (send immediately)

**Subject:** Command Centre is live — your AI workforce starts today

**Body (HTML):**

```html
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Command Centre Launch</title>
<style>
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #050810; color: #d4d4d4; margin: 0; padding: 0; }
.wrapper { max-width: 600px; margin: 0 auto; padding: 40px 24px; }
h1 { color: #ffffff; font-size: 28px; line-height: 1.3; margin-bottom: 8px; }
h2 { color: #00c8ff; font-size: 20px; margin-top: 32px; margin-bottom: 12px; }
p { font-size: 16px; line-height: 1.6; margin-bottom: 16px; }
.highlight { color: #00ff88; font-weight: 600; }
.cta-button { display: inline-block; background: linear-gradient(135deg, #00c8ff, #a855f7); color: #ffffff; text-decoration: none; padding: 16px 40px; border-radius: 8px; font-size: 18px; font-weight: 700; margin: 24px 0; }
.tier-box { background: #0c1220; border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; padding: 20px; margin: 12px 0; }
.tier-name { color: #00c8ff; font-weight: 700; font-size: 18px; }
.tier-price { color: #ffffff; font-size: 24px; font-weight: 800; }
.tier-desc { color: #a0a0a0; font-size: 14px; margin-top: 4px; }
.footer { margin-top: 40px; padding-top: 24px; border-top: 1px solid rgba(255,255,255,0.08); font-size: 13px; color: #666; }
a { color: #00c8ff; }
</style>
</head>
<body>
<div class="wrapper">

<h1>Command Centre is live.</h1>
<p>28 AI agents. Running on your Mac. No cloud dependency. Working while you sleep.</p>

<p>You signed up because you were curious about autonomous AI that actually runs your business — not another chatbot wrapper. Today, it's real and ready to install.</p>

<h2>What you get on day one:</h2>
<p>
&#x2713; <span class="highlight">28 persistent agents</span> — research, marketing, revenue tracking, email, social, monitoring<br>
&#x2713; <span class="highlight">Live dashboard</span> — watch agents work in real-time on an office-floor map<br>
&#x2713; <span class="highlight">Revenue tools built in</span> — Stripe payments, SendGrid email, Bluesky social<br>
&#x2713; <span class="highlight">Fully local</span> — your data stays on your machine, always<br>
&#x2713; <span class="highlight">Consciousness engine</span> — agents learn from their own predictions over time
</p>

<div style="text-align: center;">
<a href="https://secondmindhq.com/#pricing" class="cta-button">See Pricing &amp; Start Free Trial</a>
</div>

<h2>Choose your tier:</h2>

<div class="tier-box">
<div class="tier-name">Solo</div>
<div class="tier-price">$49/mo</div>
<div class="tier-desc">Full agent suite, live dashboard, email support. Perfect for solo founders and indie hackers.</div>
<p><a href="https://secondmindhq.com/#pricing">Start 14-day free trial &rarr;</a></p>
</div>

<div class="tier-box">
<div class="tier-name">Team</div>
<div class="tier-price">$149/mo</div>
<div class="tier-desc">Everything in Solo + multi-user access, priority support, advanced analytics.</div>
<p><a href="https://secondmindhq.com/#pricing">Start 14-day free trial &rarr;</a></p>
</div>

<div class="tier-box">
<div class="tier-name">Enterprise</div>
<div class="tier-price">$499/mo</div>
<div class="tier-desc">Full platform + custom agent development, dedicated onboarding, SLA guarantees.</div>
<p><a href="https://secondmindhq.com/#pricing">Start 14-day free trial &rarr;</a></p>
</div>

<p style="text-align: center; margin-top: 32px;">
<a href="https://hq.secondmindhq.com" style="color: #a855f7;">Try the live demo first &rarr;</a>
</p>

<p>Every tier includes a <span class="highlight">14-day free trial</span>. No credit card required to start. Cancel anytime.</p>

<p>Built by a solo founder in Australia. No VC, no bloat, no enterprise sales team. Just software that works.</p>

<div class="footer">
<p>Second Mind Labs<br>
<a href="https://secondmindhq.com">secondmindhq.com</a></p>
<p>You're receiving this because you signed up at secondmindhq.com or hq.secondmindhq.com.<br>
<a href="https://secondmindhq.com/unsubscribe">Unsubscribe</a></p>
</div>

</div>
</body>
</html>
```

---

## Email 2: Follow-up (send 48 hours after Email 1)

**Subject:** Quick question — did you try the demo?

**Body (plain text):**

```
Hey —

Sent you the Command Centre launch email a couple days ago. Wanted to follow up with one question:

Did you get a chance to try the live demo?

→ https://hq.secondmindhq.com

If you did — what did you think? Reply to this email, I read every one.

If you didn't — here's the 30-second version:

Command Centre is 28 AI agents that run on your Mac. They handle research, marketing, email campaigns, revenue tracking, social media, and system monitoring. All local, no cloud dependency.

Three tiers:
• Solo — $49/mo (solo founders)
• Team — $149/mo (small teams)
• Enterprise — $499/mo (custom agents + SLA)

All come with a 14-day free trial: https://secondmindhq.com/#pricing

No pressure. But if you've been thinking about replacing manual ops work with AI that actually runs autonomously — this is what I built it for.

— Second Mind Labs
https://secondmindhq.com
```

---

## Queue Format (for email_queue.json)

```json
[
  {
    "to": "{{subscriber_email}}",
    "subject": "Command Centre is live — your AI workforce starts today",
    "body": "<!-- paste HTML from Email 1 above -->",
    "html": true
  }
]
```
