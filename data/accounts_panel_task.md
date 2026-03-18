# Task: Add Accounts & Links Tab to Dashboard

File: /Users/secondmind/claudecodetest/agent-command-centre.html

## EDIT 1 — Tab button (find line ~2811, after the Mobile button)

Find:
```
<button class="top-tab-btn" id="toptab-mobile" onclick="switchTopTab('mobile')">Mobile</button>
```
Add AFTER it:
```html
  <button class="top-tab-btn" id="toptab-accounts" onclick="switchTopTab('accounts'); loadAccountsPanel();">Accounts</button>
```

## EDIT 2 — Tab panel (find the end of mobile panel, around line 3406)

Find: `</div><!-- /#tab-panel-mobile -->`

Add AFTER it:
```html
<div class="top-tab-panel" id="tab-panel-accounts" style="flex:1;overflow-y:auto;background:var(--bg);padding:1.2rem;">
  <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:1rem;">
    <div>
      <div style="font-size:1.1rem;font-weight:700;color:var(--cyan);letter-spacing:0.05em;">Accounts &amp; Links</div>
      <div style="font-size:0.72rem;color:rgba(255,255,255,0.5);margin-top:0.2rem;">External accounts, credentials &amp; API keys managed by AccountProvisioner</div>
    </div>
    <button onclick="loadAccountsPanel()" style="background:rgba(0,200,255,0.1);border:1px solid rgba(0,200,255,0.3);color:var(--cyan);padding:0.4rem 0.9rem;border-radius:4px;cursor:pointer;font-size:0.72rem;font-family:inherit;">&#8635; Refresh</button>
  </div>
  <div id="accounts-panel-body" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:0.75rem;">
    <div style="color:rgba(255,255,255,0.4);font-size:0.8rem;padding:2rem;text-align:center;grid-column:1/-1;">Loading accounts...</div>
  </div>
</div><!-- /#tab-panel-accounts -->
```

## EDIT 3 — JavaScript (find the last </script> tag, add before it)

