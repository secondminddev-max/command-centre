#!/usr/bin/env python3
"""Generate a morning briefing HTML report."""

import json
import os
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).parent.parent
DATA = BASE / "data"
REPORTS = BASE / "reports"


def load_json(path):
    try:
        with open(path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


WEATHER_CODES = {
    0: ("Clear sky", "☀️"),
    1: ("Mainly clear", "🌤️"),
    2: ("Partly cloudy", "⛅"),
    3: ("Overcast", "☁️"),
    45: ("Foggy", "🌫️"),
    48: ("Icy fog", "🌫️"),
    51: ("Light drizzle", "🌦️"),
    53: ("Drizzle", "🌦️"),
    55: ("Dense drizzle", "🌧️"),
    61: ("Slight rain", "🌧️"),
    63: ("Rain", "🌧️"),
    65: ("Heavy rain", "🌧️"),
    71: ("Slight snow", "🌨️"),
    73: ("Snow", "❄️"),
    75: ("Heavy snow", "❄️"),
    80: ("Rain showers", "🌦️"),
    81: ("Rain showers", "🌧️"),
    82: ("Violent showers", "⛈️"),
    95: ("Thunderstorm", "⛈️"),
    99: ("Thunderstorm with hail", "⛈️"),
}


def weather_section(data):
    if not data:
        return "<p>Weather data unavailable.</p>"

    code = data.get("weathercode", 0)
    desc, icon = WEATHER_CODES.get(code, ("Unknown", "🌡️"))
    temp = data.get("temperature_c", "?")
    wind = data.get("windspeed_kmh", "?")
    location = data.get("location", "Unknown")

    forecast = data.get("forecast_24h", [])
    today = [h for h in forecast if "T" in h.get("hour", "") and h["hour"].startswith("2026-03-15")]
    max_t = max((h["temp_c"] for h in today), default=temp)
    min_t = min((h["temp_c"] for h in today), default=temp)
    total_precip = sum(h.get("precip_mm", 0) for h in today)

    rain_warning = ""
    if total_precip > 1:
        rain_warning = f'<span class="badge badge-warn">🌂 Rain expected ({total_precip:.1f}mm)</span>'
    elif total_precip > 0:
        rain_warning = f'<span class="badge badge-info">💧 Light rain possible</span>'

    hourly_html = ""
    for h in today[::3]:
        hour_label = h["hour"].split("T")[1][:5]
        hourly_html += f'<div class="hour-item"><span class="hour-time">{hour_label}</span><span class="hour-temp">{h["temp_c"]}°C</span></div>'

    return f"""
    <div class="weather-hero">
      <div class="weather-main">
        <span class="weather-icon">{icon}</span>
        <div class="weather-info">
          <div class="weather-desc">{desc}</div>
          <div class="weather-temp">{temp}°C <span class="weather-location">in {location}</span></div>
          <div class="weather-meta">💨 Wind {wind} km/h &nbsp;|&nbsp; ↑ {max_t}°C &nbsp; ↓ {min_t}°C</div>
          {rain_warning}
        </div>
      </div>
      {f'<div class="hourly-forecast">{hourly_html}</div>' if hourly_html else ''}
    </div>"""


def improvements_section(data):
    completed = data.get("completed", [])
    if not completed:
        return "<p>No completed tasks overnight.</p>"

    started = data.get("started_at", "Unknown")
    items = ""
    for item in completed:
        status = "✅" if item.get("success") else "❌"
        agent = item.get("agent", "agent")
        time_done = item.get("completed", "")
        title = item.get("title", "Untitled")
        desc = item.get("description", "")[:120]
        if len(item.get("description", "")) > 120:
            desc += "…"
        items += f"""
        <div class="task-item">
          <span class="task-status">{status}</span>
          <div class="task-body">
            <div class="task-title">{title}</div>
            <div class="task-meta">Agent: <em>{agent}</em>{f' &nbsp;·&nbsp; Done: {time_done}' if time_done else ''}</div>
            <div class="task-desc">{desc}</div>
          </div>
        </div>"""

    return f'<p class="session-meta">Session started: {started} &nbsp;·&nbsp; {len(completed)} tasks completed</p>{items}'


def hn_section(data):
    stories = data.get("stories", [])
    if not stories:
        return "<p>No HN data available.</p>"

    top = sorted(stories, key=lambda s: s.get("score", 0), reverse=True)[:10]
    items = ""
    for i, s in enumerate(top, 1):
        score = s.get("score", 0)
        comments = s.get("comments", 0)
        url = s.get("url", "#")
        title = s.get("title", "Untitled")
        by = s.get("by", "")
        items += f"""
        <div class="hn-item">
          <span class="hn-rank">#{i}</span>
          <div class="hn-body">
            <a href="{url}" class="hn-title" target="_blank">{title}</a>
            <div class="hn-meta">▲ {score} pts &nbsp;·&nbsp; 💬 {comments} &nbsp;·&nbsp; by {by}</div>
          </div>
        </div>"""
    return items


def github_section(data):
    repos = data.get("repos", [])
    if not repos:
        return "<p>No GitHub trending data available.</p>"

    items = ""
    for repo in repos[:8]:
        name = repo.get("name", "")
        desc = repo.get("description", "") or "No description"
        stars = repo.get("stars", 0)
        lang = repo.get("language", "")
        url = repo.get("url", "#")
        lang_badge = f'<span class="lang-badge">{lang}</span>' if lang else ""
        items += f"""
        <div class="repo-item">
          <div class="repo-header">
            <a href="{url}" class="repo-name" target="_blank">{name}</a>
            {lang_badge}
          </div>
          <div class="repo-desc">{desc[:140]}{"…" if len(desc) > 140 else ""}</div>
          <div class="repo-meta">⭐ {stars:,} stars</div>
        </div>"""
    return items


def wiki_section(data):
    facts = data.get("facts", [])
    if not facts:
        return "<p>No facts available.</p>"

    items = ""
    for fact in facts[:5]:
        title = fact.get("title", "")
        summary = fact.get("summary", "")[:300]
        if len(fact.get("summary", "")) > 300:
            summary += "…"
        url = fact.get("url", "#")
        items += f"""
        <div class="fact-item">
          <a href="{url}" class="fact-title" target="_blank">{title}</a>
          <div class="fact-summary">{summary}</div>
        </div>"""
    return items


def generate_html(weather, hn, github, wiki, improvements):
    now = datetime.now()
    greeting_hour = now.hour
    if greeting_hour < 12:
        greeting = "Good Morning"
    elif greeting_hour < 17:
        greeting = "Good Afternoon"
    else:
        greeting = "Good Evening"

    date_str = now.strftime("%A, %B %-d, %Y")
    time_str = now.strftime("%H:%M")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Morning Briefing — {date_str}</title>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

    body {{
      background: #0f1117;
      color: #e2e8f0;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      font-size: 15px;
      line-height: 1.6;
      min-height: 100vh;
    }}

    a {{ color: #7dd3fc; text-decoration: none; }}
    a:hover {{ color: #bae6fd; text-decoration: underline; }}

    .container {{
      max-width: 860px;
      margin: 0 auto;
      padding: 2rem 1.5rem 4rem;
    }}

    /* Header */
    .hero {{
      text-align: center;
      padding: 3rem 1rem 2.5rem;
      background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
      border-radius: 16px;
      margin-bottom: 2rem;
      border: 1px solid #1e3a5f;
    }}
    .hero-greeting {{
      font-size: 2.8rem;
      font-weight: 700;
      background: linear-gradient(90deg, #38bdf8, #818cf8);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
      margin-bottom: 0.25rem;
    }}
    .hero-date {{
      font-size: 1.1rem;
      color: #94a3b8;
      margin-bottom: 0.5rem;
    }}
    .hero-time {{
      font-size: 3.5rem;
      font-weight: 300;
      color: #f1f5f9;
      letter-spacing: 0.05em;
    }}

    /* Section */
    .section {{
      background: #1a1f2e;
      border: 1px solid #2d3748;
      border-radius: 12px;
      padding: 1.5rem;
      margin-bottom: 1.5rem;
    }}
    .section-header {{
      display: flex;
      align-items: center;
      gap: 0.6rem;
      font-size: 1.1rem;
      font-weight: 600;
      color: #f1f5f9;
      margin-bottom: 1.25rem;
      padding-bottom: 0.75rem;
      border-bottom: 1px solid #2d3748;
    }}
    .section-icon {{ font-size: 1.3rem; }}

    /* Weather */
    .weather-hero {{
      display: flex;
      flex-direction: column;
      gap: 1rem;
    }}
    .weather-main {{
      display: flex;
      align-items: center;
      gap: 1.5rem;
    }}
    .weather-icon {{ font-size: 4rem; }}
    .weather-desc {{ font-size: 1rem; color: #94a3b8; margin-bottom: 0.2rem; }}
    .weather-temp {{ font-size: 2.2rem; font-weight: 600; color: #f1f5f9; }}
    .weather-location {{ font-size: 1rem; font-weight: 400; color: #64748b; }}
    .weather-meta {{ font-size: 0.875rem; color: #64748b; margin-top: 0.3rem; }}
    .badge {{ display: inline-block; padding: 0.2rem 0.7rem; border-radius: 999px; font-size: 0.8rem; margin-top: 0.5rem; }}
    .badge-warn {{ background: #422006; color: #fb923c; border: 1px solid #7c2d12; }}
    .badge-info {{ background: #172554; color: #93c5fd; border: 1px solid #1e3a8a; }}
    .hourly-forecast {{
      display: flex;
      gap: 0.5rem;
      overflow-x: auto;
      padding-bottom: 0.25rem;
    }}
    .hour-item {{
      display: flex;
      flex-direction: column;
      align-items: center;
      background: #0f1117;
      border: 1px solid #2d3748;
      border-radius: 8px;
      padding: 0.5rem 0.75rem;
      min-width: 64px;
    }}
    .hour-time {{ font-size: 0.75rem; color: #64748b; }}
    .hour-temp {{ font-size: 0.95rem; font-weight: 600; color: #e2e8f0; }}

    /* Tasks */
    .session-meta {{ font-size: 0.85rem; color: #64748b; margin-bottom: 1rem; }}
    .task-item {{
      display: flex;
      gap: 0.75rem;
      padding: 0.75rem 0;
      border-bottom: 1px solid #1e293b;
    }}
    .task-item:last-child {{ border-bottom: none; }}
    .task-status {{ font-size: 1.2rem; flex-shrink: 0; padding-top: 0.1rem; }}
    .task-title {{ font-weight: 600; color: #e2e8f0; margin-bottom: 0.15rem; }}
    .task-meta {{ font-size: 0.8rem; color: #64748b; margin-bottom: 0.2rem; }}
    .task-desc {{ font-size: 0.85rem; color: #94a3b8; }}

    /* HN */
    .hn-item {{
      display: flex;
      gap: 0.75rem;
      align-items: flex-start;
      padding: 0.7rem 0;
      border-bottom: 1px solid #1e293b;
    }}
    .hn-item:last-child {{ border-bottom: none; }}
    .hn-rank {{ font-size: 0.85rem; color: #64748b; min-width: 28px; font-weight: 700; padding-top: 0.1rem; }}
    .hn-title {{ font-weight: 500; color: #e2e8f0; display: block; margin-bottom: 0.2rem; }}
    .hn-meta {{ font-size: 0.8rem; color: #64748b; }}

    /* GitHub */
    .repo-item {{
      padding: 0.85rem 0;
      border-bottom: 1px solid #1e293b;
    }}
    .repo-item:last-child {{ border-bottom: none; }}
    .repo-header {{ display: flex; align-items: center; gap: 0.6rem; margin-bottom: 0.3rem; }}
    .repo-name {{ font-weight: 600; color: #7dd3fc; }}
    .lang-badge {{
      font-size: 0.7rem;
      background: #1e3a5f;
      color: #7dd3fc;
      border-radius: 999px;
      padding: 0.1rem 0.5rem;
    }}
    .repo-desc {{ font-size: 0.875rem; color: #94a3b8; margin-bottom: 0.3rem; }}
    .repo-meta {{ font-size: 0.8rem; color: #64748b; }}

    /* Wiki */
    .fact-item {{
      padding: 0.85rem 0;
      border-bottom: 1px solid #1e293b;
    }}
    .fact-item:last-child {{ border-bottom: none; }}
    .fact-title {{ font-weight: 600; color: #a78bfa; display: block; margin-bottom: 0.35rem; }}
    .fact-summary {{ font-size: 0.875rem; color: #94a3b8; }}

    .footer {{
      text-align: center;
      color: #475569;
      font-size: 0.8rem;
      margin-top: 2rem;
    }}

    @media (max-width: 600px) {{
      .hero-greeting {{ font-size: 2rem; }}
      .hero-time {{ font-size: 2.5rem; }}
      .weather-main {{ flex-direction: column; align-items: flex-start; }}
    }}
  </style>
</head>
<body>
  <div class="container">

    <!-- Header -->
    <div class="hero">
      <div class="hero-greeting">{greeting}</div>
      <div class="hero-date">{date_str}</div>
      <div class="hero-time">{time_str}</div>
    </div>

    <!-- Weather -->
    <div class="section">
      <div class="section-header">
        <span class="section-icon">🌤️</span> Weather Summary
      </div>
      {weather_section(weather)}
    </div>

    <!-- Overnight improvements -->
    <div class="section">
      <div class="section-header">
        <span class="section-icon">🌙</span> What Happened Overnight
      </div>
      {improvements_section(improvements)}
    </div>

    <!-- HN -->
    <div class="section">
      <div class="section-header">
        <span class="section-icon">🔶</span> Today's Top Hacker News Stories
      </div>
      {hn_section(hn)}
    </div>

    <!-- GitHub -->
    <div class="section">
      <div class="section-header">
        <span class="section-icon">🐙</span> Trending on GitHub
      </div>
      {github_section(github)}
    </div>

    <!-- Wiki facts -->
    <div class="section">
      <div class="section-header">
        <span class="section-icon">📚</span> Random Facts to Start Your Day
      </div>
      {wiki_section(wiki)}
    </div>

    <div class="footer">Generated at {now.strftime("%Y-%m-%d %H:%M:%S")} &nbsp;·&nbsp; Morning Briefing</div>
  </div>
</body>
</html>"""


def main():
    REPORTS.mkdir(exist_ok=True)

    weather = load_json(DATA / "weather.json")
    hn = load_json(DATA / "hn_top.json")
    github = load_json(DATA / "github_trending.json")
    wiki = load_json(DATA / "wiki_facts.json")
    improvements = load_json(BASE / "improvements.json")

    html = generate_html(weather, hn, github, wiki, improvements)

    out = REPORTS / "morning_briefing.html"
    out.write_text(html, encoding="utf-8")
    print(f"✅ Morning briefing written to: {out}")
    print(f"   Size: {out.stat().st_size:,} bytes")


if __name__ == "__main__":
    main()
