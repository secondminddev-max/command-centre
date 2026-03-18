def run_emailagent():
    import time, json, os, smtplib, base64, urllib.request, urllib.error, urllib.parse
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart

    aid = "emailagent"
    CWD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    CONFIG_FILE = os.path.join(CWD, "data", "email_config.json")
    QUEUE_FILE  = os.path.join(CWD, "data", "email_queue.json")
    FAILED_FILE = os.path.join(CWD, "data", "email_failed.json")
    LOG_FILE    = os.path.join(CWD, "data", "email_log.json")
    STATUS_FILE = os.path.join(CWD, "data", "email_status.json")

    GMAIL_TOKEN_URL = "https://oauth2.googleapis.com/token"
    GMAIL_SMTP_HOST = "smtp.gmail.com"
    GMAIL_SMTP_PORT = 587

    def _oauth_configured():
        return all([
            os.environ.get("GMAIL_CLIENT_ID", "").strip(),
            os.environ.get("GMAIL_CLIENT_SECRET", "").strip(),
            os.environ.get("GMAIL_REFRESH_TOKEN", "").strip(),
            os.environ.get("GMAIL_USER", "").strip(),
        ])

    def _oauth_partial():
        """Client ID+secret present but refresh token or user missing — needs consent flow."""
        return (
            bool(os.environ.get("GMAIL_CLIENT_ID", "").strip()) and
            bool(os.environ.get("GMAIL_CLIENT_SECRET", "").strip()) and
            not _oauth_configured()
        )

    # Determine initial status
    if _oauth_configured():
        _init_status = "Gmail OAuth2 fully configured — ready to send"
        _init_level  = "ok"
        _role_desc   = "Email Gateway — sends via Gmail OAuth2 (XOAUTH2 SMTP)"
    elif _oauth_partial():
        _init_status = "Gmail OAuth2 partial — GMAIL_REFRESH_TOKEN or GMAIL_USER missing. Visit /api/email/auth to complete consent flow."
        _init_level  = "warn"
        _role_desc   = "Email Gateway — Gmail OAuth2 pending refresh token"
    else:
        _init_status = "No Gmail credentials configured. Set GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET, GMAIL_REFRESH_TOKEN, GMAIL_USER env vars."
        _init_level  = "warn"
        _role_desc   = "Email Gateway — awaiting Gmail OAuth2 configuration"

    set_agent(aid, name="EmailAgent",
              role=_role_desc,
              emoji="\U0001f4e7", color="#00cc88", status="idle", progress=0,
              task="Standby — awaiting email send requests")
    add_log(aid, _init_status, _init_level)

    sent_count        = 0
    failed_count      = 0
    last_recipient    = ""
    last_subject      = ""
    last_sent_ts      = ""
    _daily_send_count = 0
    _daily_send_date  = ""

    def _html_wrap(subj, body_text):
        """Wrap plain body in a minimal dark-theme HTML email template."""
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        return (
            "<!DOCTYPE html><html><head><meta charset='utf-8'><style>"
            "body{font-family:Arial,sans-serif;background:#0d0d0d;color:#e0e0e0;margin:0;padding:0}"
            ".hdr{background:#1a1a2e;padding:20px;text-align:center;border-bottom:2px solid #00cc88}"
            ".hdr h1{color:#00cc88;margin:0;font-size:22px}"
            ".bdy{padding:24px;max-width:700px;margin:0 auto;white-space:pre-wrap;line-height:1.6}"
            ".ftr{background:#111;padding:12px;text-align:center;font-size:11px;color:#666;border-top:1px solid #333}"
            "</style></head><body>"
            f"<div class='hdr'><h1>Agent Command Centre</h1><p style='color:#aaa;margin:6px 0 0'>{subj}</p></div>"
            f"<div class='bdy'>{body_text}</div>"
            f"<div class='ftr'>Generated {ts} | Agent Command Centre</div>"
            "</body></html>"
        )

    def _append_log(to_addr, subject, method, success):
        try:
            log = []
            if os.path.exists(LOG_FILE):
                with open(LOG_FILE) as _f:
                    log = json.load(_f)
        except Exception:
            log = []
        log.append({
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "to": to_addr,
            "subject": subject,
            "method": method,
            "success": success,
        })
        log = log[-500:]
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        with open(LOG_FILE, "w") as _f:
            json.dump(log, _f, indent=2)

    def _write_status(backend, sent, failed, last_rcpt):
        try:
            os.makedirs(os.path.dirname(STATUS_FILE), exist_ok=True)
            configured = _oauth_configured()
            pending    = _oauth_partial()
            with open(STATUS_FILE, "w") as _f:
                json.dump({
                    "backend": backend,
                    "sent_count": sent,
                    "failed_count": failed,
                    "last_recipient": last_rcpt,
                    "oauth_status": "configured" if configured else ("pending_refresh_token" if pending else "not_configured"),
                    "credentials_configured": configured,
                    "gmail_user": os.environ.get("GMAIL_USER", "") or None,
                    "updated": time.strftime("%Y-%m-%dT%H:%M:%S"),
                }, _f, indent=2)
        except Exception:
            pass

    def _get_access_token():
        """Exchange refresh token for a fresh access token via Google OAuth2 token endpoint."""
        client_id     = os.environ.get("GMAIL_CLIENT_ID", "").strip()
        client_secret = os.environ.get("GMAIL_CLIENT_SECRET", "").strip()
        refresh_token = os.environ.get("GMAIL_REFRESH_TOKEN", "").strip()
        if not (client_id and client_secret and refresh_token):
            raise RuntimeError("Gmail OAuth2 credentials incomplete — run /api/email/auth consent flow first")
        params = urllib.parse.urlencode({
            "client_id":     client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type":    "refresh_token",
        }).encode("utf-8")
        req = urllib.request.Request(GMAIL_TOKEN_URL, data=params,
                                     headers={"Content-Type": "application/x-www-form-urlencoded"},
                                     method="POST")
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
        if "access_token" not in data:
            raise RuntimeError(f"Token refresh failed: {data.get('error_description', data)}")
        return data["access_token"]

    def _build_xoauth2(user, access_token):
        """Build XOAUTH2 SASL string for Gmail SMTP authentication."""
        auth_str = f"user={user}\x01auth=Bearer {access_token}\x01\x01"
        return base64.b64encode(auth_str.encode("utf-8")).decode("utf-8")

    def _send_once(to_addr, subject, body, is_html, cc_list, bcc_list, cfg):
        """Send via Gmail OAuth2 XOAUTH2 SMTP. Raises on failure."""
        gmail_user    = (os.environ.get("GMAIL_USER", "").strip()
                         or cfg.get("gmail_user", "").strip())
        from_addr     = (os.environ.get("EMAIL_FROM", "").strip()
                         or cfg.get("from_addr", "").strip()
                         or gmail_user
                         or "noreply@system.local")

        if not _oauth_configured():
            if _oauth_partial():
                raise RuntimeError(
                    "Gmail OAuth2 setup incomplete — GMAIL_REFRESH_TOKEN or GMAIL_USER not set. "
                    "Visit http://localhost:5050/api/email/auth to complete the consent flow."
                )
            raise RuntimeError(
                "Gmail OAuth2 not configured — set GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET, "
                "GMAIL_REFRESH_TOKEN, GMAIL_USER env vars and restart the server."
            )

        access_token = _get_access_token()
        xoauth2_b64  = _build_xoauth2(gmail_user, access_token)

        mime_msg = MIMEMultipart("alternative")
        mime_msg["Subject"] = subject
        mime_msg["From"]    = from_addr
        mime_msg["To"]      = to_addr
        if cc_list:
            mime_msg["Cc"] = ", ".join(cc_list)
        all_rcpts = [to_addr] + cc_list + bcc_list
        mime_msg.attach(MIMEText(body, "html" if is_html else "plain"))

        with smtplib.SMTP(GMAIL_SMTP_HOST, GMAIL_SMTP_PORT, timeout=15) as srv:
            srv.ehlo()
            srv.starttls()
            srv.ehlo()
            srv.docmd("AUTH", "XOAUTH2 " + xoauth2_b64)
            srv.sendmail(from_addr, all_rcpts, mime_msg.as_string())

        return "gmail-oauth2-smtp"

    _write_status("gmail-oauth2-smtp", 0, 0, "")

    while True:
        if agent_should_stop(aid):
            set_agent(aid, status="idle", task="Stopped")
            agent_sleep(aid, 2)
            continue

        # Refresh status on each cycle so OAuth state is always current
        if _oauth_configured():
            _cur_oauth = "oauth:ready"
        elif _oauth_partial():
            _cur_oauth = "oauth:pending-token — visit /api/email/auth"
        else:
            _cur_oauth = "oauth:not-configured"

        try:
            _today = time.strftime("%Y-%m-%d")
            if _today != _daily_send_date:
                _daily_send_count = 0
                _daily_send_date  = _today

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

                    if not is_html and msg.get("use_template", False):
                        body = _html_wrap(subject, body)
                        is_html = True

                    set_agent(aid, status="busy", progress=50,
                              task=f"Sending to {to_addr}: {subject[:40]}")

                    if not to_addr:
                        reason = "no recipient — set EMAIL_TO env var or data/email_config.json default_to"
                        add_log(aid, f"Cannot send: {reason}", "warn")
                        failed = []
                        if os.path.exists(FAILED_FILE):
                            try:
                                with open(FAILED_FILE) as f: failed = json.load(f)
                            except Exception: pass
                        msg["error"] = reason
                        failed.append(msg)
                        os.makedirs(os.path.dirname(FAILED_FILE), exist_ok=True)
                        with open(FAILED_FILE, "w") as f:
                            json.dump(failed, f, indent=2)
                        _append_log("", subject, "none", False)
                    else:
                        if _daily_send_count >= 50:
                            add_log(aid, "Daily send cap reached: 50 emails sent today — skipping remaining queue", "warn")
                            queue.insert(0, msg)
                            with open(QUEUE_FILE, "w") as f:
                                json.dump(queue, f)
                        else:
                            # Retry logic: 3 attempts with 5s backoff
                            last_err    = None
                            method_used = None
                            for attempt in range(1, 4):
                                try:
                                    method_used = _send_once(to_addr, subject, body, is_html,
                                                             cc_list, bcc_list, cfg)
                                    last_err = None
                                    break
                                except Exception as exc:
                                    last_err = exc
                                    add_log(aid, f"Send attempt {attempt}/3 failed: {exc}", "warn")
                                    if attempt < 3:
                                        time.sleep(5)

                            if last_err is None:
                                sent_count        += 1
                                _daily_send_count += 1
                                last_recipient = to_addr
                                last_subject   = subject
                                last_sent_ts   = time.strftime("%Y-%m-%dT%H:%M:%S")
                                add_log(aid, f"Sent via {method_used} to {to_addr}: {subject}", "ok")
                                _append_log(to_addr, subject, method_used, True)
                                _write_status(method_used or "gmail-oauth2-smtp", sent_count, failed_count, to_addr)
                            else:
                                failed_count += 1
                                add_log(aid, f"Send failed after 3 attempts: {last_err}", "error")
                                set_agent(aid, status="error", task=f"Send failed: {str(last_err)[:60]}")
                                _append_log(to_addr, subject, "failed", False)
                                _write_status("gmail-oauth2-smtp", sent_count, failed_count, last_recipient)
                                failed = []
                                if os.path.exists(FAILED_FILE):
                                    try:
                                        with open(FAILED_FILE) as f: failed = json.load(f)
                                    except Exception: pass
                                msg["error"] = str(last_err)
                                failed.append(msg)
                                os.makedirs(os.path.dirname(FAILED_FILE), exist_ok=True)
                                with open(FAILED_FILE, "w") as f:
                                    json.dump(failed, f, indent=2)

                    _ts_info  = f" @ {last_sent_ts}" if last_sent_ts else ""
                    last_info = f"last\u2192{last_recipient}: {last_subject[:30]}{_ts_info}" if last_recipient else "awaiting requests"
                    set_agent(aid, status="idle", progress=0,
                              task=f"Standby | {sent_count} sent {failed_count} failed | today:{_daily_send_count}/50 | {_cur_oauth} | {last_info}")

        except Exception as e:
            add_log(aid, f"Queue error: {e}", "error")

        cur = agents.get(aid, {})
        if cur.get("status") not in ("busy", "error"):
            _ts_info  = f" @ {last_sent_ts}" if last_sent_ts else ""
            last_info = f"last\u2192{last_recipient}: {last_subject[:30]}{_ts_info}" if last_recipient else "awaiting requests"
            set_agent(aid, status="idle", progress=0,
                      task=f"Standby \u2014 {sent_count} sent {failed_count} failed | today:{_daily_send_count}/50 | {_cur_oauth} | {last_info}")
        agent_sleep(aid, 5)
