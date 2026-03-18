# Busy-Agent Pulse Ring — Visual Effect Specification

**Target file:** `agent-command-centre.html`
**Authored:** 2026-03-15
**Scope:** Two render surfaces — (A) the office-floor canvas, (B) the sidebar agent-card `.ac-avatar`

---

## 1. Overview

A concentric expanding ring radiates outward from an agent's head/avatar whenever its status is `active` or `busy`. The effect signals "this agent is doing work" through a looping scale-and-fade animation — analogous to a sonar ping or a radio transmitter pulse.

Two separate but visually coherent implementations are required, one per render surface:

| Surface | Technique | Loop mechanism |
|---|---|---|
| Office canvas (`_drawChar`) | Canvas 2D arc draws each frame in `requestAnimationFrame` loop | Existing `frame` counter drives phase |
| Sidebar `.ac-avatar` | CSS `@keyframes` on a `::before`/`::after` pseudo-element | Browser compositor runs animation |

---

## 2. Design Tokens

These values are drawn from existing CSS variables in the file and should remain consistent:

```css
/* active ring */
--pulse-active-rgb:   0, 255, 136;    /* var(--green) #00ff88 */

/* busy ring */
--pulse-busy-rgb:     0, 200, 255;    /* var(--cyan)  #00c8ff */

/* timing */
--pulse-duration-active: 2.2s;
--pulse-duration-busy:   1.4s;        /* faster cadence = higher urgency */

/* ring sizing (sidebar) */
--pulse-avatar-size: 32px;            /* matches .ac-avatar width/height */
--pulse-ring-max-scale: 2.0;          /* ring expands to 2× avatar size = 64px diameter */
```

---

## 3. CSS Animation (Sidebar Agent Cards)

### 3.1 HTML Structure

Wrap each `.ac-avatar` in a `.ac-avatar-wrap` element so the pulse ring can be an absolutely positioned pseudo-element without disturbing flex layout:

```html
<!-- Before (current) -->
<div class="ac-avatar" style="...">🤖</div>

<!-- After -->
<div class="ac-avatar-wrap">
  <div class="ac-avatar" style="...">🤖</div>
</div>
```

### 3.2 Keyframe Definitions

```css
@keyframes pulse-ring-active {
  0% {
    transform: scale(1.0);
    opacity: 0.7;
  }
  60% {
    transform: scale(1.75);
    opacity: 0.2;
  }
  100% {
    transform: scale(2.0);
    opacity: 0.0;
  }
}

@keyframes pulse-ring-busy {
  0% {
    transform: scale(1.0);
    opacity: 0.85;
  }
  50% {
    transform: scale(1.5);
    opacity: 0.35;
  }
  100% {
    transform: scale(2.0);
    opacity: 0.0;
  }
}
```

### 3.3 Base Ring Styles

```css
.ac-avatar-wrap {
  position: relative;
  width: 32px;
  height: 32px;
  flex-shrink: 0;
}

.ac-avatar-wrap::before,
.ac-avatar-wrap::after {
  content: '';
  position: absolute;
  inset: 0;                        /* same bounding box as avatar */
  border-radius: 10px;             /* slightly larger than avatar's 8px to match expansion */
  border-width: 1.5px;
  border-style: solid;
  transform-origin: center center;
  pointer-events: none;
  animation: none;                 /* inactive by default */
}
```

### 3.4 Activation: status-active

```css
/* Single ring, moderate pace */
.status-active .ac-avatar-wrap::before {
  border-color: rgba(var(--pulse-active-rgb), 0.7);
  animation: pulse-ring-active var(--pulse-duration-active) ease-out infinite;
}

/* Optional second ring, staggered 50% phase */
.status-active .ac-avatar-wrap::after {
  border-color: rgba(var(--pulse-active-rgb), 0.4);
  animation: pulse-ring-active var(--pulse-duration-active) ease-out infinite;
  animation-delay: calc(var(--pulse-duration-active) * -0.5);
}
```

### 3.5 Activation: status-busy

