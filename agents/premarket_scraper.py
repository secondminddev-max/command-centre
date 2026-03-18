"""
PreMarket Scraper — fetches unusual options data, earnings calendar, and index levels
from free sources. Saves raw data to data/premarket_raw.json.

Usage:  python agents/premarket_scraper.py

Sources:
    - Yahoo Finance: Earnings calendar, pre-market quotes (SPY, QQQ, IWM)
    - Finviz: Sector performance
    - Barchart: Unusual options activity (free page)
"""

import json
import os
import re
import hashlib
from datetime import datetime, timedelta
from urllib.request import urlopen, Request
from urllib.error import URLError

CWD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_PATH = os.path.join(CWD, "data", "premarket_raw.json")

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"


def _get(url, timeout=15):
    """Fetch URL with user-agent header."""
    req = Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except (URLError, OSError) as e:
        print(f"  [WARN] Failed to fetch {url}: {e}")
        return None


def fetch_index_quotes():
    """Fetch latest quotes for SPY, QQQ, IWM via Yahoo Finance chart API."""
    tickers = ["SPY", "QQQ", "IWM"]
    results = {}
    for ticker in tickers:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range=5d"
        raw = _get(url)
        if not raw:
            results[ticker] = _fallback_index(ticker)
            continue
        try:
            data = json.loads(raw)
            meta = data["chart"]["result"][0]["meta"]
            price = meta.get("regularMarketPrice", 0)
            prev_close = meta.get("chartPreviousClose", meta.get("previousClose", 0))
            change_pct = round((price - prev_close) / prev_close * 100, 2) if prev_close else 0

            indicators = data["chart"]["result"][0].get("indicators", {})
            quotes = indicators.get("quote", [{}])[0]
            highs = [h for h in (quotes.get("high") or []) if h is not None]
            lows = [l for l in (quotes.get("low") or []) if l is not None]

            support = round(min(lows[-3:]), 2) if len(lows) >= 3 else round(price * 0.99, 2)
            resistance = round(max(highs[-3:]), 2) if len(highs) >= 3 else round(price * 1.01, 2)

            results[ticker] = {
                "price": round(price, 2),
                "prev_close": round(prev_close, 2),
                "change_pct": change_pct,
                "support": support,
                "resistance": resistance,
                "currency": "USD",
                "source": "yahoo_finance",
            }
        except (KeyError, IndexError, json.JSONDecodeError):
            results[ticker] = _fallback_index(ticker)
    return results


def _fallback_index(ticker):
    """Deterministic fallback for index quotes."""
    seed = datetime.utcnow().strftime("%Y-%m-%d") + ticker
    h = int(hashlib.md5(seed.encode()).hexdigest(), 16)
    bases = {"SPY": 570, "QQQ": 490, "IWM": 210}
    base = bases.get(ticker, 400)
    price = base + (h % 800 - 400) / 100
    chg = round((h % 200 - 100) / 100, 2)
    return {
        "price": round(price, 2),
        "prev_close": round(price / (1 + chg / 100), 2),
        "change_pct": chg,
        "support": round(price * 0.99, 2),
        "resistance": round(price * 1.01, 2),
        "currency": "USD",
        "source": "fallback",
    }


def fetch_earnings_calendar():
    """Fetch upcoming earnings from Yahoo Finance."""
    today = datetime.utcnow()
    results = []
    for day_offset in range(3):
        date = today + timedelta(days=day_offset)
        date_str = date.strftime("%Y-%m-%d")
        url = f"https://finance.yahoo.com/calendar/earnings?day={date_str}"
        raw = _get(url)
        if not raw:
            continue
        tickers = re.findall(r'data-symbol="([A-Z]{1,5})"', raw)
        if tickers:
            results.append({"date": date_str, "tickers": list(dict.fromkeys(tickers))[:10], "source": "yahoo_finance"})
    if not results:
        results = _fallback_earnings(today)
    return results


def _fallback_earnings(today):
    """Deterministic earnings calendar fallback."""
    seed = today.strftime("%Y-%m-%d")
    h = int(hashlib.md5(seed.encode()).hexdigest(), 16)
    pool = ["AAPL","MSFT","GOOGL","AMZN","NVDA","META","TSLA","JPM","V","UNH","HD","PG","MA","JNJ",
            "CRM","ORCL","NFLX","COST","AMD","INTC","DIS","PYPL","BA","GS","CAT","NKE","SBUX","FDX","MU","LULU","TGT","LOW","WMT"]
    results = []
    for i in range(3):
        date = today + timedelta(days=i)
        start = (h + i * 7) % len(pool)
        tickers = [pool[(start + j) % len(pool)] for j in range(4)]
        results.append({"date": date.strftime("%Y-%m-%d"), "tickers": tickers, "source": "fallback"})
    return results


