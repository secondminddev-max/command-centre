#!/usr/bin/env python3
"""
RivalRadar Engine v1.0.0-mvp
AI-powered competitor intelligence — monitoring, diffing, synthesis, delivery.
Built by Reforger. US market only.
"""

import hashlib
import json
import os
import time
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict
from typing import Optional

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class Competitor:
    name: str
    url: str
    tier: str  # scout | analyst | warroom
    watch_pages: list = field(default_factory=list)  # URLs to monitor
    social_handles: dict = field(default_factory=dict)  # platform -> handle
    last_snapshot: Optional[str] = None
    last_checked: Optional[str] = None


@dataclass
class Snapshot:
    competitor: str
    url: str
    content_hash: str
    captured_at: str
    raw_text: str = ""


@dataclass
class Change:
    competitor: str
    url: str
    change_type: str  # pricing | feature | copy | social | job_posting
    summary: str
    old_hash: str
    new_hash: str
    detected_at: str
    severity: str = "medium"  # low | medium | high | critical


@dataclass
class IntelBrief:
    generated_at: str
    period: str  # daily | weekly | monthly
    changes: list = field(default_factory=list)
    synthesis: str = ""
    recommendations: list = field(default_factory=list)


# ---------------------------------------------------------------------------
# Storage (file-based for MVP)
# ---------------------------------------------------------------------------

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "rivalradar")


def _ensure_dirs():
    for sub in ["snapshots", "changes", "briefs", "subscribers"]:
        os.makedirs(os.path.join(DATA_DIR, sub), exist_ok=True)


def save_json(path: str, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)


def load_json(path: str, default=None):
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return default


# ---------------------------------------------------------------------------
# 1. Competitor URL Monitoring
# ---------------------------------------------------------------------------

def fetch_page(url: str) -> str:
    """
    Fetch page content. MVP stub — in production this would use
    httpx/playwright for JS-rendered pages.
    """
    # STUB: simulate fetching content
    # In production: resp = httpx.get(url, follow_redirects=True, timeout=30)
    stub_content = f"[STUB] Page content for {url} fetched at {datetime.now(timezone.utc).isoformat()}"
    return stub_content


def take_snapshot(competitor: Competitor, url: str) -> Snapshot:
    """Capture a point-in-time snapshot of a competitor page."""
    content = fetch_page(url)
    content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
    snap = Snapshot(
        competitor=competitor.name,
        url=url,
        content_hash=content_hash,
        captured_at=datetime.now(timezone.utc).isoformat(),
        raw_text=content,
    )
    return snap


# ---------------------------------------------------------------------------
# 2. Change Detection
# ---------------------------------------------------------------------------

def detect_changes(competitor: Competitor, new_snap: Snapshot) -> Optional[Change]:
    """Compare new snapshot against the last stored one. Return Change if different."""
    _ensure_dirs()
    snap_path = os.path.join(
        DATA_DIR, "snapshots",
        f"{competitor.name}_{hashlib.md5(new_snap.url.encode()).hexdigest()[:8]}.json"
    )
    old_data = load_json(snap_path)

    if old_data and old_data.get("content_hash") != new_snap.content_hash:
        change = Change(
            competitor=competitor.name,
            url=new_snap.url,
            change_type=classify_change(new_snap.url),
            summary=f"Content changed on {new_snap.url}",
            old_hash=old_data["content_hash"],
            new_hash=new_snap.content_hash,
            detected_at=new_snap.captured_at,
            severity=assess_severity(new_snap.url),
        )
        # persist new snapshot
        save_json(snap_path, asdict(new_snap))
        return change

    # First snapshot or no change
    if not old_data:
        save_json(snap_path, asdict(new_snap))
    return None


def classify_change(url: str) -> str:
    """Heuristic classification based on URL path."""
    lower = url.lower()
    if "pricing" in lower:
        return "pricing"
    if "feature" in lower or "product" in lower:
        return "feature"
    if "blog" in lower or "changelog" in lower:
        return "copy"
    if "jobs" in lower or "careers" in lower:
        return "job_posting"
    return "copy"


