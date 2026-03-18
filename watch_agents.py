#!/usr/bin/env python3
"""
watch_agents.py — Live terminal viewer for the Agent Command Centre.

Usage:
  python3 watch_agents.py            # stream everything
  python3 watch_agents.py coder      # only show output from 'coder' agent

Connects via SSE to http://localhost:5050/api/stream and renders:
  - Agent status changes
  - Log entries
  - Live delegate output (tool calls, file writes, bash commands, Claude text)
"""

import sys, json, time, urllib.request, urllib.error, shutil, os
from datetime import datetime

# ─── Config ────────────────────────────────────────────────────────────────────
SERVER   = "http://localhost:5050"
FILTER   = sys.argv[1] if len(sys.argv) > 1 else None   # optional agent_id filter

# ─── ANSI colours ──────────────────────────────────────────────────────────────
RESET  = "\033[0m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
ITALIC = "\033[3m"

def fg(r,g,b): return f"\033[38;2;{r};{g};{b}m"
def bg(r,g,b): return f"\033[48;2;{r};{g};{b}m"

C_TIME     = fg(120,120,140)
C_AGENT    = fg(160,220,255)
C_TEXT     = fg(220,220,220)
C_DIM      = fg(100,100,110)
C_GREEN    = fg( 80,220,120)
C_YELLOW   = fg(255,210, 60)
C_RED      = fg(255, 80, 80)
C_BLUE     = fg( 80,160,255)
C_PURPLE   = fg(200,100,255)
C_CYAN     = fg( 60,210,210)
C_ORANGE   = fg(255,150, 50)
C_PINK     = fg(255,120,180)

# Event type → (prefix_emoji, colour)
TYPE_STYLE = {
    "text":       ("💬", C_TEXT),
    "file_write": ("📝", C_GREEN),
    "bash":       ("🔧", C_YELLOW),
    "tool_use":   ("⚙️ ", C_BLUE),
    "tool_result":("✓ ", C_DIM),
    "init":       ("▶ ", C_CYAN),
    "done":       ("✅", C_GREEN),
    "error":      ("❌", C_RED),
}

LOG_LEVEL_COLOR = {
    "info":  C_DIM,
    "ok":    C_GREEN,
    "warn":  C_YELLOW,
    "error": C_RED,
}

# ─── Per-agent colour palette ──────────────────────────────────────────────────
AGENT_COLORS = [
    fg(100,200,255), fg(255,150, 80), fg(120,255,160), fg(255,100,200),
    fg(200,150,255), fg( 60,220,200), fg(255,220, 60), fg(255, 80,100),
]
_agent_color_map = {}
_color_idx = 0

def agent_color(aid):
    global _color_idx
    if aid not in _agent_color_map:
        _agent_color_map[aid] = AGENT_COLORS[_color_idx % len(AGENT_COLORS)]
        _color_idx += 1
    return _agent_color_map[aid]

# ─── Terminal helpers ───────────────────────────────────────────────────────────
COLS = shutil.get_terminal_size().columns

def divider(char="─", color=C_DIM):
    print(f"{color}{char * COLS}{RESET}")

def header():
    os.system("clear")
    title  = "  Agent Command Centre — Live View  "
    filt   = f"  filter: {FILTER}  " if FILTER else ""
    pad    = max(0, COLS - len(title) - len(filt) - 2)
    print(f"\n{BOLD}{C_AGENT}{title}{RESET}{DIM}{filt}{' ' * pad}{RESET}")
    print(f"{C_DIM}  {SERVER}/api/stream   •   Ctrl-C to quit{RESET}")
    divider("═")
    print()

def now_str():
    return datetime.now().strftime("%H:%M:%S")

def wrap(text, indent=22, max_lines=8):
    """Word-wrap text to fit terminal width."""
    width = COLS - indent - 2
    if width < 20: width = 40
    lines, cur = [], ""
    for word in str(text).split():
        if len(cur) + len(word) + 1 > width:
            lines.append(cur)
            cur = word
        else:
            cur = (cur + " " + word).strip()
    if cur: lines.append(cur)
    if len(lines) > max_lines:
        lines = lines[:max_lines] + ["…"]
    return lines

