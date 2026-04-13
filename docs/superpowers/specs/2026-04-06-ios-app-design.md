# JTF News iOS App — Design Spec

**Date:** 2026-04-06
**Status:** Final

---

## Context

JTF News currently distributes verified factual news through three channels: a YouTube daily digest video, an Archive.org-hosted podcast, and a GitHub Pages website serving static JSON/XML data files. There is no unified mobile experience. Users must visit the website, subscribe to the podcast separately, or find the YouTube channel independently.

An iOS app creates a single calm, unified surface for all three content streams — read today's facts, watch/listen to the daily digest, and search the full archive — while honoring JTF's core principles: no tracking, no ads, no engagement, full transparency.

---

## Architecture: Pure Static Consumer

The app consumes existing static files from `jtfnews.org` (GitHub Pages). **No backend server. No API. No changes to main.py.**

```
jtfnews.org (GitHub Pages)          iOS App
┌─────────────────────┐            ┌──────────────────────┐
│ stories.json        │ ──HTTP──▶  │ SwiftData local DB   │
│ feed.xml            │            │ (offline cache +     │
│ podcast.xml         │            │  FTS5 search index)  │
│ corrections.json    │            │                      │
│ monitor.json        │            │ AVFoundation         │
│ archive/index.json  │            │ (podcast audio)      │
│ archive/YYYY/*.gz   │            │                      │
└─────────────────────┘            │ WKWebView / YT API   │
                                   │ (YouTube embed)      │
YouTube (daily digest video) ───▶  │                      │
Archive.org (podcast audio)  ───▶  └──────────────────────┘
```

### Why This Approach

- **Simplicity = Stability** — no server to maintain, no API to version
- **Decoupled** — app can ship and update independently of main.py
- **Aligned with JTF philosophy** — the system already publishes everything needed as static files
- **Path to notifications** — can add a thin push relay (Cloudflare Worker) later without restructuring

---

## Data Sources

| Endpoint | Purpose | Refresh |
|----------|---------|---------|
| `stories.json` | Current day's verified stories | ~30 min |
| `feed.xml` | RSS with full source metadata (ratings, ownership) | ~30 min |
| `podcast.xml` | Daily digest audio links (Archive.org) | Daily |
| `corrections.json` | Corrections and retractions log | As issued |
| `monitor.json` | System health and operational status | Every cycle |
| `archive/index.json` | Index of all archived days | Daily |
| `archive/YYYY/YYYY-MM-DD.txt.gz` | Compressed daily story archives | Daily |

### Refresh Strategy

- Pull-to-refresh on Stories tab
- Automatic refresh when app foregrounds (5-minute cooldown)
- Background App Refresh for notification checks
- Archive backfill on Wi-Fi only (configurable)

---

## Navigation: Three Tabs

### Tab 1: Stories

Today's verified facts. Each story card displays:

- **The fact** — one sentence, plain text
- **Source badges** — e.g., `BBC 9.4` `CBC 9.0` (name + accuracy rating), color-coded
- **Ownership disclosure** — e.g., "UK Public (100%) · Canadian Public (100%)" — visible on every card
- **Time** — relative timestamp ("2h ago")
- **Corrections** — inline with distinct visual treatment (strikethrough original, arrow to correction, timestamp)

Pull-to-refresh. Grouped by date when scrolling into yesterday.

### Tab 2: Digest

Daily audio/video experience with two modes:

- **Video mode** — embedded YouTube player (WKWebView or YouTube iOS Player Helper) showing the daily digest
- **Audio mode** — native AVFoundation player streaming from Archive.org podcast URL

Features:
- Video/Audio toggle (preference remembered)
- Mini-player persists when switching tabs
- iOS Now Playing integration (lock screen controls via MPNowPlayingInfoCenter)
- Past digests listed chronologically below current day
- Offline: previously played audio cached locally; video requires connectivity

### Tab 3: Archive

The full searchable record:

- **Date browser** — calendar-style date picker at top
- **Full-text search** — search bar queries local FTS5 index
- **Progressive indexing** — downloads last 30 days on first launch, backfills older archives on Wi-Fi + charging
- **Index progress** — "Indexing archive... 45% complete" indicator
- **Each day** shows its stories + link to that day's digest

---

## Offline Support

- Stories cached in SwiftData on every fetch
- Podcast audio cached on-demand after playback
- Archive files decompressed and indexed locally
- Search works entirely offline against local FTS5 index
- YouTube video embed requires connectivity

---

## Notifications (Local, v1)

All notifications use **iOS Background App Refresh + local notifications**. No server infrastructure required.