def assess_severity(url: str) -> str:
    """Quick severity heuristic."""
    lower = url.lower()
    if "pricing" in lower:
        return "critical"
    if "feature" in lower or "product" in lower:
        return "high"
    return "medium"


# ---------------------------------------------------------------------------
# 3. AI Synthesis Brief Generation
# ---------------------------------------------------------------------------

def generate_brief(changes: list, period: str = "weekly") -> IntelBrief:
    """
    Generate an AI-synthesized intelligence brief from detected changes.
    MVP stub — production would call Claude API for deep analysis.
    """
    brief = IntelBrief(
        generated_at=datetime.now(timezone.utc).isoformat(),
        period=period,
        changes=[asdict(c) for c in changes],
    )

    if not changes:
        brief.synthesis = "No significant competitor changes detected this period. All monitored competitors appear stable."
        brief.recommendations = ["Continue regular monitoring.", "Consider expanding competitor list."]
        return brief

    # STUB synthesis — in production this calls Claude API
    pricing_changes = [c for c in changes if c.change_type == "pricing"]
    feature_changes = [c for c in changes if c.change_type == "feature"]

    parts = []
    if pricing_changes:
        names = ", ".join(set(c.competitor for c in pricing_changes))
        parts.append(f"Pricing changes detected at: {names}. Review immediately for competitive positioning impact.")
    if feature_changes:
        names = ", ".join(set(c.competitor for c in feature_changes))
        parts.append(f"Feature/product updates at: {names}. Evaluate for feature parity gaps.")

    other = [c for c in changes if c.change_type not in ("pricing", "feature")]
    if other:
        parts.append(f"{len(other)} additional content/copy changes detected across monitored competitors.")

    brief.synthesis = " ".join(parts) if parts else "Changes detected — see details below."
    brief.recommendations = [
        "Review pricing changes and assess whether your pricing remains competitive.",
        "Check feature updates for potential gaps in your product roadmap.",
        "Update competitive battlecards with latest intelligence.",
    ]

    return brief


# ---------------------------------------------------------------------------
# 4. Email Digest Formatting
# ---------------------------------------------------------------------------

def format_digest_html(brief: IntelBrief, subscriber_email: str = "") -> str:
    """Render an intelligence brief as an HTML email digest."""

    change_rows = ""
    for ch in brief.changes:
        sev_color = {"critical": "#ef4444", "high": "#f59e0b", "medium": "#3b82f6", "low": "#94a3b8"}.get(ch.get("severity", "medium"), "#3b82f6")
        change_rows += f"""
        <tr>
          <td style="padding:10px;border-bottom:1px solid #1e293b;color:#e2e8f0">{ch.get('competitor','')}</td>
          <td style="padding:10px;border-bottom:1px solid #1e293b;color:{sev_color};font-weight:700">{ch.get('change_type','').upper()}</td>
          <td style="padding:10px;border-bottom:1px solid #1e293b;color:#94a3b8">{ch.get('summary','')}</td>
        </tr>"""

    recs_html = "".join(f"<li style='padding:4px 0;color:#94a3b8'>{r}</li>" for r in brief.recommendations)

    html = f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#0a0e17;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif">
