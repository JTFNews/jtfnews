# Website Redesign Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Redesign the JTF News website with a shared CSS foundation, consistent navigation, responsive layout, and an elevated visual design while preserving all existing functionality.

**Architecture:** Create a shared `style.css` with design tokens, shared nav/footer markup, and responsive components. Each page imports the shared stylesheet and adds page-specific styles as needed. Mobile-first responsive design with hamburger nav on small screens.

**Tech Stack:** HTML5, CSS3 (custom properties, flexbox, grid, media queries), vanilla JavaScript (mobile nav toggle), Inter font from Google Fonts.

---

## Important Notes

- **DO NOT touch:** screensaver.html, screensaver-setup.html, lower-third.html, background-slideshow.html, lower-third.css, lower-third.js
- **Commits:** Use `./bu.sh "message"` which pushes and deploys immediately. Verify each page works before committing.
- **No templating:** Each HTML page gets a full copy of the nav/footer markup. This is intentional (static GitHub Pages site).
- **Testing:** Visual verification only. Open each page in browser after changes. Check mobile using browser dev tools responsive mode.
- **Sync reminder:** After modifying files that exist in BOTH `web/` and `docs/` (screensaver.html, monitor.html), update both. See CLAUDE.md for path differences.
- **JavaScript:** Each page keeps its own inline `<script>` for page-specific logic. Only the mobile nav toggle is shared.

---

### Task 1: Create Shared CSS Foundation (`docs/style.css`)

**Files:**
- Create: `docs/style.css`

**Step 1: Create the shared stylesheet**

Create `docs/style.css` with the following sections:

