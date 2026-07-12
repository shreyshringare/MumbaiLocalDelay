# TODOS

## Design Debt

### P3: Mobile Responsive Layout
**What:** Replace fixed-width elements with responsive equivalents.
**Why:** Some components break on viewports < 400px (map iframe, narrow dropdowns).
**Context:** Dashboard is primarily a desktop portfolio piece. Deferred from design review 2026-05-20.
**Files:** `frontend/src/components/tabs/` — MapTab.tsx iframe height, any fixed-width containers.
**Verify:** Open Render URL on mobile, check no horizontal scroll or clipped elements.

## Deployment

### DONE: Live URL in README
Render URL (`mumbailocaldelay.onrender.com`) already linked on README line 9.

### DONE: Screenshot gallery in README
All 12-tab screenshot gallery added to Dashboard section in README. Also fixed Methodology tab `[object Object]` rendering bug (`MethodologyTab.tsx` now handles `{title, content}` API shape).
