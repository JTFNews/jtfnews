# JTF News Website Redesign - Design Document

**Date:** 2026-02-27
**Approach:** Elevated Minimal
**Scope:** Full site redesign (excluding OBS/screensaver pages)

---

## Goals

- Build credibility (journalists, academics, skeptics take it seriously)
- Attract general public (approachable for people tired of biased news)
- Responsive design (mobile-first, works on all devices)
- Visual consistency across all pages

## Visual Direction

Evolve the existing dark navy + gold palette. More whitespace, better typography, subtle animations. Calm is the brand. Where CNN screams, JTF breathes.

## Pages In Scope

- index.html (homepage - major redesign)
- how-it-works.html (adopt shared system, keep interactive demo)
- whitepaper.html (adopt shared nav/footer, keep markdown rendering)
- sources.html (adopt shared system, polish cards)
- archive.html (adopt shared system, same functionality)
- corrections.html (adopt shared system, same functionality)
- monitor.html (adopt shared system, same functionality)

## Pages NOT Touched

- screensaver.html
- screensaver-setup.html
- lower-third.html
- background-slideshow.html

---

## Architecture

### Shared CSS: `docs/style.css`

All pages import one stylesheet. No more inline `<style>` blocks (except page-specific overrides if truly needed).

### Design Tokens (CSS Custom Properties)

```css
:root {
    --color-bg:         #0f172a;
    --color-surface:    #1e293b;
    --color-border:     rgba(255, 255, 255, 0.1);
    --color-gold:       #d4af37;
    --color-blue:       #60a5fa;
    --color-text:       #e2e8f0;
    --color-text-muted: #94a3b8;
    --color-text-dim:   #64748b;
    --color-green:      #22c55e;
    --color-red:        #ef4444;
    --color-yellow:     #eab308;
    --font:             'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    --max-width:        900px;
    --radius:           12px;
    --radius-sm:        8px;
}
```

### Typography Scale

| Element | Desktop | Mobile |
|---------|---------|--------|
| Hero heading | 48px | 36px |
| Page heading (h1) | 32px | 28px |
| Section heading (h2) | 24px | 20px |
| Body text | 16px | 16px |
| Small/labels | 13px | 13px |

### Responsive Breakpoints (Mobile-First)

- Base: mobile (< 640px) - single column
- `sm` (640px): minor adjustments
- `md` (768px): two-column grids, side-by-side layouts
- `lg` (1024px): full desktop layout, max-width container

---

## Shared Components

### Navigation Bar

Sticky top bar on every page:
- Logo (left) + nav links (right)
- Active page highlighted in gold
- Mobile (< 768px): hamburger menu, full-screen overlay with stacked links
- Simple CSS + minimal JS

Links: Home, How It Works, Sources, Whitepaper, Archive, Corrections

### Footer

Minimal footer on every page:
- Links to all pages
- "Methodology belongs to no one" tagline
- GitHub link
- Sponsor link

### Cards

Consistent card component:
- Background: var(--color-surface)
- Border: 1px solid var(--color-border)
- Border-radius: var(--radius)
- Padding: 20-25px

### Buttons

Primary: gold gradient (existing)
Secondary: blue (#1e40af)
Both: 12px 24px padding, 8px radius, 600 weight

---

## Homepage (index.html) - Major Redesign

### Structure (top to bottom):

1. **Nav bar** (shared)

2. **Hero section** - generous padding, centered
   - "Just The Facts." - large gold heading (48px)
   - "No opinions. No adjectives. No interpretation." - subtitle
   - "24/7 verified news from 17 independent sources." - one-liner
   - Two CTAs: [Watch Live] [How It Works]
   - Mobile: CTAs stack vertically

3. **Live Story Preview** - embedded card
   - Reuses lower-third visual style from how-it-works.html
   - Shows: source names + scores, time ago, fact text
   - "LIVE" badge
   - Show, don't tell - visitors see what JTF produces

4. **"How It Works" summary** - 4 cards in 2x2 grid
   - Collect, Extract, Verify, Broadcast (condensed)
   - Link to full how-it-works.html
   - Mobile: stacks to single column

5. **Operational Costs** - redesigned cost widget
   - Same live data from monitor.json
   - Cleaner card layout matching design system
   - Budget bar, service breakdown

6. **Subscribe / Watch / Support** - 3 cards side by side
   - RSS Feed, YouTube Live, GitHub Sponsors
   - Mobile: stacked vertically

7. **Footer** (shared)

### Removed from homepage:
- Screensaver section (available via nav/footer)
- Raw GitHub sponsors iframe (replaced with styled card)

---

## Inner Pages

### Principle: Consistency Over Reinvention

Inner pages are mostly about wrapping existing functionality in the shared design system.

### how-it-works.html
- Move from inline CSS to shared stylesheet
- Update nav bar to shared version
- Keep: interactive demo, card grids, tooltips (all work well)
- Minor typography/spacing to match system

### whitepaper.html
- Replace back-link with shared nav
- Keep markdown-rendering from GitHub (smart, single source of truth)
- Typography styles move to shared CSS
- Add shared footer

### sources.html
- Adopt shared nav + footer
- Source cards get visual polish matching card system
- Same content and structure

### archive.html
- Adopt shared nav + footer
- Filters and story cards match design system
- Same functionality

### corrections.html
- Adopt shared nav + footer
- Correction cards match design system
- Same functionality

### monitor.html
- Adopt shared nav + footer
- Dashboard cards match design system
- Same functionality

---

## Responsive Behavior

### Mobile Navigation (< 768px)
- Hamburger icon on right side of nav bar
- Full-screen overlay with stacked nav links
- Gold highlight on active page
- CSS + minimal JS (no framework)

### Homepage
- Hero: heading 48px -> 36px, CTAs stack
- Live story: full-width card
- How-it-works: 2x2 -> single column
- Costs: 2-column -> single column
- Subscribe: 3 cards -> stacked

### Inner Pages
- Source cards: 3-4 columns -> 2 -> 1
- Archive cards: full-width at all sizes
- Monitor dashboard: grid stacks on mobile

### Details
- Touch targets: minimum 44px
- No horizontal scroll at any viewport
- Images: max-width 100%
- Fluid font scaling with clamp() where appropriate