```css
/* Single ring, faster and brighter */
.status-busy .ac-avatar-wrap::before {
  border-color: rgba(var(--pulse-busy-rgb), 0.85);
  animation: pulse-ring-busy var(--pulse-duration-busy) ease-out infinite;
}

/* Second ring, staggered 50% — creates the double-pulse "urgent heartbeat" feel */
.status-busy .ac-avatar-wrap::after {
  border-color: rgba(var(--pulse-busy-rgb), 0.45);
  animation: pulse-ring-busy var(--pulse-duration-busy) ease-out infinite;
  animation-delay: calc(var(--pulse-duration-busy) * -0.5);
}
```

### 3.6 Z-index & Layering (Sidebar)

```
z-index stack (lowest → highest) inside .agent-card:
  ┌─────────────────────────────┐
  │ agent-card background       │  z-index: auto
  │ ac-avatar-wrap::before/after│  z-index: 0  (behind avatar)
  │ .ac-avatar                  │  z-index: 1  (above rings)
  │ .ac-status-dot              │  z-index: 2
  └─────────────────────────────┘
```

Apply:

```css
.ac-avatar-wrap::before,
.ac-avatar-wrap::after { z-index: 0; }
.ac-avatar             { position: relative; z-index: 1; }
```

### 3.7 Full Animation Property Reference

| Property | status-active | status-busy |
|---|---|---|
| `animation-name` | `pulse-ring-active` | `pulse-ring-busy` |
| `animation-duration` | `2.2s` | `1.4s` |
| `animation-timing-function` | `ease-out` | `ease-out` |
| `animation-iteration-count` | `infinite` | `infinite` |
| `animation-fill-mode` | `none` | `none` |
| `border-color` (::before) | `rgba(0,255,136, 0.70)` | `rgba(0,200,255, 0.85)` |
| `border-color` (::after) | `rgba(0,255,136, 0.40)` | `rgba(0,200,255, 0.45)` |
| `animation-delay` (::after) | `-1.1s` | `-0.7s` |

---

## 4. Canvas Animation (Office Floor — `_drawChar`)

The office canvas has no DOM, so the ring is drawn frame-by-frame inside `_drawChar()` using the existing `frame` counter as the animation clock.

### 4.1 Where to Insert

In `_drawChar()` (approx. line 3098), insert the pulse ring draw call **after the shadow draw and before the leg draw**, so it sits underneath the character figure:

```
Shadow         ← draw order 1
[PULSE RING]   ← draw order 2  (new, behind character)
Legs           ← draw order 3
Body           ← draw order 4
Arms           ← draw order 5
CEO/ORC rings  ← draw order 6  (existing special roles)
Head circle    ← draw order 7
Emoji          ← draw order 8
```

### 4.2 Phase Calculation

Each ring wave is a value `p ∈ [0, 1)` derived from `frame` and a per-wave offset:

```js
// Period in frames. At ~60fps:  90 frames ≈ 1.5s (active),  55 frames ≈ 0.9s (busy)
const PERIOD_ACTIVE = 90;
const PERIOD_BUSY   = 55;

const period = (busy) ? PERIOD_BUSY : PERIOD_ACTIVE;

// Two rings, staggered half a period apart
const p0 = (frame % period) / period;           // ring 0: phase 0.0
const p1 = ((frame + period * 0.5) % period) / period;  // ring 1: phase 0.5
```

### 4.3 Ring Geometry

The agent head radius is `10px` for regular agents, `12px` for the CEO (`isCeo`). The pulse ring starts just outside the head and expands to ~2.4× head radius before disappearing:

```js
const headR   = isCeo ? 12 : 10;
const ringMin = headR + 2;        // 12 or 14 — starts flush outside head stroke
const ringMax = headR * 2.4;      // 24 or ~29 — fades before reaching ORC ring (r=17)

// For CEO the ringMax needs to stay below the crown ring (r=14) — adjust:
// isCeo: ringMin=14, ringMax=22 (CEO ring at 14 is the base, expand beyond)
```

### 4.4 Color & Opacity Keyframes per Ring Wave