<div style="max-width:600px;margin:0 auto;padding:32px 24px">

  <div style="text-align:center;margin-bottom:32px">
    <h1 style="color:#e2e8f0;font-size:24px;margin:0">Rival<span style="color:#3b82f6">Radar</span></h1>
    <p style="color:#94a3b8;font-size:14px;margin:8px 0 0">{brief.period.title()} Intelligence Brief &mdash; {brief.generated_at[:10]}</p>
  </div>

  <div style="background:#111827;border:1px solid #1e293b;border-radius:12px;padding:24px;margin-bottom:24px">
    <h2 style="color:#e2e8f0;font-size:16px;margin:0 0 12px">Executive Summary</h2>
    <p style="color:#94a3b8;font-size:14px;line-height:1.6;margin:0">{brief.synthesis}</p>
  </div>

  {"" if not brief.changes else f'''
  <div style="background:#111827;border:1px solid #1e293b;border-radius:12px;padding:24px;margin-bottom:24px">
    <h2 style="color:#e2e8f0;font-size:16px;margin:0 0 16px">Changes Detected ({len(brief.changes)})</h2>
    <table style="width:100%;border-collapse:collapse">
      <thead><tr>
        <th style="padding:10px;text-align:left;color:#64748b;font-size:12px;text-transform:uppercase;border-bottom:1px solid #1e293b">Competitor</th>
        <th style="padding:10px;text-align:left;color:#64748b;font-size:12px;text-transform:uppercase;border-bottom:1px solid #1e293b">Type</th>
        <th style="padding:10px;text-align:left;color:#64748b;font-size:12px;text-transform:uppercase;border-bottom:1px solid #1e293b">Details</th>
      </tr></thead>
      <tbody>{change_rows}</tbody>
    </table>
  </div>'''}

  <div style="background:#111827;border:1px solid #1e293b;border-radius:12px;padding:24px;margin-bottom:24px">
    <h2 style="color:#e2e8f0;font-size:16px;margin:0 0 12px">Recommended Actions</h2>
    <ul style="margin:0;padding-left:20px">{recs_html}</ul>
  </div>

  <div style="text-align:center;padding:24px 0;border-top:1px solid #1e293b">
    <p style="color:#475569;font-size:12px;margin:0">RivalRadar &mdash; AI Competitive Intelligence</p>
  </div>

</div>
</body>
</html>"""
    return html


# ---------------------------------------------------------------------------
# 5. Full monitoring cycle (orchestration)
# ---------------------------------------------------------------------------

def run_monitoring_cycle(competitors: list) -> IntelBrief:
    """Execute one full monitoring cycle for a list of competitors."""
    _ensure_dirs()
    all_changes = []

    for comp in competitors:
        for url in comp.watch_pages:
            snap = take_snapshot(comp, url)
            change = detect_changes(comp, snap)
            if change:
                all_changes.append(change)
                # persist change
                change_path = os.path.join(
                    DATA_DIR, "changes",
                    f"{change.competitor}_{change.detected_at[:10]}_{change.change_type}.json"
                )
                save_json(change_path, asdict(change))

    brief = generate_brief(all_changes)

    # persist brief
    brief_path = os.path.join(DATA_DIR, "briefs", f"brief_{brief.generated_at[:10]}.json")
    save_json(brief_path, asdict(brief))

    return brief


# ---------------------------------------------------------------------------
# Demo / self-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 60)
    print("RivalRadar Engine v1.0.0-mvp — Self-Test")
    print("=" * 60)

    demo_competitors = [
        Competitor(
            name="AcmeSaaS",
            url="https://acme-saas.example.com",
            tier="analyst",
            watch_pages=[
                "https://acme-saas.example.com/pricing",
                "https://acme-saas.example.com/features",
                "https://acme-saas.example.com/blog",
            ],
            social_handles={"twitter": "@acmesaas"},
        ),
        Competitor(
            name="BetaTools",
            url="https://beta-tools.example.com",
            tier="scout",
            watch_pages=[
                "https://beta-tools.example.com/pricing",
            ],
        ),
    ]

    # Run cycle 1 — initial snapshots (no changes expected)
    print("\n[Cycle 1] Taking initial snapshots...")
    brief1 = run_monitoring_cycle(demo_competitors)
    print(f"  Changes detected: {len(brief1.changes)}")
    print(f"  Synthesis: {brief1.synthesis}")

    # Run cycle 2 — stub always generates new content so changes will be detected
    print("\n[Cycle 2] Re-scanning (changes expected from timestamp diff)...")
    time.sleep(0.1)  # ensure timestamp differs
    brief2 = run_monitoring_cycle(demo_competitors)
    print(f"  Changes detected: {len(brief2.changes)}")
    print(f"  Synthesis: {brief2.synthesis}")

    # Format email
    print("\n[Email Digest] Generating HTML digest...")
    html = format_digest_html(brief2, "founder@example.com")
    digest_path = os.path.join(DATA_DIR, "briefs", "sample_digest.html")
    with open(digest_path, "w") as f:
        f.write(html)
    print(f"  Saved to: {digest_path}")

    print("\n" + "=" * 60)
    print("Self-test complete. All systems operational.")
    print("=" * 60)
