#!/usr/bin/env bash
#
# ssl_custom_domain.sh — Verify and configure SSL + custom domain for AI HQ on Render
#
# Usage:
#   ./deploy/ssl_custom_domain.sh              # Full check: DNS + SSL + HTTP
#   ./deploy/ssl_custom_domain.sh --dns-only   # DNS propagation check only
#   ./deploy/ssl_custom_domain.sh --ssl-only   # SSL certificate check only
#   ./deploy/ssl_custom_domain.sh --fix        # Print remediation steps for failures
#
set -euo pipefail

# ── Config ────────────────────────────────────────────────────────────────────
DOMAIN="secondmindhq.com"
WWW_DOMAIN="www.secondmindhq.com"
RENDER_SERVICE="command-centre"
RENDER_URL="https://${RENDER_SERVICE}.onrender.com"
RENDER_EXPECTED_IP="216.24.57.1"
RENDER_CNAME="${RENDER_SERVICE}.onrender.com"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

PASS=0; WARN=0; FAIL=0
MODE="${1:-all}"

log()  { echo -e "${CYAN}[ssl-domain]${NC} $*"; }
ok()   { echo -e "  ${GREEN}✔${NC} $*"; PASS=$((PASS + 1)); }
warn() { echo -e "  ${YELLOW}⚠${NC} $*"; WARN=$((WARN + 1)); }
fail() { echo -e "  ${RED}✖${NC} $*"; FAIL=$((FAIL + 1)); }
hdr()  { echo ""; echo -e "${BOLD}$*${NC}"; }

# ── DNS Checks ────────────────────────────────────────────────────────────────
check_dns() {
    hdr "DNS Configuration"

    # Root domain A record
    log "Checking $DOMAIN A record..."
    a_record=$(dig +short "$DOMAIN" A 2>/dev/null | head -1 || echo "")
    if [[ -z "$a_record" ]]; then
        fail "$DOMAIN — no A record found"
    elif [[ "$a_record" == "$RENDER_EXPECTED_IP" ]]; then
        ok "$DOMAIN → $a_record (Render load balancer)"
    else
        warn "$DOMAIN → $a_record (expected $RENDER_EXPECTED_IP)"
    fi

    # www CNAME
    log "Checking $WWW_DOMAIN CNAME..."
    www_cname=$(dig +short "$WWW_DOMAIN" CNAME 2>/dev/null | head -1 | sed 's/\.$//' || echo "")
    if [[ -z "$www_cname" ]]; then
        fail "$WWW_DOMAIN — no CNAME record found"
    elif [[ "$www_cname" == "$RENDER_CNAME" ]]; then
        ok "$WWW_DOMAIN → $www_cname"
    else
        warn "$WWW_DOMAIN → $www_cname (expected $RENDER_CNAME)"
    fi

    # Check DNS propagation via external resolvers
    log "Checking propagation via Google DNS (8.8.8.8)..."
    ext_a=$(dig @8.8.8.8 +short "$DOMAIN" A 2>/dev/null | head -1 || echo "")
    if [[ "$ext_a" == "$RENDER_EXPECTED_IP" ]]; then
        ok "Google DNS resolves $DOMAIN → $ext_a"
    elif [[ -n "$ext_a" ]]; then
        warn "Google DNS resolves $DOMAIN → $ext_a (expected $RENDER_EXPECTED_IP)"
    else
        warn "Google DNS cannot resolve $DOMAIN yet — propagation pending"
    fi

    # CAA record check (optional but good for SSL)
    log "Checking CAA records..."
    caa=$(dig +short "$DOMAIN" CAA 2>/dev/null || echo "")
    if [[ -z "$caa" ]]; then
        ok "No CAA restrictions — Let's Encrypt can issue certificates"
    elif echo "$caa" | grep -qi "letsencrypt"; then
        ok "CAA allows Let's Encrypt"
    else
        warn "CAA records present but may block Let's Encrypt: $caa"
    fi
}