```css
/* ============================================
   JTF News — Shared Stylesheet
   ============================================ */

/* ---------- Reset ---------- */
*, *::before, *::after { margin: 0; padding: 0; box-sizing: border-box; }

/* ---------- Design Tokens ---------- */
:root {
    --color-bg:         #0f172a;
    --color-bg-alt:     #1e293b;
    --color-surface:    rgba(15, 23, 42, 0.75);
    --color-border:     rgba(255, 255, 255, 0.1);
    --color-border-dim: rgba(255, 255, 255, 0.05);
    --color-gold:       #d4af37;
    --color-gold-dark:  #aa8723;
    --color-blue:       #60a5fa;
    --color-blue-dark:  #1e40af;
    --color-text:       #e2e8f0;
    --color-text-body:  #cbd5e1;
    --color-text-muted: #94a3b8;
    --color-text-dim:   #64748b;
    --color-text-bright:#f8fafc;
    --color-green:      #22c55e;
    --color-red:        #ef4444;
    --color-yellow:     #eab308;
    --font:             'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    --max-width:        900px;
    --radius:           12px;
    --radius-sm:        8px;
    --radius-pill:      20px;
}

/* ---------- Base ---------- */
body {
    font-family: var(--font);
    background: var(--color-bg);
    color: var(--color-text);
    line-height: 1.6;
    -webkit-font-smoothing: antialiased;
}

a { color: var(--color-blue); }
a:hover { color: #93bbfd; }

img { max-width: 100%; height: auto; }

/* ---------- Typography ---------- */
/* Use clamp() for fluid sizing between mobile and desktop */
h1 {
    color: var(--color-gold);
    font-size: clamp(1.75rem, 4vw, 2rem);
    font-weight: 700;
    line-height: 1.2;
    margin-bottom: 0.5rem;
}

h2 {
    color: var(--color-text-muted);
    font-size: clamp(1.25rem, 3vw, 1.5rem);
    font-weight: 600;
    margin-top: 2.5rem;
    margin-bottom: 1rem;
}

h3 {
    color: var(--color-text-bright);
    font-size: 1.125rem;
    font-weight: 600;
    margin-bottom: 0.75rem;
}

p { margin-bottom: 1rem; color: var(--color-text-body); }

/* ---------- Layout ---------- */
.container {
    max-width: var(--max-width);
    margin: 0 auto;
    padding: 2rem 1.25rem;
}

/* ---------- Navigation ---------- */
.site-nav {
    position: sticky;
    top: 0;
    z-index: 100;
    background: rgba(15, 23, 42, 0.95);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border-bottom: 1px solid var(--color-border);
}

.site-nav__inner {
    max-width: var(--max-width);
    margin: 0 auto;
    padding: 0.75rem 1.25rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.site-nav__logo img { height: 28px; }
.site-nav__logo { display: flex; align-items: center; text-decoration: none; }

.site-nav__links {
    display: flex;
    gap: 1.5rem;
    list-style: none;
}

.site-nav__links a {
    color: var(--color-text-muted);
    text-decoration: none;
    font-size: 0.875rem;
    font-weight: 500;
    transition: color 0.2s;
}

.site-nav__links a:hover,
.site-nav__links a[aria-current="page"] {
    color: var(--color-gold);
}

/* Hamburger (mobile) */
.site-nav__toggle {
    display: none;
    background: none;
    border: none;
    cursor: pointer;
    padding: 0.5rem;
}

.site-nav__toggle span {
    display: block;
    width: 22px;
    height: 2px;
    background: var(--color-text);
    margin: 5px 0;
    transition: transform 0.3s, opacity 0.3s;
}

/* Mobile nav overlay */
.site-nav__overlay {
    display: none;
    position: fixed;
    inset: 0;
    background: rgba(15, 23, 42, 0.98);
    z-index: 99;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 2rem;
}

.site-nav__overlay.open { display: flex; }

.site-nav__overlay a {
    color: var(--color-text);
    text-decoration: none;
    font-size: 1.25rem;
    font-weight: 500;
}

.site-nav__overlay a[aria-current="page"] { color: var(--color-gold); }

.site-nav__close {
    position: absolute;
    top: 1rem;
    right: 1.25rem;
    background: none;
    border: none;
    color: var(--color-text);
    font-size: 2rem;
    cursor: pointer;
    padding: 0.5rem;
    line-height: 1;
}

@media (max-width: 768px) {
    .site-nav__links { display: none; }
    .site-nav__toggle { display: block; }
}

/* ---------- Cards ---------- */
.card {
    background: rgba(30, 41, 59, 0.6);
    border: 1px solid var(--color-border);
    border-radius: var(--radius);
    padding: 1.25rem;
}

.card h3 {
    color: var(--color-gold);
    font-size: 1rem;
    margin-bottom: 0.625rem;
}

.card p {
    font-size: 0.875rem;
    color: var(--color-text-muted);
    margin-bottom: 0;
}

.card-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
    gap: 1.25rem;
    margin: 1.5rem 0;
}

/* ---------- Buttons ---------- */
.btn {
    display: inline-block;
    padding: 0.75rem 1.5rem;
    border-radius: var(--radius-sm);
    font-weight: 600;
    font-size: 0.875rem;
    text-decoration: none;
    transition: opacity 0.2s;
    cursor: pointer;
    border: none;
}

.btn:hover { opacity: 0.9; }

.btn--primary {
    background: linear-gradient(135deg, var(--color-gold) 0%, var(--color-gold-dark) 100%);
    color: #1a1a1a;
}

.btn--secondary {
    background: var(--color-blue-dark);
    color: white;
}

.btn--outline {
    background: transparent;
    border: 1px solid var(--color-border);
    color: var(--color-text);
}

/* ---------- Hero (homepage) ---------- */
.hero {
    text-align: center;
    padding: 4rem 1rem 3rem;
}

.hero__title {
    font-size: clamp(2.25rem, 6vw, 3rem);
    color: var(--color-gold);
    margin-bottom: 0.75rem;
    letter-spacing: -0.5px;
}

.hero__subtitle {
    font-size: clamp(1rem, 2.5vw, 1.25rem);
    color: var(--color-text);
    margin-bottom: 0.5rem;
    font-weight: 400;
}

.hero__desc {
    font-size: 1rem;
    color: var(--color-text-muted);
    margin-bottom: 2rem;
}

.hero__actions {
    display: flex;
    gap: 1rem;
    justify-content: center;
    flex-wrap: wrap;
}

/* ---------- Live Story Preview ---------- */
.live-preview {
    max-width: 700px;
    margin: 0 auto 3rem;
    position: relative;
}

.live-preview__badge {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: var(--color-green);
    margin-bottom: 0.75rem;
}

.live-preview__badge::before {
    content: '';
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--color-green);
    animation: pulse 2s ease-in-out infinite;
}

@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.4; }
}

.live-preview__card {
    background: var(--color-surface);
    backdrop-filter: blur(40px) saturate(180%);
    -webkit-backdrop-filter: blur(40px) saturate(180%);
    border: 1px solid rgba(255, 255, 255, 0.15);
    border-radius: 1rem;
    box-shadow: 0 12px 40px rgba(0, 0, 0, 0.4);
    overflow: hidden;
}

.live-preview__sources {
    background: linear-gradient(135deg, rgba(30, 64, 175, 0.7), rgba(23, 37, 84, 0.8));
    padding: 0.875rem 1.5rem;
    font-size: 0.875rem;
    font-weight: 600;
    color: white;
    text-transform: uppercase;
    letter-spacing: 2px;
}

.live-preview__fact {
    padding: 1.5rem 2rem;
    font-size: clamp(1.125rem, 2.5vw, 1.375rem);
    color: white;
    line-height: 1.5;
}

/* ---------- Section Dividers ---------- */
.section {
    margin-top: 3rem;
}

.section__title {
    color: var(--color-text-muted);
    font-size: clamp(1.25rem, 3vw, 1.5rem);
    font-weight: 600;
    margin-bottom: 1rem;
}

/* ---------- Costs Widget ---------- */
.costs-section {
    background: rgba(30, 41, 59, 0.8);
    border: 1px solid var(--color-border);
    border-radius: var(--radius);
    padding: 1.25rem;
    margin: 1.5rem 0;
}

.costs-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1rem;
}

.costs-header h3 {
    margin: 0;
    color: var(--color-gold);
    font-size: 1rem;
}

.live-badge {
    font-size: 0.6875rem;
    padding: 0.1875rem 0.5rem;
    background: rgba(34, 197, 94, 0.2);
    color: var(--color-green);
    border-radius: var(--radius-pill);
    text-transform: uppercase;
    font-weight: 600;
}

.costs-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 1rem;
}

@media (max-width: 480px) {
    .costs-grid { grid-template-columns: 1fr; }
}

.cost-item {
    background: rgba(15, 23, 42, 0.6);
    padding: 0.75rem;
    border-radius: var(--radius-sm);
}

.cost-label {
    font-size: 0.75rem;
    color: var(--color-text-dim);
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

.cost-value {
    font-size: 1.5rem;
    font-weight: 600;
    color: var(--color-text-bright);
    margin-top: 0.25rem;
}

.cost-value.highlight { color: var(--color-gold); }

.cost-detail {
    font-size: 0.6875rem;
    color: var(--color-text-dim);
    margin-top: 0.25rem;
}

.budget-bar {
    height: 4px;
    background: rgba(255, 255, 255, 0.1);
    border-radius: 2px;
    margin-top: 0.5rem;
    overflow: hidden;
}

.budget-fill {
    height: 100%;
    border-radius: 2px;
    transition: width 0.3s, background 0.3s;
}

.budget-fill.green { background: var(--color-green); }
.budget-fill.yellow { background: var(--color-yellow); }
.budget-fill.red { background: var(--color-red); }

.costs-breakdown {
    margin-top: 1rem;
    padding-top: 1rem;
    border-top: 1px solid var(--color-border);
}

.breakdown-row {
    display: flex;
    justify-content: space-between;
    padding: 0.375rem 0;
    font-size: 0.8125rem;
}

.breakdown-service { color: var(--color-text-muted); }
.breakdown-cost { color: var(--color-green); }

.status-row {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-top: 0.625rem;
    font-size: 0.8125rem;
}

.status-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--color-green);
}

.status-dot.offline { background: var(--color-red); }
.status-text { color: var(--color-text-muted); }

.transparency-note {
    font-size: 0.75rem;
    color: var(--color-text-dim);
    margin-top: 1rem;
    font-style: italic;
}

.dashboard-link {
    display: block;
    text-align: center;
    margin-top: 1rem;
    font-size: 0.8125rem;
}

/* ---------- Philosophy Block ---------- */
.philosophy {
    background: rgba(212, 175, 55, 0.1);
    border-left: 4px solid var(--color-gold);
    padding: 1.25rem;
    border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
    margin: 1.25rem 0;
}

.philosophy p {
    color: var(--color-text);
    font-size: 0.9375rem;
    margin-bottom: 0.625rem;
}

.philosophy p:last-child { margin-bottom: 0; }

/* ---------- Rule Lists ---------- */
.rule-list {
    margin: 1rem 0;
    padding-left: 1.25rem;
}

.rule-list li {
    color: var(--color-text-muted);
    margin-bottom: 0.5rem;
    font-size: 0.875rem;
}

.rule-list li strong { color: var(--color-text); }

/* ---------- CTA Section ---------- */
.cta-section {
    text-align: center;
    margin-top: 3rem;
    padding-top: 2rem;
    border-top: 1px solid var(--color-border);
}

/* ---------- Footer ---------- */
.site-footer {
    border-top: 1px solid var(--color-border);
    margin-top: 4rem;
    padding: 2rem 1.25rem;
    text-align: center;
}

.site-footer__inner {
    max-width: var(--max-width);
    margin: 0 auto;
}

.site-footer__links {
    display: flex;
    justify-content: center;
    flex-wrap: wrap;
    gap: 1.25rem;
    list-style: none;
    margin-bottom: 1.5rem;
}

.site-footer__links a {
    color: var(--color-text-muted);
    text-decoration: none;
    font-size: 0.8125rem;
}

.site-footer__links a:hover { color: var(--color-text); }

.site-footer__tagline {
    font-size: 0.8125rem;
    color: var(--color-text-dim);
    font-style: italic;
    margin-bottom: 0.5rem;
}

.site-footer__copy {
    font-size: 0.75rem;
    color: var(--color-text-dim);
}

/* ---------- Utility ---------- */
.text-center { text-align: center; }
.text-muted { color: var(--color-text-muted); }
.text-dim { color: var(--color-text-dim); }
.text-small { font-size: 0.875rem; }
.text-xs { font-size: 0.8125rem; }
.mt-1 { margin-top: 0.5rem; }
.mt-2 { margin-top: 1rem; }
.mt-3 { margin-top: 1.5rem; }
.mb-0 { margin-bottom: 0; }
.mb-1 { margin-bottom: 0.5rem; }
```

