# Domain & DNS Configuration — secondmindhq.com

## Current State
- **Domain**: secondmindhq.com (Squarespace Domains)
- **Hosting**: Render.com (service: `command-centre`)
- **Render URL**: hq.secondmindhq.com

## DNS Records to Configure (Squarespace → Render)

Log into Squarespace Domains → secondmindhq.com → DNS Settings.

### Root domain (secondmindhq.com)
| Type  | Host | Value                          | TTL  |
|-------|------|--------------------------------|------|
| A     | @    | 216.24.57.1 (Render static IP) | 3600 |

> Note: Render's load balancer IP. Verify current IP at https://docs.render.com/custom-domains

### www subdomain
| Type  | Host | Value                               | TTL  |
|-------|------|-------------------------------------|------|
| CNAME | www  | hq.secondmindhq.com         | 3600 |

### API subdomain (optional, if separating API)
| Type  | Host | Value                               | TTL  |
|-------|------|-------------------------------------|------|
| CNAME | api  | hq.secondmindhq.com         | 3600 |

## Render Custom Domain Setup

1. Go to Render Dashboard → `command-centre` service → Settings → Custom Domains
2. Add `secondmindhq.com`
3. Add `www.secondmindhq.com`
4. Render auto-provisions SSL via Let's Encrypt once DNS propagates

## Verification

```bash
# Check DNS propagation (may take up to 48h, usually ~30min)
dig secondmindhq.com A +short
dig www.secondmindhq.com CNAME +short

# Check SSL
curl -I https://secondmindhq.com
```

## Squarespace DNS Panel Path
Squarespace account (secondminddev@gmail.com) → Domains → secondmindhq.com → DNS → DNS Settings → Custom Records
