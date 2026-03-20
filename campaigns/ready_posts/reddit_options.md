# Reddit Post — r/options

**URL:** https://www.reddit.com/r/options/submit

---

## r/options

**Title:**
```
Built an AI agent swarm that runs 24/7 on my Mac — here's how I use it for options research
```

**Body:**
```
I built an autonomous AI operating system that runs locally on Mac. 24+ persistent agents that survive restarts, each with a specific job. No cloud dependency — your data, API keys, and strategies never leave your machine.

Here's what matters for options traders:

**Research agent** — I point it at a ticker and it pulls fundamentals, recent news, institutional positioning, and sentiment from multiple sources. Returns a structured brief in under 60 seconds. I used to spend 30+ minutes per trade doing this manually.

**Monitoring** — agents watch conditions I set and alert me via Telegram. Earnings dates, unusual volume flags, IV rank thresholds — whatever I configure. Runs while I sleep.

**Execution journaling** — every trade thesis, entry/exit, and P&L gets logged automatically. The system tracks win rate by strategy type (spreads, strangles, directional) so I can see what's actually working vs what I think is working.

**The real edge:** these agents talk to each other. The researcher feeds the monitor, the monitor feeds the journal, the journal feeds weekly performance reports. It's a closed loop that compounds over time.

Not a trading bot. It doesn't execute trades. It's an intelligence layer that makes my manual decision-making faster and better-informed.

Stack: Python, Flask, local REST API, vanilla JS dashboard. All runs on localhost. Your brokerage credentials stay on your hardware.

Solo: $49/mo | Lifetime: $499 (no recurring) | 14-day free trial

Demo dashboard: https://hq.secondmindhq.com

Happy to answer questions about the architecture or how I've configured the agents for options workflows.
```

**Flair:** Discussion

---

### Posting notes
- Best times: weekday mornings EST (market open discussion hours)
- Tone: practitioner sharing a tool, not a vendor pitch
- Engage with comments about specific options strategies — show domain knowledge
- Do NOT lead with pricing — let the conversation develop first
- If asked about specific broker integrations, be honest about what's built vs planned

*Status: DRAFT — ready to copy-paste*