**Step 2: Verify the CSS file loads correctly**

Create a temporary test: open any existing page in browser, add `<link rel="stylesheet" href="style.css">` to the `<head>` via dev tools, confirm it loads without errors.

**Step 3: Commit**

```bash
./bu.sh "feat: add shared stylesheet (style.css) for website redesign"
```

---

### Task 2: Redesign Homepage (`docs/index.html`)

**Files:**
- Modify: `docs/index.html` (complete rewrite)

This is the biggest single change. The new homepage has:
1. Shared nav bar
2. Hero section with tagline + CTAs
3. Live story preview card
4. "How it works" summary cards (4 cards)
5. Operational costs widget (existing functionality, new wrapper)
6. Subscribe/Watch/Support cards
7. Shared footer

**Step 1: Rewrite index.html**

Replace the entire file with the new structure. Key requirements:
- Import `style.css` (remove all inline `<style>` except page-specific overrides)
- Import Inter font from Google Fonts
- Keep ALL existing `<head>` meta tags (SEO, OpenGraph, Twitter Cards, favicons)
- Keep the existing JavaScript for loading costs from `monitor.json` and cycle-sync refresh
- Add mobile nav toggle JavaScript

**Nav HTML structure** (this exact markup goes in ALL pages, with the correct `aria-current="page"` on the active link):

