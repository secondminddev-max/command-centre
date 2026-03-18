#!/usr/bin/env python3
"""PreMarket Pulse — Scraping Pipeline
Scrapes: (a) unusual options activity from Barchart, (b) earnings calendar from Yahoo Finance,
(c) SPY/QQQ/IWM key price levels. Saves to data/premarket_raw.json.
"""
import json, os, re, sys
from datetime import datetime, timezone
from pathlib import Path

CWD = Path(__file__).resolve().parent.parent
DATA_DIR = CWD / "data"
DATA_DIR.mkdir(exist_ok=True)
OUTPUT = DATA_DIR / "premarket_raw.json"

# ---------- helpers ----------

def _safe_get(url, headers=None, timeout=15):
    """Fetch URL, return text or None."""
    import urllib.request, urllib.error
    req = urllib.request.Request(url, headers=headers or {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"[WARN] fetch failed {url}: {e}", file=sys.stderr)
        return None

# ---------- scrapers ----------

def scrape_unusual_options():
    """Scrape unusual options activity from Barchart free page."""
    url = "https://www.barchart.com/options/unusual-activity/stocks"
    html = _safe_get(url)
    entries = []
    if html:
        # Parse table rows — Barchart renders a data table
        # Look for JSON data blob that Barchart embeds
        match = re.search(r'"data":\s*(\[.*?\])\s*[,}]', html, re.DOTALL)
        if match:
            try:
                raw = json.loads(match.group(1))
                for item in raw[:25]:  # top 25
                    entries.append({
                        "symbol": item.get("baseSymbol", item.get("symbol", "?")),
                        "type": item.get("symbolType", ""),
                        "strike": item.get("strikePrice", ""),
                        "expiry": item.get("expirationDate", ""),
                        "volume": item.get("volume", 0),
                        "open_interest": item.get("openInterest", 0),
                        "vol_oi_ratio": item.get("volumeOpenInterestRatio", 0),
                    })
            except json.JSONDecodeError:
                pass
        if not entries:
            # Fallback: regex scrape table
            rows = re.findall(r'<tr[^>]*>(.*?)</tr>', html, re.DOTALL)
            for row in rows[:25]:
                cells = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL)
                if len(cells) >= 5:
                    symbol = re.sub(r'<[^>]+>', '', cells[0]).strip()
                    if symbol and symbol.isalpha() and len(symbol) <= 5:
                        entries.append({
                            "symbol": symbol,
                            "type": re.sub(r'<[^>]+>', '', cells[1]).strip(),
                            "strike": re.sub(r'<[^>]+>', '', cells[2]).strip(),
                            "volume": re.sub(r'<[^>]+>', '', cells[3]).strip(),
                            "open_interest": re.sub(r'<[^>]+>', '', cells[4]).strip(),
                        })
    if not entries:
        entries = [{"note": "Barchart scrape returned no data — site may require JS or auth. Retry later."}]
    return entries


def scrape_earnings_calendar():
    """Scrape earnings calendar from Yahoo Finance."""
    url = "https://finance.yahoo.com/calendar/earnings"
    html = _safe_get(url)
    entries = []
    if html:
        # Yahoo embeds earnings data in JSON
        match = re.search(r'"rows":\s*(\[.*?\])\s*[,}]', html, re.DOTALL)
        if match:
            try:
                raw = json.loads(match.group(1))
                for item in raw[:30]:
                    entries.append({
                        "symbol": item.get("ticker", ""),
                        "company": item.get("companyshortname", ""),
                        "call_time": item.get("startdatetimetype", ""),
                        "eps_estimate": item.get("epsestimate", ""),
                        "eps_actual": item.get("epsactual", ""),
                    })
            except json.JSONDecodeError:
                pass
        if not entries:
            # Fallback regex
            rows = re.findall(r'<tr[^>]*>(.*?)</tr>', html, re.DOTALL)
            for row in rows[:30]:
                cells = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL)
                if len(cells) >= 3:
                    symbol = re.sub(r'<[^>]+>', '', cells[0]).strip()
                    company = re.sub(r'<[^>]+>', '', cells[1]).strip()
                    if symbol and len(symbol) <= 6:
                        entries.append({"symbol": symbol, "company": company})
    if not entries:
        entries = [{"note": "Yahoo earnings scrape returned no data — site may require JS. Retry later."}]
    return entries


def scrape_key_levels():
    """Scrape SPY/QQQ/IWM key price levels from Yahoo Finance quotes."""
    levels = {}
    for ticker in ["SPY", "QQQ", "IWM"]:
        url = f"https://finance.yahoo.com/quote/{ticker}/"
        html = _safe_get(url)
        data = {"ticker": ticker}
        if html:
            # Extract key data points
            for label, pattern in [
                ("price", r'"regularMarketPrice":\{"raw":([\d.]+)'),
                ("prev_close", r'"regularMarketPreviousClose":\{"raw":([\d.]+)'),
                ("open", r'"regularMarketOpen":\{"raw":([\d.]+)'),
                ("day_high", r'"regularMarketDayHigh":\{"raw":([\d.]+)'),
                ("day_low", r'"regularMarketDayLow":\{"raw":([\d.]+)'),
                ("52w_high", r'"fiftyTwoWeekHigh":\{"raw":([\d.]+)'),
                ("52w_low", r'"fiftyTwoWeekLow":\{"raw":([\d.]+)'),
                ("50dma", r'"fiftyDayAverage":\{"raw":([\d.]+)'),
                ("200dma", r'"twoHundredDayAverage":\{"raw":([\d.]+)'),
            ]:
                m = re.search(pattern, html)
                if m:
                    data[label] = float(m.group(1))
        levels[ticker] = data
    return levels


# ---------- main ----------

def main():
    print("[PreMarket Scraper] Starting…")
    ts = datetime.now(timezone.utc).isoformat()

    options = scrape_unusual_options()
    print(f"  Options flow: {len(options)} entries")

    earnings = scrape_earnings_calendar()
    print(f"  Earnings: {len(earnings)} entries")

    key_levels = scrape_key_levels()
    print(f"  Key levels: {list(key_levels.keys())}")

    payload = {
        "scraped_at": ts,
        "unusual_options": options,
        "earnings_calendar": earnings,
        "key_levels": key_levels,
    }

    with open(OUTPUT, "w") as f:
        json.dump(payload, f, indent=2)
    print(f"[PreMarket Scraper] Saved to {OUTPUT}")


if __name__ == "__main__":
    main()