| Notification | Default | Behavior |
|-------------|---------|----------|
| Daily Digest Ready | Off | Fires when background refresh detects new podcast.xml entry. User picks preferred time. |
| Corrections | Off | Fires when background refresh detects new entries in corrections.json. |
| Breaking Facts | Off | Fires when background refresh detects stories published within last hour. |

**Trade-off:** Not instant (iOS controls background refresh timing, typically 15-30 min). Acceptable for daily digest and corrections. Can upgrade to server-pushed APNs (thin Cloudflare Worker relay) in a future version.

---

## Settings

| Setting | Default | Options |
|---------|---------|---------|
| Notifications: Daily Digest | Off | Off / On (pick time) |
| Notifications: Corrections | Off | Off / On |
| Notifications: Breaking Facts | Off | Off / On |
| Preferred Digest Mode | Video | Video / Audio |
| Archive Download | Wi-Fi only | Wi-Fi only / Wi-Fi + Cellular / Manual |
| About JTF News | — | Links to whitepaper, methodology, GitHub |
| Source Details | — | All 22 sources with ratings + ownership |

---

## Aesthetic

**Calm & minimal.** The app is a quiet companion to the calm video/audio content.

- Dark mode primary (matches the YouTube digest aesthetic)
- Muted color palette — greens/blues for source badges, subtle red for corrections
- Generous whitespace
- System fonts (SF Pro) for native iOS feel
- No animations beyond standard iOS transitions
- No sounds, no haptics beyond standard feedback

---

## Privacy & Compliance

**Zero tracking. Zero analytics. Zero user data.**

- No Firebase, Amplitude, Mixpanel, or any analytics SDK
- No crash reporting service (Apple's built-in TestFlight/App Store reports only)
- No user accounts, no login, no authentication
- No device fingerprinting
- App Store Privacy Label: **"Data Not Collected"**
- Privacy policy: hosted at jtfnews.org
- Age rating: 4+ (no violent imagery — JTF never shows the event)

---

## Distribution

- **Free** on the App Store. No in-app purchases.
- Donations directed to jtfnews.org
- **Open source** on GitHub under CC-BY-SA (consistent with JTF methodology licensing)
- Apple Developer Program account required ($99/year)

---

## Channel-Aware Architecture

Ship with JTF News Global only. Structure data models so a future channel (JTF Sports, JTF Local) can be added without rewriting:

- `Channel` model with `id`, `name`, `baseURL`, `config`
- Data fetching parameterized by channel base URL
- UI displays channel name/branding from model
- Single-channel at launch, no channel-switching UI yet

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Language | Swift 6 |
| UI Framework | SwiftUI |
| Persistence | SwiftData |
| Full-text search | SQLite FTS5 (separate SQLite DB alongside SwiftData — SwiftData doesn't expose FTS natively) |
| Networking | URLSession (no third-party HTTP libs) |
| Audio playback | AVFoundation + MPNowPlayingInfoCenter |
| Video embed | WKWebView (YouTube embed) or YouTube iOS Player Helper |
| RSS parsing | Native XMLParser or FeedKit (lightweight RSS lib) |
| Decompression | Foundation's built-in gzip support |
| Minimum target | iOS 17 (SwiftData requires iOS 17+) |

---

## Development Environment

- **Xcode project location:** `/Users/larryseyer/JTFNewsApp/` on M4 MacBook Pro
- **Own git repo** — separate from the JTF News production repo on the Intel Mac
- **No local file access needed** — app fetches all data from `jtfnews.org` over HTTP
- **Apple Developer Program:** Personal account (start personal, transfer to org account later when nonprofit entity exists)
- **Distribution:** Free, no IAP, open source (CC-BY-SA)

---

## Verification Plan

1. **Stories tab** — launch app, verify stories load from jtfnews.org/stories.json, source ratings and ownership display correctly on each card
2. **Digest video** — tap Digest tab, verify YouTube embed loads and plays current daily digest
3. **Digest audio** — toggle to Audio mode, verify Archive.org podcast streams and plays with lock screen controls
4. **Mini-player** — start audio, switch to Stories tab, verify mini-player persists
5. **Offline** — load stories, enable airplane mode, relaunch app, verify cached stories display
6. **Archive browse** — tap Archive tab, pick a past date, verify stories load from compressed archive
7. **Archive search** — type a keyword, verify FTS5 returns matching stories across indexed dates
8. **Corrections** — verify correction items display inline with visual distinction in Stories tab
9. **Settings** — verify all toggles persist across app launches
10. **Background refresh** — enable daily digest notification, background the app, verify local notification fires after background refresh detects new content
11. **Privacy** — run with Charles Proxy, verify no outbound requests to analytics/tracking domains
12. **Accessibility** — verify VoiceOver reads all story content, source ratings, and navigation correctly