```html
<nav class="site-nav" role="navigation" aria-label="Main navigation">
    <div class="site-nav__inner">
        <a href="index.html" class="site-nav__logo">
            <img src="assets/logo-horizontal-dark.svg" alt="JTF News">
        </a>
        <ul class="site-nav__links">
            <li><a href="index.html" aria-current="page">Home</a></li>
            <li><a href="how-it-works.html">How It Works</a></li>
            <li><a href="sources.html">Sources</a></li>
            <li><a href="whitepaper.html">Whitepaper</a></li>
            <li><a href="archive.html">Archive</a></li>
            <li><a href="corrections.html">Corrections</a></li>
        </ul>
        <button class="site-nav__toggle" aria-label="Open menu" onclick="document.getElementById('nav-overlay').classList.add('open')">
            <span></span><span></span><span></span>
        </button>
    </div>
</nav>
<div id="nav-overlay" class="site-nav__overlay">
    <button class="site-nav__close" aria-label="Close menu" onclick="this.parentElement.classList.remove('open')">&times;</button>
    <a href="index.html">Home</a>
    <a href="how-it-works.html">How It Works</a>
    <a href="sources.html">Sources</a>
    <a href="whitepaper.html">Whitepaper</a>
    <a href="archive.html">Archive</a>
    <a href="corrections.html">Corrections</a>
</div>
```

