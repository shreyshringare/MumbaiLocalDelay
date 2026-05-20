# TODOS

## Dashboard Design Debt

### P3: Mobile Responsive Layout
**What:** Replace fixed-width dropdowns and iframe with responsive equivalents.
**Why:** `width: 300px` dropdowns and `height: 600px` map iframe break on viewports < 400px.
**Pros:** Dashboard usable on phones, widens portfolio audience.
**Cons:** Dash inline styles require touching every tab render function. ~2h of work.
**Context:** Dashboard is primarily a desktop portfolio piece. Deferred from design review 2026-05-20.
**Files:** `dashboard/app.py` — all `_render_*` functions with inline `width:` styles.
**Verify:** Open Railway URL on mobile, check no horizontal scroll or clipped dropdowns.
