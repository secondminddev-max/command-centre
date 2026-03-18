#!/usr/bin/env python3
"""
One-time Gmail OAuth2 setup using InstalledAppFlow.
Opens browser, captures the callback on localhost:5051, saves refresh token.
Run: python3 gmail_auth.py
"""
import os, json, sys, warnings
warnings.filterwarnings("ignore")

CWD = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(CWD, ".env")

# Load .env
env = {}
if os.path.exists(ENV_PATH):
    for line in open(ENV_PATH):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()

CLIENT_ID     = env.get("GMAIL_CLIENT_ID", "").strip()
CLIENT_SECRET = env.get("GMAIL_CLIENT_SECRET", "").strip()
GMAIL_USER    = env.get("GMAIL_USER", "").strip()

if not CLIENT_ID or not CLIENT_SECRET:
    print("ERROR: GMAIL_CLIENT_ID or GMAIL_CLIENT_SECRET not set in .env")
    sys.exit(1)

print(f"Client ID: {CLIENT_ID[:30]}...")
print(f"Gmail user: {GMAIL_USER}")
print()

client_config = {
    "installed": {
        "client_id":     CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "auth_uri":      "https://accounts.google.com/o/oauth2/auth",
        "token_uri":     "https://oauth2.googleapis.com/token",
        "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob", "http://localhost"],
    }
}

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://mail.google.com/"]

flow = InstalledAppFlow.from_client_config(client_config, scopes=SCOPES)

print("Opening browser for Google authorization...")
print("(If browser doesn't open, copy the URL printed below)\n")

creds = flow.run_local_server(port=5051, open_browser=True,
                               success_message="Authorization complete — you can close this tab.")

refresh_token = creds.refresh_token
if not refresh_token:
    print("ERROR: No refresh token received. Try revoking app access at myaccount.google.com/permissions and re-running.")
    sys.exit(1)

print(f"\n✓ Refresh token received: {refresh_token[:20]}...")

# Save to .env
lines = open(ENV_PATH).readlines() if os.path.exists(ENV_PATH) else []
new_lines = []
updated = {"GMAIL_REFRESH_TOKEN": False, "GMAIL_USER": False}
for line in lines:
    k = line.split("=")[0].strip()
    if k == "GMAIL_REFRESH_TOKEN":
        new_lines.append(f"GMAIL_REFRESH_TOKEN={refresh_token}\n")
        updated["GMAIL_REFRESH_TOKEN"] = True
    elif k == "GMAIL_USER":
        new_lines.append(f"GMAIL_USER={GMAIL_USER}\n")
        updated["GMAIL_USER"] = True
    else:
        new_lines.append(line)

if not updated["GMAIL_REFRESH_TOKEN"]:
    new_lines.append(f"GMAIL_REFRESH_TOKEN={refresh_token}\n")
if not updated["GMAIL_USER"]:
    new_lines.append(f"GMAIL_USER={GMAIL_USER}\n")

with open(ENV_PATH, "w") as f:
    f.writelines(new_lines)

# Save to data/gmail_tokens.json
tokens_path = os.path.join(CWD, "data", "gmail_tokens.json")
with open(tokens_path, "w") as f:
    json.dump({
        "refresh_token": refresh_token,
        "client_id":     CLIENT_ID,
        "gmail_user":    GMAIL_USER,
        "saved_at":      __import__("time").strftime("%Y-%m-%dT%H:%M:%S"),
    }, f, indent=2)

print(f"✓ Saved to .env and {tokens_path}")
print()
print("Email is now configured. Restart the server to pick up the new token:")
print("  python3 agent_server.py")
