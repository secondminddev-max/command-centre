#!/usr/bin/env python3
"""PreMarket Pulse — AI Synthesis
Reads data/premarket_raw.json, generates formatted HTML email briefing at reports/premarket_email.html.
"""
import json, os
from datetime import datetime, timezone
from pathlib import Path

CWD = Path(__file__).resolve().parent.parent
RAW = CWD / "data" / "premarket_raw.json"
OUTPUT = CWD / "reports" / "premarket_email.html"


def load_raw():
    if not RAW.exists():
        return None
    with open(RAW) as f:
        return json.load(f)


def render_options_section(options):
    if not options or (len(options) == 1 and "note" in options[0]):
        return '<p style="color:#6a7a6a;font-size:13px;">No unusual options data available for this session.</p>'
    rows = ""
    for o in options[:15]:
        sym = o.get("symbol", "?")
        otype = o.get("type", "—")
        strike = o.get("strike", "—")
        vol = o.get("volume", "—")
        oi = o.get("open_interest", "—")
        rows += f'<tr><td style="padding:6px 12px;border-bottom:1px solid #1e1e1e;color:#e0e0e0;font-weight:600">{sym}</td><td style="padding:6px 12px;border-bottom:1px solid #1e1e1e;color:#8a8a8a">{otype}</td><td style="padding:6px 12px;border-bottom:1px solid #1e1e1e;color:#8a8a8a">{strike}</td><td style="padding:6px 12px;border-bottom:1px solid #1e1e1e;color:#8a8a8a">{vol}</td><td style="padding:6px 12px;border-bottom:1px solid #1e1e1e;color:#8a8a8a">{oi}</td></tr>'
    return f'''<table style="width:100%;border-collapse:collapse;font-size:13px">
<thead><tr style="border-bottom:2px solid #3a9a4a">
<th style="padding:8px 12px;text-align:left;color:#3a9a4a;font-size:10px;letter-spacing:2px;text-transform:uppercase">Symbol</th>
<th style="padding:8px 12px;text-align:left;color:#3a9a4a;font-size:10px;letter-spacing:2px">Type</th>
<th style="padding:8px 12px;text-align:left;color:#3a9a4a;font-size:10px;letter-spacing:2px">Strike</th>
<th style="padding:8px 12px;text-align:left;color:#3a9a4a;font-size:10px;letter-spacing:2px">Volume</th>
<th style="padding:8px 12px;text-align:left;color:#3a9a4a;font-size:10px;letter-spacing:2px">OI</th>
</tr></thead><tbody>{rows}</tbody></table>'''


def render_earnings_section(earnings):
    if not earnings or (len(earnings) == 1 and "note" in earnings[0]):
        return '<p style="color:#6a7a6a;font-size:13px;">No earnings data available for this session.</p>'
    items = ""
    for e in earnings[:12]:
        sym = e.get("symbol", "?")
        company = e.get("company", "")
        call_time = e.get("call_time", "—")
        eps_est = e.get("eps_estimate", "—")
        items += f'<div style="display:inline-block;background:#1a1a1a;border:1px solid #2a2a2a;border-radius:8px;padding:12px 16px;margin:4px;min-width:140px"><div style="font-weight:700;color:#e0e0e0;font-size:15px">{sym}</div><div style="color:#6a7a6a;font-size:11px;margin-top:2px">{company}</div><div style="color:#3a9a4a;font-size:11px;margin-top:4px">{call_time} &bull; Est: {eps_est}</div></div>'
    return f'<div style="display:flex;flex-wrap:wrap;gap:4px">{items}</div>'


def render_levels_section(key_levels):
    if not key_levels:
        return '<p style="color:#6a7a6a;font-size:13px;">No key levels data available.</p>'
    cards = ""
    for ticker, data in key_levels.items():
        price = data.get("price", "—")
        prev = data.get("prev_close", "—")
        high = data.get("day_high", "—")
        low = data.get("day_low", "—")
        ma50 = data.get("50dma", "—")
        ma200 = data.get("200dma", "—")

        change = ""
        if isinstance(price, (int, float)) and isinstance(prev, (int, float)) and prev > 0:
            pct = ((price - prev) / prev) * 100
            color = "#3a9a4a" if pct >= 0 else "#e04040"
            change = f'<span style="color:{color};font-size:13px;font-weight:600">{pct:+.2f}%</span>'

        cards += f'''<div style="flex:1;min-width:200px;background:#1a1a1a;border:1px solid #2a2a2a;border-radius:10px;padding:20px">
<div style="font-size:18px;font-weight:800;color:#f0f0f0;margin-bottom:4px">{ticker} {change}</div>
<div style="font-size:28px;font-weight:800;color:#e0e0e0;margin-bottom:12px">{price if isinstance(price,(int,float)) else price}</div>
<div style="font-size:11px;color:#6a7a6a;line-height:1.8">
High: <span style="color:#c0c0c0">{high}</span> &bull; Low: <span style="color:#c0c0c0">{low}</span><br>
50 DMA: <span style="color:#c0c0c0">{ma50}</span> &bull; 200 DMA: <span style="color:#c0c0c0">{ma200}</span>
</div></div>'''
    return f'<div style="display:flex;gap:16px;flex-wrap:wrap">{cards}</div>'


