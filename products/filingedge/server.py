"""
FilingEdge — FastAPI Backend MVP
AI-powered SEC filing alerts for US market traders.

Endpoints:
  POST /register          — User registration
  POST /login             — User login (returns token)
  GET  /watchlist          — Get user's watchlist
  POST /watchlist          — Add ticker to watchlist
  DELETE /watchlist/{ticker} — Remove ticker from watchlist
  GET  /filings            — Fetch latest SEC filings (optional ?type=8-K&ticker=AAPL)
  GET  /filings/watchlist  — Fetch filings for user's watchlist tickers
  GET  /health             — Health check

Run:  uvicorn products.filingedge.server:app --port 8100 --reload
"""

import hashlib
import json
import os
import secrets
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr

# Local EDGAR poller
from products.filingedge.edgar_poller import (
    fetch_recent_filings,
    fetch_filings_for_tickers,
    filings_to_dicts,
)

# ── App Setup ─────────────────────────────────────────────────────────────────

app = FastAPI(
    title="FilingEdge API",
    description="AI-powered SEC filing alerts for US market traders",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Storage (JSON file for MVP) ──────────────────────────────────────────────

DATA_DIR = Path(__file__).resolve().parent / "data"
DATA_DIR.mkdir(exist_ok=True)
USERS_FILE = DATA_DIR / "users.json"
WATCHLISTS_FILE = DATA_DIR / "watchlists.json"

# Tier limits
TIER_LIMITS = {
    "starter": 25,
    "pro": 150,
    "free": 5,
}


def _load_json(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text())
    return {}


def _save_json(path: Path, data: dict):
    path.write_text(json.dumps(data, indent=2))


def _hash_password(password: str, salt: str) -> str:
    return hashlib.sha256(f"{salt}:{password}".encode()).hexdigest()


# ── Models ────────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    tier: str = "free"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class WatchlistAddRequest(BaseModel):
    ticker: str


# ── Auth ──────────────────────────────────────────────────────────────────────

def get_current_user(authorization: Optional[str] = Header(None)) -> dict:
    """Extract user from Bearer token."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    token = authorization.split(" ", 1)[1]
    users = _load_json(USERS_FILE)

    for email, user_data in users.items():
        if user_data.get("token") == token:
            return {"email": email, **user_data}

    raise HTTPException(status_code=401, detail="Invalid token")


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"ok": True, "service": "FilingEdge", "version": "0.1.0"}


@app.post("/register")
def register(req: RegisterRequest):
    """Register a new user account."""
    users = _load_json(USERS_FILE)

    if req.email in users:
        raise HTTPException(status_code=409, detail="Email already registered")

    if len(req.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    tier = req.tier.lower()
    if tier not in TIER_LIMITS:
        raise HTTPException(status_code=400, detail=f"Invalid tier. Choose from: {', '.join(TIER_LIMITS.keys())}")

    salt = secrets.token_hex(16)
    token = secrets.token_urlsafe(32)

    users[req.email] = {
        "password_hash": _hash_password(req.password, salt),
        "salt": salt,
        "token": token,
        "tier": tier,
        "created": datetime.now(timezone.utc).isoformat(),
    }
    _save_json(USERS_FILE, users)

    # Initialize empty watchlist
    watchlists = _load_json(WATCHLISTS_FILE)
    if req.email not in watchlists:
        watchlists[req.email] = []
        _save_json(WATCHLISTS_FILE, watchlists)

    return {
        "ok": True,
        "email": req.email,
        "token": token,
        "tier": tier,
        "watchlist_limit": TIER_LIMITS[tier],
    }


@app.post("/login")
def login(req: LoginRequest):
    """Login and get a new token."""
    users = _load_json(USERS_FILE)

    if req.email not in users:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    user = users[req.email]
    if _hash_password(req.password, user["salt"]) != user["password_hash"]:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    # Rotate token on login
    new_token = secrets.token_urlsafe(32)
    users[req.email]["token"] = new_token
    _save_json(USERS_FILE, users)

    return {
        "ok": True,
        "email": req.email,
        "token": new_token,
        "tier": user["tier"],
    }


@app.get("/watchlist")
def get_watchlist(user: dict = Depends(get_current_user)):
    """Get the authenticated user's watchlist."""
    watchlists = _load_json(WATCHLISTS_FILE)
    tickers = watchlists.get(user["email"], [])
    limit = TIER_LIMITS.get(user.get("tier", "free"), 5)

    return {
        "ok": True,
        "tickers": tickers,
        "count": len(tickers),
        "limit": limit,
        "tier": user.get("tier", "free"),
    }


@app.post("/watchlist")
def add_to_watchlist(req: WatchlistAddRequest, user: dict = Depends(get_current_user)):
    """Add a ticker to the user's watchlist."""
    ticker = req.ticker.upper().strip()
    if not ticker or len(ticker) > 5:
        raise HTTPException(status_code=400, detail="Invalid ticker symbol")

    watchlists = _load_json(WATCHLISTS_FILE)
    tickers = watchlists.get(user["email"], [])

    limit = TIER_LIMITS.get(user.get("tier", "free"), 5)
    if len(tickers) >= limit:
        raise HTTPException(
            status_code=403,
            detail=f"Watchlist limit reached ({limit} tickers on {user.get('tier', 'free')} tier). Upgrade to add more.",
        )

    if ticker in tickers:
        raise HTTPException(status_code=409, detail=f"{ticker} already in watchlist")

    tickers.append(ticker)
    watchlists[user["email"]] = tickers
    _save_json(WATCHLISTS_FILE, watchlists)

    return {"ok": True, "ticker": ticker, "watchlist": tickers, "count": len(tickers)}


@app.delete("/watchlist/{ticker}")
def remove_from_watchlist(ticker: str, user: dict = Depends(get_current_user)):
    """Remove a ticker from the user's watchlist."""
    ticker = ticker.upper().strip()
    watchlists = _load_json(WATCHLISTS_FILE)
    tickers = watchlists.get(user["email"], [])

    if ticker not in tickers:
        raise HTTPException(status_code=404, detail=f"{ticker} not in watchlist")

    tickers.remove(ticker)
    watchlists[user["email"]] = tickers
    _save_json(WATCHLISTS_FILE, watchlists)

    return {"ok": True, "removed": ticker, "watchlist": tickers, "count": len(tickers)}


@app.get("/filings")
def get_filings(type: str = "8-K", ticker: Optional[str] = None, count: int = 20):
    """
    Fetch latest SEC filings from EDGAR.

    Query params:
      type   — Form type: "8-K", "4" (default: "8-K")
      ticker — Optional: filter by company ticker
      count  — Number of results (default: 20, max: 100)
    """
    count = max(1, min(count, 100))

    if ticker:
        filings = fetch_filings_for_tickers(
            tickers=[ticker.upper().strip()],
            form_types=[type],
        )
    else:
        filings = fetch_recent_filings(form_type=type, count=count)

    return {
        "ok": True,
        "form_type": type,
        "ticker": ticker,
        "count": len(filings),
        "filings": filings_to_dicts(filings),
    }


@app.get("/filings/watchlist")
def get_watchlist_filings(
    type: Optional[str] = None,
    user: dict = Depends(get_current_user),
):
    """Fetch recent filings for all tickers in the user's watchlist."""
    watchlists = _load_json(WATCHLISTS_FILE)
    tickers = watchlists.get(user["email"], [])

    if not tickers:
        return {"ok": True, "filings": [], "count": 0, "message": "Watchlist is empty. Add tickers first."}

    form_types = [type] if type else ["8-K", "4"]
    filings = fetch_filings_for_tickers(tickers=tickers, form_types=form_types)

    return {
        "ok": True,
        "tickers": tickers,
        "form_types": form_types,
        "count": len(filings),
        "filings": filings_to_dicts(filings),
    }


# ── Run standalone ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8100)