# ── SSL Certificate Checks ───────────────────────────────────────────────────
check_ssl() {
    hdr "SSL / TLS Certificate"

    for host in "$DOMAIN" "$WWW_DOMAIN"; do
        log "Checking SSL for $host..."

        # Attempt SSL connection
        cert_info=$(echo | openssl s_client -servername "$host" -connect "$host:443" 2>/dev/null || echo "CONNECT_FAIL")

        if echo "$cert_info" | grep -q "CONNECT_FAIL\|connect:errno"; then
            fail "$host — SSL connection failed (DNS may not be pointed yet)"
            continue
        fi

        # Extract certificate details
        cert_subject=$(echo "$cert_info" | openssl x509 -noout -subject 2>/dev/null || echo "")
        cert_issuer=$(echo "$cert_info" | openssl x509 -noout -issuer 2>/dev/null || echo "")
        cert_dates=$(echo "$cert_info" | openssl x509 -noout -dates 2>/dev/null || echo "")
        cert_san=$(echo "$cert_info" | openssl x509 -noout -ext subjectAltName 2>/dev/null || echo "")

        # Check if cert covers this domain
        if echo "$cert_subject $cert_san" | grep -qi "$host"; then
            ok "$host — certificate covers this domain"
        else
            warn "$host — certificate may not cover this domain"
            echo "        Subject: $cert_subject"
        fi

        # Check issuer (Let's Encrypt or Render)
        if echo "$cert_issuer" | grep -qi "Let's Encrypt\|R3\|R10\|R11\|E5\|E6"; then
            ok "$host — issued by Let's Encrypt"
        elif echo "$cert_issuer" | grep -qi "render"; then
            ok "$host — issued by Render"
        elif [[ -n "$cert_issuer" ]]; then
            warn "$host — issuer: $cert_issuer"
        fi

        # Check expiry
        if [[ -n "$cert_dates" ]]; then
            not_after=$(echo "$cert_dates" | grep "notAfter" | cut -d= -f2)
            expiry_epoch=$(date -jf "%b %d %T %Y %Z" "$not_after" "+%s" 2>/dev/null || date -d "$not_after" "+%s" 2>/dev/null || echo "0")
            now_epoch=$(date "+%s")
            days_left=$(( (expiry_epoch - now_epoch) / 86400 ))

            if (( days_left > 30 )); then
                ok "$host — expires in ${days_left} days ($not_after)"
            elif (( days_left > 0 )); then
                warn "$host — expires in ${days_left} days — renewal soon"
            elif (( expiry_epoch > 0 )); then
                fail "$host — certificate EXPIRED ($not_after)"
            fi
        fi
    done

    # Check HTTPS redirect from HTTP
    hdr "HTTP → HTTPS Redirect"
    for host in "$DOMAIN" "$WWW_DOMAIN"; do
        log "Checking http://$host redirect..."
        redirect=$(curl -s -o /dev/null -w "%{http_code}|%{redirect_url}" "http://$host/" --max-time 10 2>/dev/null || echo "000|")
        code=$(echo "$redirect" | cut -d'|' -f1)
        location=$(echo "$redirect" | cut -d'|' -f2)

        if [[ "$code" == "301" || "$code" == "302" ]] && echo "$location" | grep -qi "https://"; then
            ok "http://$host → HTTPS redirect ($code)"
        elif [[ "$code" == "200" ]]; then
            warn "http://$host serves HTTP 200 without redirect — HTTPS not enforced"
        elif [[ "$code" == "000" ]]; then
            warn "http://$host — unreachable"
        else
            warn "http://$host — HTTP $code (expected 301/302 redirect)"
        fi
    done
}

# ── HTTP Endpoint Verification ────────────────────────────────────────────────
check_endpoints() {
    hdr "HTTPS Endpoint Verification"

    for base in "https://$DOMAIN" "https://$WWW_DOMAIN"; do
        log "Testing $base..."
        status=$(curl -s -o /dev/null -w "%{http_code}" "$base/" --max-time 10 2>/dev/null || echo "000")
        if [[ "$status" == "200" ]]; then
            ok "$base/ → HTTP $status"
        elif [[ "$status" == "000" ]]; then
            warn "$base/ → unreachable"
        else
            warn "$base/ → HTTP $status"
        fi
    done

    # Compare Render URL vs custom domain
    log "Comparing Render URL vs custom domain response..."
    render_hash=$(curl -s "$RENDER_URL/" --max-time 10 2>/dev/null | md5 2>/dev/null || curl -s "$RENDER_URL/" --max-time 10 2>/dev/null | md5sum 2>/dev/null | cut -d' ' -f1 || echo "n/a")
    custom_hash=$(curl -s "https://$DOMAIN/" --max-time 10 2>/dev/null | md5 2>/dev/null || curl -s "https://$DOMAIN/" --max-time 10 2>/dev/null | md5sum 2>/dev/null | cut -d' ' -f1 || echo "n/a")

    if [[ "$render_hash" == "$custom_hash" && "$render_hash" != "n/a" ]]; then
        ok "Render URL and custom domain serve identical content"
    elif [[ "$custom_hash" == "n/a" ]]; then
        warn "Could not fetch custom domain content for comparison"
    else
        warn "Content differs between Render URL and custom domain"
    fi
}