```javascript
// ── Accounts & Links Panel ────────────────────────────────────────
const _PLATFORM_ICONS = {
  guerrillamail:'📧', disposable_email:'📧',
  slack:'💬', openai:'🤖', anthropic:'🧠',
  github:'🐙', twitter:'🐦', reddit:'🦊',
  instagram:'📸', wallet:'💰', crypto:'💰', default:'🔑'
};
function _acctIcon(svc) {
  if (!svc) return _PLATFORM_ICONS.default;
  const k = svc.toLowerCase();
  return _PLATFORM_ICONS[k] || _PLATFORM_ICONS.default;
}
function _statusBadge(status) {
  const map = {
    active:['#00ff88','active'],
    'needs-config':['#ff9500','needs-config'],
    pending:['#ffcc00','pending'],
    'PENDING_HUMAN_REVIEW':['#ffcc00','pending'],
    error:['#ff4444','error']
  };
  const [col, label] = map[status] || map['needs-config'];
  return `<span style="background:${col}22;color:${col};border:1px solid ${col}44;padding:0.15rem 0.5rem;border-radius:10px;font-size:0.62rem;font-weight:600;">${label}</span>`;
}
function _acctCard(rec) {
  const svc = rec.service || rec.type || 'unknown';
  const icon = _acctIcon(svc);
  const name = (rec.email || rec.token || rec.username || rec.address || '—').substring(0, 42);
  const url = rec.signup_url || rec.url || '';
  const status = rec.status || (rec.type === 'disposable_email' || rec.type === 'internal_token' ? 'active' : 'needs-config');
  const openBtn = url
    ? `<a href="${url}" target="_blank" rel="noopener" style="background:rgba(0,200,255,0.1);border:1px solid rgba(0,200,255,0.3);color:var(--cyan);padding:0.25rem 0.6rem;border-radius:4px;cursor:pointer;font-size:0.65rem;text-decoration:none;">Open ↗</a>`
    : `<span style="color:rgba(255,255,255,0.25);font-size:0.65rem;">No URL</span>`;
  return `<div style="background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.08);border-radius:8px;padding:0.9rem;transition:border-color 0.2s;" onmouseenter="this.style.borderColor='rgba(0,200,255,0.4)'" onmouseleave="this.style.borderColor='rgba(255,255,255,0.08)'">
    <div style="display:flex;align-items:center;gap:0.5rem;margin-bottom:0.5rem;">
      <span style="font-size:1.1rem;">${icon}</span>
      <span style="font-weight:700;font-size:0.8rem;color:var(--text);text-transform:capitalize;">${svc}</span>
      <span style="margin-left:auto;">${_statusBadge(status)}</span>
    </div>
    <div style="font-size:0.72rem;color:rgba(255,255,255,0.6);margin-bottom:0.6rem;word-break:break-all;">${name}</div>
    <div>${openBtn}</div>
  </div>`;
}
function _apiKeyCard(svc, info) {
  const icon = _acctIcon(svc);
  const status = info.configured ? 'active' : 'needs-config';
  const detail = info.configured ? `${info.key_count} key${info.key_count!==1?'s':''} configured` : 'No keys — add to api_key_pool.json';
  return `<div style="background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.08);border-radius:8px;padding:0.9rem;transition:border-color 0.2s;" onmouseenter="this.style.borderColor='rgba(0,200,255,0.4)'" onmouseleave="this.style.borderColor='rgba(255,255,255,0.08)'">
    <div style="display:flex;align-items:center;gap:0.5rem;margin-bottom:0.5rem;">
      <span style="font-size:1.1rem;">${icon}</span>
      <span style="font-weight:700;font-size:0.8rem;color:var(--text);text-transform:capitalize;">${svc} API</span>
      <span style="margin-left:auto;">${_statusBadge(status)}</span>
    </div>
    <div style="font-size:0.72rem;color:rgba(255,255,255,0.5);">${detail}</div>
  </div>`;
}
function _sectionHeader(title) {
  return `<div style="grid-column:1/-1;color:var(--cyan);font-size:0.68rem;font-weight:700;letter-spacing:0.12em;text-transform:uppercase;padding:0.5rem 0 0.2rem;border-bottom:1px solid rgba(0,200,255,0.15);margin-bottom:0.25rem;">${title}</div>`;
}
async function loadAccountsPanel() {
  const body = document.getElementById('accounts-panel-body');
  if (!body) return;
  body.innerHTML = '<div style="color:rgba(255,255,255,0.4);font-size:0.8rem;padding:2rem;text-align:center;grid-column:1/-1;">Loading...</div>';
  try {
    const [apRes, sbRes] = await Promise.all([
      fetch('/api/account_provisioner/status').then(r=>r.json()).catch(()=>({accounts:[],api_keys:{}})),
      fetch('/api/social_bridge/status').then(r=>r.json()).catch(()=>({accounts:[]}))
    ]);
    const accounts = apRes.accounts || [];
    const apiKeys  = apRes.api_keys || {};
    const socials  = sbRes.accounts || [];
    const emails   = accounts.filter(a => a.type === 'disposable_email');
    const tokens   = accounts.filter(a => a.type === 'internal_token');
    const external = accounts.filter(a => a.type && a.type !== 'disposable_email' && a.type !== 'internal_token');
    let html = '';
    if (emails.length)  html += _sectionHeader('📧 Email Accounts') + emails.map(_acctCard).join('');
    if (Object.keys(apiKeys).length) html += _sectionHeader('🔑 API Keys') + Object.entries(apiKeys).map(([s,i])=>_apiKeyCard(s,i)).join('');
    if (external.length) html += _sectionHeader('🔗 External Services') + external.map(_acctCard).join('');
    if (tokens.length)  html += _sectionHeader('🎟 Internal Tokens') + tokens.map(_acctCard).join('');
    if (socials.length) html += _sectionHeader('📣 Social Accounts') + socials.map(_acctCard).join('');
    if (!html) html = '<div style="color:rgba(255,255,255,0.4);font-size:0.8rem;padding:2rem;text-align:center;grid-column:1/-1;">No accounts found.</div>';
    body.innerHTML = html;
  } catch(e) {
    body.innerHTML = `<div style="color:#ff4444;font-size:0.8rem;padding:2rem;text-align:center;grid-column:1/-1;">Error: ${e.message}</div>`;
  }
}
setInterval(()=>{ if(document.getElementById('tab-panel-accounts')?.classList.contains('active')) loadAccountsPanel(); }, 30000);
// ── End Accounts & Links Panel ──────────────────────────────────────
```