def print_event(event_type, data):
    aid        = data.get("agent_id", data.get("agent", "system"))
    agent_name = data.get("agent_name", data.get("agent", aid))

    # Apply filter
    if FILTER and aid != FILTER and agent_name != FILTER:
        return

    acolor = agent_color(aid)

    if event_type == "log":
        level   = data.get("level","info")
        msg     = data.get("message","")
        lcolor  = LOG_LEVEL_COLOR.get(level, C_DIM)
        ts_str  = data.get("ts", now_str())
        print(f"  {C_TIME}{ts_str}{RESET}  {acolor}{BOLD}{agent_name:<10}{RESET}  {lcolor}{msg}{RESET}")

    elif event_type == "agent_output":
        otype = data.get("type","text")
        text  = data.get("text","")
        emoji, tcolor = TYPE_STYLE.get(otype, ("  ", C_TEXT))

        ts_str = now_str()
        prefix = f"  {C_TIME}{ts_str}{RESET}  {acolor}{BOLD}{agent_name:<10}{RESET}  {emoji} "

        lines = wrap(text)
        indent_str = " " * (22 + 3)  # align continuation lines

        for i, line in enumerate(lines):
            if i == 0:
                print(f"{prefix}{tcolor}{line}{RESET}")
            else:
                print(f"{indent_str}{tcolor}{line}{RESET}")

        # Show file preview for writes
        if otype == "file_write" and data.get("preview"):
            preview    = data["preview"]
            fp         = data.get("file_path","")
            line_width = max(40, COLS - 28)
            file_lines = preview.split("\n")[:6]
            print(f"{indent_str}{C_DIM}┌─ {fp}{RESET}")
            for fl in file_lines:
                print(f"{indent_str}{C_DIM}│ {fl[:line_width]}{RESET}")
            if len(preview.split("\n")) > 6:
                print(f"{indent_str}{C_DIM}└─ …{RESET}")
            else:
                print(f"{indent_str}{C_DIM}└─{RESET}")

        # Separator after done/init
        if otype in ("done", "init"):
            print(f"  {C_DIM}{'·' * (COLS-4)}{RESET}")

    elif event_type == "agent_update":
        status = data.get("status","")
        task   = data.get("task","")
        scolor = C_GREEN if status == "active" else C_YELLOW if status == "busy" else C_DIM
        print(f"  {C_TIME}{now_str()}{RESET}  {acolor}{BOLD}{agent_name:<10}{RESET}  "
              f"{scolor}[{status}]{RESET} {C_DIM}{task[:80]}{RESET}")

# ─── SSE reader ────────────────────────────────────────────────────────────────
def connect_sse():
    url = f"{SERVER}/api/stream"
    req = urllib.request.Request(url, headers={"Accept": "text/event-stream", "Cache-Control": "no-cache"})
    return urllib.request.urlopen(req, timeout=None)

def read_sse(resp):
    """Yield (event_type, data_dict) from an SSE response."""
    event_type = "message"
    buf = b""
    while True:
        chunk = resp.read(1)
        if not chunk:
            break
        buf += chunk
        if buf.endswith(b"\n\n"):
            block = buf.decode("utf-8", errors="replace").strip()
            buf = b""
            if not block or block.startswith(":"):
                continue
            ev_type = "message"
            ev_data = ""
            for line in block.splitlines():
                if line.startswith("event:"):
                    ev_type = line[6:].strip()
                elif line.startswith("data:"):
                    ev_data = line[5:].strip()
            if ev_data:
                try:    yield ev_type, json.loads(ev_data)
                except: yield ev_type, {"raw": ev_data}

# ─── Main ──────────────────────────────────────────────────────────────────────
def main():
    header()

    # Show a snapshot of current status before streaming
    try:
        with urllib.request.urlopen(f"{SERVER}/api/status", timeout=5) as r:
            st = json.loads(r.read())
        print(f"  {BOLD}Agents:{RESET}")
        for a in st.get("agents",[]):
            sc = C_GREEN if a.get("status")=="active" else C_YELLOW if a.get("status")=="busy" else C_DIM
            ac = agent_color(a["id"])
            print(f"    {ac}{BOLD}{a.get('emoji','')} {a.get('name',''):<14}{RESET} "
                  f"{sc}{a.get('status',''):<8}{RESET} {C_DIM}{a.get('task','')[:60]}{RESET}")
        print()
        print(f"  {BOLD}Recent logs:{RESET}")
        for log in reversed(st.get("logs",[])[:10]):
            lc = LOG_LEVEL_COLOR.get(log.get("level","info"), C_DIM)
            ac = agent_color(log["agent"])
            print(f"    {C_TIME}{log['ts']}{RESET} {ac}{log['agent']:<10}{RESET} {lc}{log['message'][:80]}{RESET}")
        print()
        divider()
        print(f"\n  {C_CYAN}Streaming live events…  (Ctrl-C to quit){RESET}\n")
    except Exception as e:
        print(f"  {C_RED}Could not reach server: {e}{RESET}\n")

    while True:
        try:
            resp = connect_sse()
            for ev_type, data in read_sse(resp):
                print_event(ev_type, data)
        except KeyboardInterrupt:
            print(f"\n\n  {C_DIM}Disconnected.{RESET}\n")
            sys.exit(0)
        except urllib.error.URLError as e:
            print(f"\n  {C_RED}Connection lost: {e}  — retrying in 3s…{RESET}")
            time.sleep(3)
        except Exception as e:
            print(f"\n  {C_RED}Error: {e}  — retrying in 3s…{RESET}")
            time.sleep(3)

if __name__ == "__main__":
    main()