# ── Security Headers ─────────────────────────────────────────────────────────
check_security_headers() {
    hdr "Security Headers (HTTPS)"

    headers=$(curl -s -I "https://$DOMAIN/" --max-time 10 2>/dev/null || echo "")
    if [[ -z "$headers" ]]; then
        warn "Could not fetch headers from https://$DOMAIN/"
        return
    fi

    # HSTS
    if echo "$headers" | grep -qi "strict-transport-security"; then
        ok "HSTS header present"
    else
        warn "HSTS header missing — add Strict-Transport-Security for HTTPS enforcement"
    fi

    # X-Content-Type-Options
    if echo "$headers" | grep -qi "x-content-type-options"; then
        ok "X-Content-Type-Options present"
    else
        warn "X-Content-Type-Options missing"
    fi

    # X-Frame-Options
    if echo "$headers" | grep -qi "x-frame-options"; then
        ok "X-Frame-Options present"
    else
        warn "X-Frame-Options missing"
    fi
}

# ── Remediation Guide ────────────────────────────────────────────────────────
show_fix() {
    hdr "Remediation Steps"
    echo ""
    echo -e "${BOLD}1. Add custom domains in Render Dashboard:${NC}"
    echo "   → https://dashboard.render.com → command-centre → Settings → Custom Domains"
    echo "   → Add: $DOMAIN"
    echo "   → Add: $WWW_DOMAIN"
    echo ""
    echo -e "${BOLD}2. Configure DNS in Squarespace:${NC}"
    echo "   → https://account.squarespace.com → Domains → $DOMAIN → DNS Settings"
    echo "   → A record:     @ → $RENDER_EXPECTED_IP (TTL 3600)"
    echo "   → CNAME record: www → $RENDER_CNAME (TTL 3600)"
    echo ""
    echo -e "${BOLD}3. Wait for DNS propagation:${NC}"
    echo "   → Usually 5-30 minutes, can take up to 48 hours"
    echo "   → Monitor: dig $DOMAIN A +short"
    echo ""
    echo -e "${BOLD}4. SSL auto-provisions:${NC}"
    echo "   → Render issues Let's Encrypt cert automatically once DNS resolves"
    echo "   → Check: openssl s_client -servername $DOMAIN -connect $DOMAIN:443"
    echo ""
    echo -e "${BOLD}5. Add security headers in agent_server.py:${NC}"
    cat <<'PYCODE'
   @app.after_request
   def security_headers(response):
       response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
       response.headers['X-Content-Type-Options'] = 'nosniff'
       response.headers['X-Frame-Options'] = 'SAMEORIGIN'
       return response
PYCODE
    echo ""
    echo -e "${BOLD}6. Force HTTPS redirect (add to agent_server.py):${NC}"
    cat <<'PYCODE'
   @app.before_request
   def force_https():
       if request.headers.get('X-Forwarded-Proto') == 'http':
           return redirect(request.url.replace('http://', 'https://'), code=301)
PYCODE
    echo ""
}

# ── Main ──────────────────────────────────────────────────────────────────────
main() {
    echo ""
    echo "  ╔═══════════════════════════════════════════════════╗"
    echo "  ║   AI HQ — SSL & Custom Domain Verification       ║"
    echo "  ╚═══════════════════════════════════════════════════╝"
    echo ""
    echo "  Domain:  $DOMAIN / $WWW_DOMAIN"
    echo "  Render:  $RENDER_URL"
    echo ""

    case "$MODE" in
        --dns-only) check_dns ;;
        --ssl-only) check_ssl ;;
        --fix)      show_fix ;;
        *)
            check_dns
            check_ssl
            check_endpoints
            check_security_headers
            ;;
    esac

    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo -e "  Results: ${GREEN}$PASS passed${NC}  ${YELLOW}$WARN warnings${NC}  ${RED}$FAIL failed${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    if (( FAIL > 0 )); then
        echo ""
        echo -e "  ${YELLOW}Run with --fix for remediation steps${NC}"
    fi
    echo ""

    [[ $FAIL -eq 0 ]] && exit 0 || exit 1
}

main
