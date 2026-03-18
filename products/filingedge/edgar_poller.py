"""
FilingEdge — EDGAR Poller
Fetches 8-K and Form 4 filings from SEC EDGAR EFTS (full-text search) API.
Rate-limited to comply with SEC's 10 req/sec policy.
"""

import json
import time
from dataclasses import dataclass, asdict
from typing import List, Optional
from urllib.request import Request, urlopen
from urllib.parse import urlencode, quote

# SEC requires a User-Agent header identifying the caller
USER_AGENT = "FilingEdge/1.0 (contact@filingedge.com)"

# Rate limiter: max 10 requests per second
_last_request_time = 0.0
_MIN_INTERVAL = 0.1  # 100ms between requests = 10 req/sec max

# EDGAR endpoints
EFTS_BASE = "https://efts.sec.gov/LATEST/search-index"
EDGAR_FILINGS_BASE = "https://www.sec.gov/Archives/edgar/data"


@dataclass
class Filing:
    company: str
    cik: str
    form_type: str
    date_filed: str
    link: str
    ticker: str = ""
    description: str = ""
    items: str = ""


def _rate_limit():
    """Enforce SEC rate limit of 10 req/sec."""
    global _last_request_time
    now = time.time()
    elapsed = now - _last_request_time
    if elapsed < _MIN_INTERVAL:
        time.sleep(_MIN_INTERVAL - elapsed)
    _last_request_time = time.time()


def _fetch_url(url: str) -> bytes:
    """Fetch URL with rate limiting and proper User-Agent."""
    _rate_limit()
    req = Request(url, headers={
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
    })
    resp = urlopen(req, timeout=15)
    return resp.read()


def _build_filing_url(cik: str, accession: str) -> str:
    """Build a direct link to the filing on EDGAR."""
    cik_clean = cik.lstrip("0") or "0"
    acc_clean = accession.replace("-", "")
    return f"https://www.sec.gov/Archives/edgar/data/{cik_clean}/{acc_clean}/{accession}-index.htm"


def fetch_recent_filings(form_type: str = "8-K", count: int = 20) -> List[Filing]:
    """
    Fetch recent SEC filings via EDGAR EFTS full-text search API.

    Args:
        form_type: SEC form type ("8-K", "4", etc.)
        count: Number of results (max 100)

    Returns:
        List of Filing objects.
    """
    count = min(count, 100)

    params = urlencode({
        "q": f'"{form_type}"',
        "forms": form_type,
        "dateRange": "custom",
        "startdt": _recent_date(days=7),
        "enddt": _today(),
    })
    url = f"{EFTS_BASE}?{params}"

    try:
        raw = _fetch_url(url)
        data = json.loads(raw)
    except Exception as e:
        print(f"[edgar_poller] EFTS fetch failed: {e}")
        return []

    return _parse_efts_response(data, limit=count)


def _today() -> str:
    """Today's date as YYYY-MM-DD."""
    return time.strftime("%Y-%m-%d")


def _recent_date(days: int = 7) -> str:
    """Date N days ago as YYYY-MM-DD."""
    return time.strftime("%Y-%m-%d", time.localtime(time.time() - 86400 * days))


def _parse_efts_response(data: dict, limit: int = 20) -> List[Filing]:
    """Parse EFTS JSON response into Filing objects."""
    filings = []
    hits = data.get("hits", {}).get("hits", [])

    for hit in hits[:limit]:
        src = hit.get("_source", {})
        display_names = src.get("display_names", [])
        ciks = src.get("ciks", [])
        accession = src.get("adsh", "")

        # Extract company name and ticker from display_names
        # Format: "Company Name  (TICKER)  (CIK 0001234567)"
        company = ""
        ticker = ""
        if display_names:
            dn = display_names[0]
            # Parse "Company Name  (TICKER)  (CIK ...)"
            if "(" in dn:
                parts = dn.split("(")
                company = parts[0].strip()
                if len(parts) >= 2:
                    ticker = parts[1].split(")")[0].strip()
                    # Skip if it's a CIK, not a ticker
                    if ticker.startswith("CIK"):
                        ticker = ""

        cik = ciks[0] if ciks else ""
        filing_url = _build_filing_url(cik, accession) if cik and accession else ""
        items_list = src.get("items", [])

        filings.append(Filing(
            company=company,
            cik=cik,
            form_type=src.get("form", src.get("root_forms", [""])[0] if src.get("root_forms") else ""),
            date_filed=src.get("file_date", ""),
            link=filing_url,
            ticker=ticker,
            description=src.get("file_description", ""),
            items=", ".join(items_list) if items_list else "",
        ))

    return filings


def fetch_filings_for_tickers(
    tickers: List[str],
    form_types: Optional[List[str]] = None,
) -> List[Filing]:
    """
    Fetch filings for specific ticker symbols via EFTS.

    Args:
        tickers: List of US stock ticker symbols (e.g., ["AAPL", "TSLA"])
        form_types: Form types to search for (default: ["8-K", "4"])

    Returns:
        List of Filing objects across all tickers and form types.
    """
    if form_types is None:
        form_types = ["8-K", "4"]

    all_filings = []

    for ticker in tickers:
        for ftype in form_types:
            params = urlencode({
                "q": f'"{ticker}"',
                "forms": ftype,
                "dateRange": "custom",
                "startdt": _recent_date(days=30),
                "enddt": _today(),
            })
            url = f"{EFTS_BASE}?{params}"

            try:
                raw = _fetch_url(url)
                data = json.loads(raw)
                filings = _parse_efts_response(data, limit=10)
                all_filings.extend(filings)
            except Exception as e:
                print(f"[edgar_poller] Error fetching {ftype} for {ticker}: {e}")
                continue

    return all_filings


def filings_to_dicts(filings: List[Filing]) -> List[dict]:
    """Convert Filing objects to plain dicts for JSON serialization."""
    return [asdict(f) for f in filings]


# CLI test
if __name__ == "__main__":
    print("Fetching recent 8-K filings from EDGAR EFTS...")
    results = fetch_recent_filings("8-K", count=5)
    for f in results:
        print(f"  {f.form_type} | {f.company} ({f.ticker}) | {f.date_filed} | {f.link}")

    print(f"\nFetched {len(results)} filings")
    print(json.dumps(filings_to_dicts(results), indent=2))