```js
function drawPulseRing(ctx, cx, cy, p, color, maxAlpha) {
  // p ∈ [0,1): 0=start (small, opaque) → 1=end (large, transparent)
  const eased = 1 - Math.pow(1 - p, 2.2);  // ease-out power curve

  const r     = ringMin + (ringMax - ringMin) * eased;
  const alpha = maxAlpha * (1 - eased);     // linear fade-out

  if (alpha < 0.01) return;

  ctx.beginPath();
  ctx.arc(cx, cy, r, 0, Math.PI * 2);
  ctx.strokeStyle = color.replace(')', `, ${alpha})`).replace('rgb(', 'rgba(');
  // If color is already a hex like '#00ff88', use a helper:
  ctx.strokeStyle = hexToRgba(color, alpha);
  ctx.lineWidth = 1.5;
  ctx.stroke();
}
```

#### Keyframe table (canvas equivalent, sampled at p steps)

| p (phase) | scale factor | opacity (active) | opacity (busy) |
|---|---|---|---|
| 0.00 | 1.00 (ringMin) | 0.65 | 0.80 |
| 0.25 | 1.22 | 0.48 | 0.60 |
| 0.50 | 1.52 | 0.30 | 0.38 |
| 0.75 | 1.82 | 0.13 | 0.16 |
| 1.00 | 2.40 (ringMax) | 0.00 | 0.00 |

### 4.5 Color Assignment

```js
// active: green, busy: cyan — match existing status palette
const pulseColor = busy   ? 'rgba(0,200,255,1)' :   // --cyan
                   active ? 'rgba(0,255,136,1)' :   // --green
                   null;

const maxAlpha   = busy   ? 0.80 : 0.65;
```

### 4.6 Full Canvas Draw Snippet

```js
// ─── Pulse ring — busy/active only ───────────────────────────────────────
if ((busy || active) && !stopped) {
  const period  = busy ? 55 : 90;
  const headR   = isCeo ? 12 : 10;
  const ringMin = headR + 2;
  const ringMax = headR * 2.4;
  const maxAlpha = busy ? 0.80 : 0.65;
  const ringColor = busy ? [0, 200, 255] : [0, 255, 136];

  [0, 0.5].forEach(offset => {
    const p = ((frame + period * offset) % period) / period;
    const eased = 1 - Math.pow(1 - p, 2.2);
    const r   = ringMin + (ringMax - ringMin) * eased;
    const opc = maxAlpha * (1 - eased);
    if (opc < 0.01) return;
    ctx.beginPath();
    ctx.arc(bx, by, r, 0, Math.PI * 2);
    ctx.strokeStyle = `rgba(${ringColor[0]},${ringColor[1]},${ringColor[2]},${opc.toFixed(3)})`;
    ctx.lineWidth = 1.5;
    ctx.stroke();
  });
}
// ─────────────────────────────────────────────────────────────────────────
```

### 4.7 Layering on Canvas (Draw Order in `_drawChar`)

```
BEFORE existing code:
  ctx.fillStyle = 'rgba(0,0,0,0.38)';
  ctx.beginPath(); ctx.ellipse(x, y+14, 10, 3.5, ...);  // shadow — line ~3151

INSERT pulse ring draw here (after shadow, before legs at ~3154)

AFTER pulse ring:
  // Legs
  ctx.fillStyle = color+'65';  // line ~3157
```

This order ensures:
- Pulse rings appear **above the floor** (above shadow)
- Pulse rings appear **behind the character body, legs, arms, and head**
- Pulse rings appear **behind** all special-role rings (ORC dashed ring at r=17, CEO ring at r=14)

---

## 5. Activation Rules

| Condition | Sidebar CSS | Canvas |
|---|---|---|
| `status === 'busy'` | `.status-busy .ac-avatar-wrap::before/after` active | `busy = true` branch fires |
| `status === 'active'` | `.status-active .ac-avatar-wrap::before/after` active | `active = true` branch fires |
| `status === 'idle'` | no animation | no ring drawn |
| `status === 'waiting'` | no animation (waiting has its own yellow dot blink) | no ring drawn |
| `status === 'error'` | no animation (error shakes the avatar red) | no ring drawn |
| `status === 'stopped'` | no animation | no ring drawn (`stopped` guard already present) |
| `systemPaused === true` | agents remain stopped; no rings | `isStopped` guard covers this |

The `passive` modifier (used for monitoring/radar agents) should suppress the busy pulse ring on canvas (these agents have their own radar sweep at `r=18,26`) and show only the quieter `active` ring if `status === 'active'`.