**Footer HTML structure** (same in all pages):

```html
<footer class="site-footer">
    <div class="site-footer__inner">
        <ul class="site-footer__links">
            <li><a href="index.html">Home</a></li>
            <li><a href="how-it-works.html">How It Works</a></li>
            <li><a href="sources.html">Sources</a></li>
            <li><a href="whitepaper.html">Whitepaper</a></li>
            <li><a href="archive.html">Archive</a></li>
            <li><a href="corrections.html">Corrections</a></li>
            <li><a href="monitor.html">Dashboard</a></li>
            <li><a href="feed.xml">RSS</a></li>
        </ul>
        <p class="site-footer__tagline">The methodology belongs to no one. It serves everyone.</p>
        <p class="site-footer__copy">
            <a href="https://github.com/JTFNews/jtfnews">GitHub</a> &middot;
            <a href="https://github.com/sponsors/larryseyer">Support</a>
        </p>
    </div>
</footer>
```

**Homepage body structure:**

```html
<!-- Nav -->
<!-- Hero -->
<section class="hero">
    <div class="container">
        <h1 class="hero__title">Just The Facts.</h1>
        <p class="hero__subtitle">No opinions. No adjectives. No interpretation.</p>
        <p class="hero__desc">24/7 verified news from 17 independent sources.</p>
        <div class="hero__actions">
            <a href="https://www.youtube.com/@JTFNewsLive" class="btn btn--secondary">Watch Live</a>
            <a href="how-it-works.html" class="btn btn--outline">How It Works</a>
        </div>
    </div>
</section>

<!-- Live Story Preview -->
<section class="container">
    <div class="live-preview">
        <div class="live-preview__badge" id="demo-label">Live Story</div>
        <div class="live-preview__card">
            <div class="live-preview__sources" id="demo-sources">Loading...</div>
            <div class="live-preview__fact" id="demo-fact">Loading latest verified fact...</div>
        </div>
    </div>
</section>

<!-- How It Works Summary -->
<section class="container section">
    <h2 class="section__title">How It Works</h2>
    <div class="card-grid">
        <div class="card">
            <h3>1. Collect</h3>
            <p>Headlines gathered from 17+ sources worldwide, including public broadcasters and government records.</p>
        </div>
        <div class="card">
            <h3>2. Extract</h3>
            <p>AI extracts only verifiable facts. Opinions, adjectives, and speculation are removed.</p>
        </div>
        <div class="card">
            <h3>3. Verify</h3>
            <p>Facts require 2+ independent sources with different owners before broadcast.</p>
        </div>
        <div class="card">
            <h3>4. Broadcast</h3>
            <p>Verified facts are spoken aloud and displayed with full source attribution.</p>
        </div>
    </div>
    <p class="text-center"><a href="how-it-works.html">Learn more about our process &rarr;</a></p>
</section>

<!-- Operational Costs (keep existing widget markup + JS, wrap in new classes) -->
<section class="container section">
    <h2 class="section__title">Operational Costs</h2>
    <!-- Existing costs-section markup here, using shared CSS classes -->
</section>

<!-- Subscribe / Watch / Support -->
<section class="container section">
    <h2 class="section__title">Get Involved</h2>
    <div class="card-grid" style="grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));">
        <div class="card text-center">
            <h3>RSS Feed</h3>
            <p>Subscribe to verified facts.</p>
            <a href="feed.xml" class="btn btn--secondary mt-2" style="display:inline-block;">Subscribe</a>
        </div>
        <div class="card text-center">
            <h3>Watch Live</h3>
            <p>24/7 on YouTube.</p>
            <a href="https://www.youtube.com/@JTFNewsLive" class="btn btn--secondary mt-2" style="display:inline-block;">YouTube</a>
        </div>
        <div class="card text-center">
            <h3>Support</h3>
            <p>No ads. No tracking. Viewer-supported.</p>
            <a href="https://github.com/sponsors/larryseyer" class="btn btn--primary mt-2" style="display:inline-block;">Sponsor</a>
        </div>
    </div>
</section>

<!-- Footer -->
```

