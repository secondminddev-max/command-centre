"""
Spawn / upgrade script for the 'emailer' agent.
Agent ID : emailer
Name     : EmailAgent
Role     : Email dispatch agent — sends reports, alerts and digests via SendGrid SMTP
Emoji    : 📧
Color    : #22D3EE
"""

EMAILER_CODE = r"""
def run_emailer():
    import time, json, os, smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart

    aid = "emailer"
    CWD = "/Users/secondmind/claudecodetest"
    CONFIG_FILE = os.path.join(CWD, "data", "email_config.json")
    QUEUE_FILE  = os.path.join(CWD, "data", "email_queue.json")
    FAILED_FILE = os.path.join(CWD, "data", "email_failed.json")
    SENT_LOG    = os.path.join(CWD, "data", "email_sent_log.json")
    STATS_FILE  = os.path.join(CWD, "data", "email_stats.json")

    set_agent(aid, name="EmailAgent",
              role="Email dispatch agent \u2014 sends reports, alerts and digests via SendGrid SMTP",
              emoji="\U0001f4e7", color="#22D3EE", status="idle", progress=0,
              task="Standby \u2014 awaiting email send requests")
    add_log(aid, "EmailAgent (emailer) online \u2014 primary transport: SendGrid SMTP (smtp.sendgrid.net:587)", "ok")

    sent_count     = 0
    failed_count   = 0
    last_recipient = ""
    last_subject   = ""
    last_backend   = "sendgrid-smtp"

    # Startup credential check
    _sg_key_startup = os.environ.get("SENDGRID_API_KEY", "").strip()
    if not _sg_key_startup:
        add_log(aid,
                "WARN: SENDGRID_API_KEY not set. EmailAgent (emailer) will remain idle until the "
                "env var is configured. Set SENDGRID_API_KEY and SENDGRID_FROM_EMAIL to enable sending.",
                "warn")
    else:
        add_log(aid, "SendGrid SMTP credentials detected \u2014 ready to send", "ok")

    def _write_stats():
        stats = {
            "agent": aid,
            "backend": last_backend,
            "sent_count": sent_count,
            "failed_count": failed_count,
            "last_recipient": last_recipient,
            "updated": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }
        os.makedirs(os.path.dirname(STATS_FILE), exist_ok=True)
        with open(STATS_FILE, "w") as _f:
            json.dump(stats, _f, indent=2)

    def _append_sent_log(entry):
        try:
            log = []
            if os.path.exists(SENT_LOG):
                with open(SENT_LOG) as _f:
                    log = json.load(_f)
        except Exception:
            log = []
        log.append(entry)
        log = log[-100:]
        os.makedirs(os.path.dirname(SENT_LOG), exist_ok=True)
        with open(SENT_LOG, "w") as _f:
            json.dump(log, _f, indent=2)

    def _send_smtp_sendgrid(to_addr, subject, body, is_html, from_addr, sg_key, cc_list, bcc_list):
        # Send via SendGrid SMTP relay. login='apikey', password=SENDGRID_API_KEY. Raises on failure.
        mime_msg = MIMEMultipart("alternative")
        mime_msg["Subject"] = subject
        mime_msg["From"]    = from_addr
        mime_msg["To"]      = to_addr
        if cc_list:
            mime_msg["Cc"] = ", ".join(cc_list)
        all_rcpts = [to_addr] + cc_list + bcc_list
        mime_msg.attach(MIMEText(body, "html" if is_html else "plain"))
        with smtplib.SMTP("smtp.sendgrid.net", 587, timeout=15) as srv:
            srv.ehlo()
            srv.starttls()
            srv.ehlo()
            srv.login("apikey", sg_key)
            srv.sendmail(from_addr, all_rcpts, mime_msg.as_string())

    _write_stats()

    while not agent_should_stop(aid):
        try:
            queue = []
            if os.path.exists(QUEUE_FILE):
                with open(QUEUE_FILE) as f:
                    queue = json.load(f)

            if queue:
                msg = queue.pop(0)
                with open(QUEUE_FILE, "w") as f:
                    json.dump(queue, f)

                cfg = {}
                if os.path.exists(CONFIG_FILE):
                    with open(CONFIG_FILE) as f:
                        cfg = json.load(f)

                to_addr  = (msg.get("to", "").strip()
                            or cfg.get("default_to", "").strip()
                            or os.environ.get("EMAIL_TO", "").strip())
                subject  = msg.get("subject", "No Subject")
                body     = msg.get("body", "")
                is_html  = bool(msg.get("html", False))
                cc_list  = msg.get("cc", [])
                bcc_list = msg.get("bcc", [])
                if isinstance(cc_list,  str): cc_list  = [cc_list]  if cc_list  else []
                if isinstance(bcc_list, str): bcc_list = [bcc_list] if bcc_list else []

                # Credentials from env (preferred) then config file
                sg_key    = (os.environ.get("SENDGRID_API_KEY", "").strip()
                             or cfg.get("sendgrid_api_key", "").strip())
                from_addr = (os.environ.get("SENDGRID_FROM_EMAIL", "").strip()
                             or cfg.get("from_address", cfg.get("from_addr", "")).strip()
                             or os.environ.get("EMAIL_FROM", "").strip()
                             or "noreply@system.local")

                queue_depth = len(queue)
                set_agent(aid, status="busy", progress=50,
                          task=f"Sending to {to_addr}: {subject[:40]} | queue:{queue_depth}")

                try:
                    if not to_addr:
                        raise ValueError("no recipient \u2014 set EMAIL_TO env var or data/email_config.json default_to")

                    if not sg_key:
                        add_log(aid,
                                "Cannot send \u2014 SENDGRID_API_KEY not set. "
                                f"Message parked: {subject[:50]}", "warn")
                        failed = []
                        if os.path.exists(FAILED_FILE):
                            with open(FAILED_FILE) as f:
                                failed = json.load(f)
                        msg["error"] = "SENDGRID_API_KEY not set"
                        failed.append(msg)
                        os.makedirs(os.path.dirname(FAILED_FILE), exist_ok=True)
                        with open(FAILED_FILE, "w") as f:
                            json.dump(failed, f, indent=2)
                        failed_count += 1
                        _write_stats()
                    else:
                        _send_smtp_sendgrid(to_addr, subject, body, is_html,
                                            from_addr, sg_key, cc_list, bcc_list)
                        last_backend   = "sendgrid-smtp"
                        sent_count    += 1
                        last_recipient = to_addr
                        last_subject   = subject
                        add_log(aid, f"Sent via SendGrid SMTP to {to_addr}: {subject}", "ok")
                        _append_sent_log({"ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
                                          "to": to_addr, "subject": subject,
                                          "via": "sendgrid-smtp"})
                        _write_stats()

                except Exception as e:
                    add_log(aid, f"Send error: {e}", "error")
                    set_agent(aid, status="error", task=f"Send failed: {str(e)[:60]}")
                    failed_count += 1
                    _write_stats()
                    try:
                        failed = []
                        if os.path.exists(FAILED_FILE):
                            with open(FAILED_FILE) as _f:
                                failed = json.load(_f)
                        msg["error"] = str(e)
                        failed.append(msg)
                        with open(FAILED_FILE, "w") as _f:
                            json.dump(failed, _f, indent=2)
                    except Exception:
                        pass
                    time.sleep(3)

                queue_depth = len(queue)
                last_info = f"last\u2192{last_recipient}: {last_subject[:30]}" if last_recipient else "no sends yet"
                set_agent(aid, status="idle", progress=0,
                          task=f"Standby | sent:{sent_count} failed:{failed_count} queue:{queue_depth} | {last_info}")

            else:
                queue_depth = 0
                last_info = f"last\u2192{last_recipient}: {last_subject[:30]}" if last_recipient else "awaiting requests"
                set_agent(aid, status="idle", progress=0,
                          task=f"Standby \u2014 sent:{sent_count} | failed:{failed_count} | queue:{queue_depth} | {last_info}")

        except Exception as e:
            add_log(aid, f"Queue error: {e}", "error")

        agent_sleep(aid, 60)

    set_agent(aid, status="idle", task="Stopped")
"""

if __name__ == "__main__":
    import json, sys, urllib.request

    BASE = "http://localhost:5050"

    payload = json.dumps({
        "agent_id": "emailer",
        "name":     "EmailAgent",
        "role":     "Email dispatch agent \u2014 sends reports, alerts and digests via SendGrid SMTP",
        "emoji":    "\U0001f4e7",
        "color":    "#22D3EE",
        "code":     EMAILER_CODE,
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{BASE}/api/agent/upgrade",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        result = json.loads(resp.read().decode())
    except Exception as e:
        print(f"HTTP error: {e}")
        sys.exit(1)

    if result.get("ok"):
        print("✓ emailer (EmailAgent) upgraded to SendGrid SMTP successfully")
    else:
        print(f"✗ Upgrade failed: {result}")
        sys.exit(1)