---

## 6. Interaction with Existing Ring Effects

The following existing ring effects must **not clash** with the pulse ring:

| Role | Existing ring | Radius | Relation to pulse ring |
|---|---|---|---|
| CEO | Gold outer ring | r=14 | Pulse ring max ≈ 24–29; rings are temporally distinct (CEO ring is static glow) |
| Orchestrator (ORC) | Cyan dashed spinner | r=17 | Pulse ring must start at r=12 and be drawn *before* ORC ring — ORC ring sits on top |
| Reforger | Orange forge glow | r=17 | Same as ORC — draw pulse first, forge ring second |
| Passive radar | Green sweep arc | r=18,26 | Pulse suppressed for passive agents (see §5) |

No z-index adjustments are needed beyond draw order, because all of these are canvas 2D — draw order is the only stacking mechanism.

---

## 7. Performance Considerations

- **No `shadowBlur`**: All existing shadow glow was stripped for performance (`/* shadow-removed */` comments throughout). The pulse ring must **not** use `ctx.shadowBlur`. Color and opacity alone carry the visual weight.
- **`globalAlpha` reset**: Always reset `ctx.globalAlpha = 1` after drawing the ring if it was changed.
- **`ctx.beginPath()` discipline**: Call `beginPath()` before each arc to avoid path accumulation.
- **Frame budget**: The ring draw is two `ctx.arc` strokes per agent per frame — negligible cost compared to existing per-agent draw calls.
- **CSS `will-change`**: The `.ac-avatar-wrap::before/after` elements animate `transform` and `opacity` only — both are compositor-friendly. No `will-change` declaration needed (browser promotes automatically for these properties).

---

## 8. Accessibility

- `prefers-reduced-motion`: Wrap both the CSS animation and the canvas period in a motion check.

**CSS:**
```css
@media (prefers-reduced-motion: reduce) {
  .ac-avatar-wrap::before,
  .ac-avatar-wrap::after {
    animation: none;
  }
}
```

**Canvas:** Read the media query once on load:
```js
const _reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
// then inside the pulse ring block:
if (!_reduceMotion && (busy || active) && !stopped) { /* draw rings */ }
```

---

## 9. Visual Comparison: Before / After

```
BEFORE (busy agent, current):
  ┌──────────────────────────┐
  │  [head emoji]            │   ← head circle r=10, cyan stroke
  │  [body ellipse]          │   ← color+'a8' fill
  │  [keyboard glow]         │   ← on desk
  └──────────────────────────┘
  Status dot: blinking cyan, 2s

AFTER (busy agent, with pulse ring):
  ┌──────────────────────────┐
  │  ◌◌◌◌◌  (faded)          │   ← ring 2: r≈24, opacity≈0.05
  │  ◯◯◯◯   (fading)         │   ← ring 1: r≈18, opacity≈0.35
  │  [head emoji]            │   ← head circle r=10, cyan stroke
  │  [body ellipse]          │   ← color+'a8' fill
  │  [keyboard glow]         │   ← on desk
  └──────────────────────────┘
  Status dot: blinking cyan, 2s
```

---

## 10. Implementation Checklist

- [ ] Add `.ac-avatar-wrap` div wrapper in `renderAgentList()` template string (approx. line 1384)
- [ ] Add `.ac-avatar-wrap` CSS rules (position, sizing) to `<style>` block
- [ ] Add `@keyframes pulse-ring-active` to `<style>` block
- [ ] Add `@keyframes pulse-ring-busy` to `<style>` block
- [ ] Add `.status-active` / `.status-busy` animation rules on `::before` / `::after`
- [ ] Add `prefers-reduced-motion` media query override
- [ ] Insert canvas pulse ring draw block in `_drawChar()` after shadow (line ~3151), before legs (line ~3154)
- [ ] Add `_reduceMotion` guard in canvas draw block
- [ ] Verify draw order does not override ORC/Reforger/CEO rings (those draw after the pulse)
- [ ] Suppress pulse ring for `passive` agents on canvas (they use radar sweep instead)
- [ ] QA: confirm `ctx.globalAlpha` is reset to 1 after pulse ring draw