**JavaScript:** Keep the existing `loadCosts()` and `checkForCycleRefresh()` functions. Add a new function to load the live story preview (similar to how-it-works.html's `loadLiveStory()`):

```javascript
async function loadLivePreview() {
    try {
        const response = await fetch('./stories.json?t=' + Date.now());
        if (!response.ok) throw new Error('No stories');
        const data = await response.json();
        if (!data.stories || data.stories.length === 0) throw new Error('Empty');

        const story = data.stories[0];
        document.getElementById('demo-sources').textContent = story.source || 'JTF News';
        document.getElementById('demo-fact').textContent = story.fact;
        document.getElementById('demo-label').innerHTML =
            'Live Story <span style="background:rgba(34,197,94,0.2);color:#22c55e;padding:2px 8px;border-radius:10px;font-size:9px;margin-left:8px;">LIVE</span>';
    } catch (e) {
        document.getElementById('demo-sources').textContent = 'Reuters 9.8|9.5 · AP 9.6|9.4';
        document.getElementById('demo-fact').textContent =
            'The European Central Bank held interest rates at 2.75% at its February 2025 meeting.';
        document.getElementById('demo-label').textContent = 'Example';
    }
}

loadLivePreview();
```

**Step 2: Verify in browser**

- Open `docs/index.html` in browser
- Check: nav bar appears with correct links, "Home" highlighted in gold
- Check: hero section is centered, text is readable, CTAs work
- Check: live story preview loads (or shows fallback)
- Check: cards display in 2x2 grid on desktop, stack on mobile
- Check: costs widget loads live data
- Check: footer appears at bottom with all links
- Check mobile: use dev tools to test at 375px width. Hamburger menu should appear, cards should stack, text should be readable.

**Step 3: Commit**

```bash
./bu.sh "feat: redesign homepage with hero, live preview, shared nav/footer"
```

---

### Task 3: Update How It Works (`docs/how-it-works.html`)

**Files:**
- Modify: `docs/how-it-works.html`

**Step 1: Update the page**

This page is already the most polished. Changes are:
- Replace the inline `<style>` block. Import `style.css` instead. Keep ONLY page-specific styles (demo section, tooltips, hover zones) in a small inline `<style>` block.
- Replace the existing nav bar (lines 462-474) with the shared nav markup (same as Task 2, but with `aria-current="page"` on "How It Works" link)
- Add the shared footer before `</body>`
- Keep ALL existing JavaScript unchanged
- Keep ALL interactive demo functionality unchanged

Styles that should remain page-specific (in a small inline `<style>`):
- `.demo-section` and its children (the interactive demo)
- `.hover-zone`, `.tooltip`, `.tooltip-right`, `.tooltip-left`, `.tooltip-bottom` (hover interactions)
- `.mobile-explanations` (mobile fallback for tooltips)
- `.bg-grid`, `.bg-sample` (background image grid)
- `.rating-example`, `.rating-badge`, `.rating-desc` (source score examples)

Styles that move to shared `style.css` (already there):
- `.card`, `.card-grid`, `.card h3`, `.card p`
- `.philosophy`, `.rule-list`
- `.cta-section`, `.btn`, `.btn--primary`, `.btn--secondary`
- Body, typography, links, colors

**Step 2: Verify in browser**

- Check: shared nav appears, "How It Works" highlighted
- Check: interactive demo still works (hover tooltips, live story loads)
- Check: card grids display correctly
- Check: footer appears
- Check mobile: hamburger nav, tooltips hidden (mobile explanations shown instead)

**Step 3: Commit**

```bash
./bu.sh "refactor: update how-it-works page to use shared stylesheet"
```

---

### Task 4: Update Whitepaper (`docs/whitepaper.html`)

**Files:**
- Modify: `docs/whitepaper.html`

**Step 1: Update the page**

- Replace inline `<style>`. Import `style.css`. Keep only whitepaper-specific styles (markdown rendering overrides for `#content h1`, `#content h2`, etc.) in a small inline `<style>`.
- Replace the back-link with shared nav (set `aria-current="page"` on "Whitepaper")
- Add shared footer before `</body>`
- Keep ALL JavaScript (markdown loading from GitHub) unchanged
- Keep the loading spinner and error state styles

**Step 2: Verify in browser**

- Check: nav appears, "Whitepaper" highlighted
- Check: whitepaper content loads from GitHub and renders correctly
- Check: typography matches design system
- Check: footer appears
- Check mobile responsive

**Step 3: Commit**

```bash
./bu.sh "refactor: update whitepaper page to use shared stylesheet"
```

---

### Task 5: Update Sources (`docs/sources.html`)

**Files:**
- Modify: `docs/sources.html`

**Step 1: Update the page**

- Replace inline `<style>`. Import `style.css`. Keep only source-specific styles (`.criteria-box`, `.category`, `.source-grid`, `.source-item`, `.transparency-note`) in a small inline `<style>`.
- Replace logo + h1 header with shared nav (set `aria-current="page"` on "Sources")
- Replace bottom `.nav-links` with shared footer
- Keep all content unchanged

**Step 2: Verify in browser**

- Check: nav appears, "Sources" highlighted
- Check: source categories display correctly
- Check: source cards responsive (grid adapts on mobile)
- Check: footer appears
- Check mobile responsive

**Step 3: Commit**

```bash
./bu.sh "refactor: update sources page to use shared stylesheet"
```

---

### Task 6: Update Archive (`docs/archive.html`)

**Files:**
- Modify: `docs/archive.html`

**Step 1: Update the page**

- Replace inline `<style>`. Import `style.css`. Keep only archive-specific styles (`.filters`, `.filter-input`, `.quick-dates`, `.story-card`, `.empty-state`, `.loading`, etc.) in a small inline `<style>`.
- Replace back-link + logo + h1 with shared nav (set `aria-current="page"` on "Archive")
- Replace bottom `.nav-links` with shared footer
- Keep ALL JavaScript unchanged (archive loading, gzip decompression, filtering, cycle-sync)

**Step 2: Verify in browser**

- Check: nav appears, "Archive" highlighted
- Check: date picker works, quick dates work
- Check: stories load and display correctly
- Check: source filter works
- Check: footer appears
- Check mobile responsive (filters stack, story cards full-width)

**Step 3: Commit**

```bash
./bu.sh "refactor: update archive page to use shared stylesheet"
```

---

### Task 7: Update Corrections (`docs/corrections.html`)

**Files:**
- Modify: `docs/corrections.html`

**Step 1: Update the page**

- Replace inline `<style>`. Import `style.css`. Keep only corrections-specific styles (`.correction-card`, `.philosophy-quote`, `.stats-summary`, `.stat-box`, status badges) in a small inline `<style>`.
- Replace back-link + logo + h1 with shared nav (set `aria-current="page"` on "Corrections")
- Replace bottom `.nav-links` with shared footer
- Keep ALL JavaScript unchanged

**Step 2: Verify in browser**

- Check: nav appears, "Corrections" highlighted
- Check: corrections load (or empty state appears)
- Check: stats summary displays
- Check: footer appears
- Check mobile responsive

**Step 3: Commit**

```bash
./bu.sh "refactor: update corrections page to use shared stylesheet"
```

---

### Task 8: Update Monitor Dashboard (`docs/monitor.html`)

**Files:**
- Modify: `docs/monitor.html`

**Step 1: Update the page**

The monitor page is special - it already has its own external CSS (`monitor.css`) with a different max-width (1400px) and grid layout. We want to ADD the shared nav/footer while keeping monitor.css for the dashboard-specific styles.

Changes:
- Add `<link rel="stylesheet" href="style.css">` BEFORE `<link rel="stylesheet" href="monitor.css">` (so monitor.css can override shared styles)
- Add shared nav before the `<div class="dashboard">` (no `aria-current` on any nav link since Dashboard is not in the main nav)
- Add shared footer after `</main>` / before `</div><!-- .dashboard -->`
- The dashboard-specific header (with "Operations Dashboard" subtitle and connection status) stays as-is inside the grid area
- Keep ALL JavaScript via `monitor.js` unchanged

**Important:** The monitor.css already defines its own `*`, `body`, and `.card` styles. Adding `style.css` first means monitor.css will properly override these for the dashboard page. Verify there are no visual conflicts.

**Step 2: Verify in browser**

- Check: shared nav appears at top
- Check: dashboard grid still displays correctly (3 columns, responsive to 2 then 1)
- Check: all dashboard cards load live data
- Check: no visual conflicts between style.css and monitor.css
- Check: footer appears below dashboard
- Check mobile responsive

**Step 3: Commit**

```bash
./bu.sh "refactor: add shared nav/footer to monitor dashboard"
```

**Step 4: Sync to web/ if needed**

Check CLAUDE.md: monitor.html exists in both `web/` and `docs/`. If the web/ version also needs the nav, update it. However, the web/ version is for OBS browser source and probably should NOT have the nav. Verify with the user if unsure. Path differences apply (see CLAUDE.md).

---

### Task 9: Final Cross-Page Verification

**Files:** None (verification only)

**Step 1: Visual verification across all pages**

Open each page in browser and verify:

| Page | Nav | Footer | Responsive | Functionality |
|------|-----|--------|------------|--------------|
| index.html | Home highlighted | Yes | Tested at 375px, 768px, 1024px | Costs load, live story loads |
| how-it-works.html | HIW highlighted | Yes | Cards stack, tooltips work | Interactive demo works |
| whitepaper.html | WP highlighted | Yes | Text reflows | Markdown loads from GitHub |
| sources.html | Sources highlighted | Yes | Source cards reflow | All sources display |
| archive.html | Archive highlighted | Yes | Filters stack | Stories load, filter works |
| corrections.html | Corrections highlighted | Yes | Cards reflow | Corrections load |
| monitor.html | No highlight | Yes | Dashboard grid stacks | Live data loads |

**Step 2: Cross-page navigation**

Click through every nav link on every page. Confirm all links work and the correct page is highlighted.

**Step 3: Mobile hamburger menu**

On each page, resize to mobile width. Verify:
- Hamburger icon appears
- Tapping opens full-screen overlay
- Links work
- Close button works

**Step 4: Check untouched pages still work**

Verify these pages are completely unchanged:
- screensaver.html
- screensaver-setup.html
- lower-third.html
- background-slideshow.html

**Step 5: Final commit (if any fixes needed)**

```bash
./bu.sh "fix: polish cross-page consistency after redesign"
```
