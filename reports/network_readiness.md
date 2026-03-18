# Network Readiness Report

**Agent:** NetScout
**Date:** 2026-03-18
**Overall Status:** READY (with notes)

---

## 1. Service Connectivity

| Service | Endpoint | Status | HTTP Code | Latency (total) | DNS (ms) | TLS (ms) | Remote IP |
|---------|----------|--------|-----------|-----------------|----------|----------|-----------|
| Bluesky API | bsky.social/xrpc | **UP** | 200 | 661ms | 2ms | 438ms | 52.72.250.30 |
| Stripe API | api.stripe.com/v1 | **UP** | 404 (expected — no auth) | 44ms | 2ms | 32ms | 52.62.14.35 |
| Gmail SMTP | smtp.gmail.com | **UP** | N/A (not HTTP) | — | 12ms | — | 172.217.194.108 |

### Gmail SMTP Port Status
- Port 587 (STARTTLS): **OPEN**
- Port 465 (SSL): **OPEN**

---

## 2. DNS Resolution

| Host | Resolved IPs | Status |
|------|-------------|--------|
| bsky.social | 52.5.16.34, 54.84.141.39, 32.192.58.14, 54.224.90.131, 32.192.150.187 | Healthy (5 IPs, good redundancy) |
| api.stripe.com | 52.62.14.35, 13.55.5.15, 13.55.153.188 | Healthy (3 IPs, AP-region) |
| smtp.gmail.com | 172.217.194.108 | Healthy |

DNS resolution times are all under 15ms — no bottleneck here.

---

## 3. Latency Analysis

| Metric | Bluesky | Stripe | Gmail |
|--------|---------|--------|-------|
| DNS lookup | 2ms | 2ms | 12ms |
| TCP connect | 218ms | 13ms | — |
| TLS handshake | 438ms | 32ms | — |
| Total | 661ms | 44ms | — |

### Notes
- **Bluesky** has the highest latency (661ms). The IPs resolve to US-East (AWS), so this is expected from an Australian connection. TLS negotiation accounts for most of the time.
- **Stripe** is very fast (44ms) — resolving to AP-Southeast (Sydney), indicating a local edge.
- **Gmail SMTP** ports are responsive; DNS is slightly slower (12ms) but well within normal range.

---

## 4. Network Interface

- **Active interface:** en1 (Wi-Fi) via gateway 192.168.0.1
- **en0 (Ethernet):** Inactive
- **IPv6:** Available via utun0

No bottlenecks detected at the local network level.

---

## 5. Verdict

| Check | Result |
|-------|--------|
| External connectivity | PASS |
| DNS resolution | PASS |
| Bluesky API reachable | PASS |
| Stripe API reachable | PASS |
| Gmail SMTP ports open | PASS |
| Network bottlenecks | NONE DETECTED |

**All systems are go.** The only advisory is Bluesky's 661ms round-trip due to geographic distance (US-East servers), which is normal and not a blocker.