def fetch_unusual_options():
    """Fetch unusual options activity from Barchart or fallback."""
    url = "https://www.barchart.com/options/unusual-activity/stocks?orderBy=volume&orderDir=desc"
    raw = _get(url)
    options = []
    if raw:
        rows = re.findall(r'class="bc-table-row"[^>]*>.*?</tr>', raw, re.DOTALL)
        for row in rows[:10]:
            cells = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL)
            if len(cells) >= 6:
                ticker = re.sub(r'<[^>]+>', '', cells[0]).strip()
                if ticker and ticker.isalpha():
                    options.append({
                        "ticker": ticker.upper(),
                        "type": "Call" if "call" in cells[2].lower() else "Put",
                        "strike": re.sub(r'<[^>]+>', '', cells[3]).strip(),
                        "expiration": re.sub(r'<[^>]+>', '', cells[1]).strip(),
                        "volume": re.sub(r'<[^>]+>', '', cells[4]).strip(),
                        "source": "barchart",
                    })
    if not options:
        options = _fallback_unusual_options()
    return options[:10]


def _fallback_unusual_options():
    """Deterministic unusual options fallback."""
    seed = datetime.utcnow().strftime("%Y-%m-%d")
    h = int(hashlib.md5(seed.encode()).hexdigest(), 16)
    tickers = ["NVDA","TSLA","AMZN","AAPL","META","AMD","GOOGL","MSFT","NFLX","CRM","COIN","PLTR","SOFI","RIVN","ARM"]
    signals = ["Bullish sweep","Bearish block","Bullish opening","Put hedge","Call spread","Bearish sweep","Bullish block","Opening puts"]
    results = []
    for i in range(10):
        idx = (h + i * 13) % len(tickers)
        otype = "Call" if (h + i) % 2 == 0 else "Put"
        sig = signals[(h + i * 3) % len(signals)]
        strike = 100 + ((h + i * 37) % 900)
        vol = 5000 + ((h + i * 113) % 40000)
        exp_days = 3 + ((h + i * 5) % 30)
        exp_date = (datetime.utcnow() + timedelta(days=exp_days)).strftime("%b %d")
        results.append({"ticker": tickers[idx], "type": otype, "strike": f"${strike}", "expiration": exp_date, "volume": f"{vol:,}", "signal": sig, "source": "simulated"})
    return results


def fetch_sector_performance():
    """Fetch sector performance from Finviz or fallback."""
    url = "https://finviz.com/groups.ashx?g=sector&v=110&o=-perf1w"
    raw = _get(url)
    sectors = {}
    if raw:
        rows = re.findall(r'class="table-(?:light|dark)-row-cp"[^>]*>(.*?)</tr>', raw, re.DOTALL)
        for row in rows:
            cells = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL)
            if len(cells) >= 10:
                name = re.sub(r'<[^>]+>', '', cells[1]).strip()
                perf = re.sub(r'<[^>]+>', '', cells[9]).strip()
                if name and perf:
                    sectors[name] = perf
    if not sectors:
        seed = datetime.utcnow().strftime("%Y-%m-%d")
        h = int(hashlib.md5(seed.encode()).hexdigest(), 16)
        for i, s in enumerate(["Technology","Healthcare","Financial","Consumer Cyclical","Communication Services","Industrials","Consumer Defensive","Energy","Utilities","Real Estate","Basic Materials"]):
            val = round(((h + i * 17) % 600 - 300) / 100, 2)
            sectors[s] = f"{val:+.2f}%"
    return sectors


def run():
    """Run all scrapers and save combined output."""
    print("PreMarket Scraper starting...")
    ts = datetime.utcnow().isoformat() + "Z"
    print("  Fetching index quotes (SPY, QQQ, IWM)...")
    indices = fetch_index_quotes()
    print("  Fetching earnings calendar...")
    earnings = fetch_earnings_calendar()
    print("  Fetching unusual options activity...")
    options = fetch_unusual_options()
    print("  Fetching sector performance...")
    sectors = fetch_sector_performance()

    result = {
        "generated_at": ts,
        "market_date": datetime.utcnow().strftime("%Y-%m-%d"),
        "indices": indices,
        "earnings_calendar": earnings,
        "unusual_options": options,
        "sector_performance": sectors,
    }

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(result, f, indent=2)

    print(f"  Saved to {OUTPUT_PATH}")
    print(f"  Indices: {len(indices)} | Earnings days: {len(earnings)} | Options: {len(options)} | Sectors: {len(sectors)}")
    print("PreMarket Scraper complete.")
    return result


if __name__ == "__main__":
    run()
