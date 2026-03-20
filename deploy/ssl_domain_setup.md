# SSL + Custom Domain Setup Guide — secondmindhq.com → Render

**Service:** command-centre on Render
**Domain:** secondmindhq.com (registered on Squarespace)
**Target:** https://hq.secondmindhq.com

---

## 1. Point DNS from Squarespace to Render

### Step 1a — Add custom domains in Render

1. Log in to [Render Dashboard](https://dashboard.render.com)
2. Select the **command-centre** web service
3. Go to **Settings → Custom Domains**
4. Click **Add Custom Domain** and enter: `secondmindhq.com`
5. Click **Add Custom Domain** again and enter: `www.secondmindhq.com`
6. Render will display the required DNS records — note them down (they should match below)

### Step 1b — Configure DNS records in Squarespace

1. Log in to [Squarespace Domains](https://account.squarespace.com)
2. Go to **Domains → secondmindhq.com → DNS Settings**
3. **Delete** any existing A records or CNAME records for `@` and `www` that point to Squarespace
4. Add the following records:

| Type  | Host | Value                          | TTL  |
|-------|------|--------------------------------|------|
| A     | @    | `216.24.57.1`                  | 3600 |
| CNAME | www  | `hq.secondmindhq.com`  | 3600 |

> **Note:** The A record IP `216.24.57.1` is Render's load balancer. Confirm this in the Render dashboard as it may change. The CNAME for `www` points to your Render service URL.

### Step 1c — Wait for DNS propagation

- Typically 5–30 minutes, can take up to 48 hours
- Monitor propagation:
  ```bash
  dig secondmindhq.com A +short
  # Expected: 216.24.57.1

  dig www.secondmindhq.com CNAME +short
  # Expected: hq.secondmindhq.com.
  ```
- Check via external resolver to confirm global propagation:
  ```bash
  dig @8.8.8.8 secondmindhq.com A +short
  ```

---

## 2. Enable SSL on Render (Auto TLS)

Render provisions SSL certificates automatically via Let's Encrypt once DNS is correctly pointed.

### What happens automatically

1. After adding custom domains in Render and pointing DNS, Render detects the domain resolves to its infrastructure
2. Render requests a Let's Encrypt certificate covering both `secondmindhq.com` and `www.secondmindhq.com`
3. Certificate is installed and HTTPS is enabled — **no manual action required**
4. Render auto-renews certificates before expiry

### If SSL does not provision automatically

- Verify DNS is resolving correctly (see Step 1c)
- Check that no **CAA DNS records** are blocking Let's Encrypt:
  ```bash
  dig secondmindhq.com CAA +short
  # Should be empty, or include: 0 issue "letsencrypt.org"
  ```
- In Render dashboard, go to **Settings → Custom Domains** — click the domain and check the SSL status. If it shows "pending", DNS may not have propagated yet
- If stuck, remove and re-add the custom domain in Render to trigger a new certificate request

### Force HTTPS redirect

Add to `agent_server.py` to redirect HTTP → HTTPS in production:

```python
@app.before_request
def force_https():
    if request.headers.get('X-Forwarded-Proto') == 'http':
        return redirect(request.url.replace('http://', 'https://'), code=301)
```

### Security headers

Add to `agent_server.py`:

```python
@app.after_request
def security_headers(response):
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    return response
```

---

## 3. Custom Domain Verification Steps

### In Render Dashboard

1. Navigate to **command-centre → Settings → Custom Domains**
2. Each domain should show a green checkmark with status **"Verified"**
3. SSL status should show **"Active"** or **"Certificate issued"**

### From terminal

```bash
# Verify A record
dig secondmindhq.com A +short
# → 216.24.57.1

# Verify CNAME
dig www.secondmindhq.com CNAME +short
# → hq.secondmindhq.com.

# Verify SSL certificate
echo | openssl s_client -servername secondmindhq.com -connect secondmindhq.com:443 2>/dev/null | openssl x509 -noout -subject -issuer -dates

# Verify HTTPS response
curl -I https://secondmindhq.com/
# → HTTP/2 200

# Verify HTTP→HTTPS redirect
curl -I http://secondmindhq.com/
# → 301/302 → https://secondmindhq.com/
```

### Using the verification script

A comprehensive automated checker is available:

```bash
# Full verification (DNS + SSL + endpoints + security headers)
./deploy/ssl_custom_domain.sh

# DNS only
./deploy/ssl_custom_domain.sh --dns-only

# SSL only
./deploy/ssl_custom_domain.sh --ssl-only

# Show remediation steps for any failures
./deploy/ssl_custom_domain.sh --fix
```

---

## 4. Testing Checklist

Run through this checklist after DNS propagation and SSL provisioning:

### DNS

- [ ] `dig secondmindhq.com A +short` returns `216.24.57.1`
- [ ] `dig www.secondmindhq.com CNAME +short` returns `hq.secondmindhq.com`
- [ ] `dig @8.8.8.8 secondmindhq.com A +short` confirms external propagation
- [ ] No blocking CAA records present

### SSL / TLS

- [ ] `https://secondmindhq.com` loads without certificate warnings
- [ ] `https://www.secondmindhq.com` loads without certificate warnings
- [ ] Certificate issuer is Let's Encrypt (R3/R10/R11/E5/E6)
- [ ] Certificate covers both `secondmindhq.com` and `www.secondmindhq.com`
- [ ] Certificate expiry is >30 days out

### Redirects

- [ ] `http://secondmindhq.com` redirects to `https://secondmindhq.com`
- [ ] `http://www.secondmindhq.com` redirects to `https://www.secondmindhq.com`
- [ ] `https://www.secondmindhq.com` serves content (or redirects to apex)

### Content Parity

- [ ] `https://secondmindhq.com` serves the same content as `https://hq.secondmindhq.com`
- [ ] Landing page loads correctly with all assets (CSS, images, fonts)
- [ ] Stripe checkout links work from the custom domain
- [ ] API endpoints respond at `https://secondmindhq.com/api/status`

### Security Headers

- [ ] `Strict-Transport-Security` header present
- [ ] `X-Content-Type-Options: nosniff` header present
- [ ] `X-Frame-Options: SAMEORIGIN` header present

### Automated Verification

- [ ] `./deploy/ssl_custom_domain.sh` passes with 0 failures

---

## Quick Reference

| Item | Value |
|------|-------|
| Domain | secondmindhq.com |
| DNS Provider | Squarespace |
| Hosting | Render (command-centre) |
| Render URL | https://hq.secondmindhq.com |
| Render LB IP | 216.24.57.1 |
| SSL Provider | Let's Encrypt (auto via Render) |
| Verification Script | `deploy/ssl_custom_domain.sh` |