def render_sentiment():
    """Static sentiment section — would be dynamic with live data."""
    return '''<div style="display:flex;gap:16px;flex-wrap:wrap">
<div style="flex:1;min-width:140px;background:#1a1a1a;border:1px solid #2a2a2a;border-radius:10px;padding:16px;text-align:center">
<div style="font-size:11px;color:#6a7a6a;text-transform:uppercase;letter-spacing:2px;margin-bottom:8px">Futures</div>
<div style="font-size:24px;font-weight:800;color:#3a9a4a">Neutral</div>
</div>
<div style="flex:1;min-width:140px;background:#1a1a1a;border:1px solid #2a2a2a;border-radius:10px;padding:16px;text-align:center">
<div style="font-size:11px;color:#6a7a6a;text-transform:uppercase;letter-spacing:2px;margin-bottom:8px">VIX</div>
<div style="font-size:24px;font-weight:800;color:#e0e0e0">—</div>
</div>
<div style="flex:1;min-width:140px;background:#1a1a1a;border:1px solid #2a2a2a;border-radius:10px;padding:16px;text-align:center">
<div style="font-size:11px;color:#6a7a6a;text-transform:uppercase;letter-spacing:2px;margin-bottom:8px">Put/Call</div>
<div style="font-size:24px;font-weight:800;color:#e0e0e0">—</div>
</div>
<div style="flex:1;min-width:140px;background:#1a1a1a;border:1px solid #2a2a2a;border-radius:10px;padding:16px;text-align:center">
<div style="font-size:11px;color:#6a7a6a;text-transform:uppercase;letter-spacing:2px;margin-bottom:8px">Social Buzz</div>
<div style="font-size:24px;font-weight:800;color:#e0e0e0">—</div>
</div>
</div>'''


def main():
    raw = load_raw()
    now = datetime.now(timezone.utc).strftime("%d %B %Y — %H:%M UTC")

    options_html = render_options_section(raw.get("unusual_options", []) if raw else [])
    earnings_html = render_earnings_section(raw.get("earnings_calendar", []) if raw else [])
    levels_html = render_levels_section(raw.get("key_levels", {}) if raw else {})
    sentiment_html = render_sentiment()
    scraped = raw.get("scraped_at", "Unknown") if raw else "No data"

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>PreMarket Pulse Briefing — {now}</title>
</head>
<body style="margin:0;padding:32px 16px;background:#0d0d0d;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif;color:#e0e0e0">
<div style="max-width:680px;margin:0 auto;background:#141414;border:1px solid #2a2a2a;border-radius:12px;overflow:hidden">

<!-- HEADER -->
<div style="background:linear-gradient(135deg,#0f1923 0%,#1a2a1a 50%,#0f1923 100%);border-bottom:1px solid #1e3a1e;padding:28px 32px;text-align:center">
<div style="font-size:11px;letter-spacing:4px;text-transform:uppercase;color:#3a9a4a;font-weight:600;margin-bottom:8px">PreMarket Pulse</div>
<div style="font-size:22px;font-weight:700;color:#f0f0f0;margin-bottom:4px">Pre-Market Intelligence Briefing</div>
<div style="font-size:13px;color:#6a7a6a">{now}</div>
<div style="margin-top:10px;font-size:11px;letter-spacing:2px;text-transform:uppercase;color:#3a9a4a;opacity:0.8">US Markets Only</div>
</div>

<!-- OPTIONS FLOW -->
<div style="padding:24px 32px;border-bottom:1px solid #1e1e1e">
<div style="font-size:10px;letter-spacing:3px;text-transform:uppercase;color:#3a9a4a;font-weight:700;margin-bottom:16px">Unusual Options Flow</div>
{options_html}
</div>

<!-- EARNINGS WATCH -->
<div style="padding:24px 32px;border-bottom:1px solid #1e1e1e">
<div style="font-size:10px;letter-spacing:3px;text-transform:uppercase;color:#3a9a4a;font-weight:700;margin-bottom:16px">Earnings Watch</div>
{earnings_html}
</div>

<!-- KEY LEVELS -->
<div style="padding:24px 32px;border-bottom:1px solid #1e1e1e">
<div style="font-size:10px;letter-spacing:3px;text-transform:uppercase;color:#3a9a4a;font-weight:700;margin-bottom:16px">Key Levels — SPY / QQQ / IWM</div>
{levels_html}
</div>

<!-- MARKET SENTIMENT -->
<div style="padding:24px 32px">
<div style="font-size:10px;letter-spacing:3px;text-transform:uppercase;color:#3a9a4a;font-weight:700;margin-bottom:16px">Market Sentiment</div>
{sentiment_html}
</div>

<!-- FOOTER -->
<div style="padding:16px 32px;border-top:1px solid #1e1e1e;text-align:center;font-size:11px;color:#4a4a4a">
PreMarket Pulse by AI HQ &bull; Data scraped {scraped} &bull; Not financial advice
</div>

</div>
</body>
</html>'''

    with open(OUTPUT, "w") as f:
        f.write(html)
    print(f"[PreMarket Synthesize] Briefing saved to {OUTPUT}")


if __name__ == "__main__":
    main()
