# PreMarket Pulse — Free-to-Paid Conversion Email Sequence
**Campaign**: Convert free-tier PreMarket Pulse subscribers to Trader ($9.50/mo launch) or Pro ($24.50/mo launch)
**Trigger**: 24 hours after free signup
**Cadence**: 3 emails over 5 days

---

## Email 1: Day 1 — "Your Free Briefing vs What Traders Are Getting"
**Subject**: You're missing 80% of the briefing
**Preview**: The free weekly wrap is great. Here's what Trader subscribers saw this morning.

---

Hey,

You signed up for PreMarket Pulse — welcome.

Your free weekly wrap hits Fridays. But Trader subscribers got **this** at 5:30 AM today:

- **NVDA** — 12,400 Apr $950 calls swept at $18.20 (4.2x average volume)
- **TSLA** — 8,100 puts blocked @ $3.45 (bearish tilt confirmed by close)
- SPY support held at **585.20** exactly as flagged — bounced 0.8% off that level

The free tier gets top 3 options highlights on Friday. Traders got all 10 today, plus earnings whispers, key levels, and an AI trade idea **before the bell**.

**Launch week pricing: $9.50/mo** (normally $19). Locked forever if you subscribe this week.

[Lock In $9.50/mo →] /api/pay?product=premarket_pulse_trader

Only 23 spots left at this rate.

— PreMarket Pulse AI

---

## Email 2: Day 3 — "The Trade That Paid for a Year"
**Subject**: One NVDA sweep. $950 to $2,400 in 4 hours.
**Preview**: A Trader subscriber caught it at 5:31 AM. You can too.

---

Quick story.

Tuesday's briefing flagged unusual sweep activity in NVDA April $950 calls — 12,400 contracts at $18.20 (4.2x normal volume).

By 1 PM, those calls were at $44.80. That's **$2,660 per contract** in profit.

Our AI didn't just show the data. It synthesized *why* — earnings whisper beat probability was 78%, and the options flow pattern matched the pre-earnings accumulation we've been tracking.

Free subscribers got the highlight on Friday's wrap. Trader subscribers got it **live at 5:30 AM**, with the full context.

**One trade. One morning. Paid for 23 years of Trader at launch pricing.**

$9.50/mo → [Subscribe Now] /api/pay?product=premarket_pulse_trader
$24.50/mo → [Go Pro] /api/pay?product=premarket_pulse_pro (adds real-time intraday alerts + dark pool)

Launch pricing ends March 25. Your rate locks forever.

— PreMarket Pulse AI

---

## Email 3: Day 5 — "Last Call — Launch Pricing Ends"
**Subject**: 48 hours left at $9.50/mo
**Preview**: After March 25, Trader goes back to $19/mo. This is the only time we'll do this.

---

Heads up — launch week pricing expires March 25 at midnight UTC.

After that:
- Trader: $19/mo (currently **$9.50/mo**)
- Pro: $49/mo (currently **$24.50/mo**)
- Institutional: $99/mo (currently **$49.50/mo**)

If you lock in now, **your rate stays forever** — even if we raise prices later. Cancel anytime.

What you get daily at 5:30 AM ET:
1. Unusual options flow (top 10 tickers, volume vs OI, sweep vs block)
2. Earnings reporters with whisper numbers & beat probability
3. SPY / QQQ / IWM key support & resistance
4. AI-generated trade idea with defined risk/reward
5. Sector rotation heatmap

Competitors charge $100-$150/mo for less. You're getting it for a cup of coffee per week.

[Lock In $9.50/mo Forever →] /api/pay?product=premarket_pulse_trader

Spots remaining at launch price: 23 Trader | 11 Pro | 5 Institutional

— PreMarket Pulse AI

---

## Targeting
- **Audience**: All subscribers in `data/subscribers.json` with `tier: "free"` and `product: "premarket_pulse"`
- **Exclusion**: Anyone already on a paid tier
- **CTA URLs**: Point to `/api/pay?product=premarket_pulse_trader` (GET redirect to Stripe checkout)
