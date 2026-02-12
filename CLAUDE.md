# CLAUDE.md - JTF News

## Project Overview
JTF News (Just the Facts News) - Automated 24/7 news stream that reports only verified facts. No opinions, no adjectives, no interpretation.

## Current State
**Planning/specification phase** - No implementation code yet. SPECIFICATION.md is the primary reference (~53KB, comprehensive).

## Key Architecture Principles (from spec)
- **Simplicity = Stability** - Always choose the simplest solution; code must run forever
- **OBS Does Heavy Lifting** - Let OBS handle media/streaming; we write minimal code (~500 lines total)
- **Silence is Default** - Don't speak unless facts are verified by 2+ unrelated sources
- **No Drama** - No emotional language, no "BREAKING" labels, just calm facts

## Key Files
- `SPECIFICATION.md` - Complete technical spec (read this first for implementation)
- `PromptStart.md` - Initial prompt/context document
- `docs/implementation Ver 0.1.md` - Implementation notes
- `docs/mediasetup.md` - Media/OBS setup instructions

## Commands
- `./bu.sh "commit message"` - Git commit+push AND creates timestamped backup zip to Dropbox (excludes media/)
- `./deploy.sh` - Rsync source files to deploy machine

## IMPORTANT: Deploy Folder Location
**The deploy folder is NOT `gh-pages-dist/`!**

| Machine | Path | Purpose |
|---------|------|---------|
| Apple Silicon (dev) | `/Users/larryseyer/JTFNews` | Development |
| Intel/Mojave (deploy) | `/Volumes/larryseyer/JTFNews` | Production streaming |

- `gh-pages-dist/` is for GitHub Pages web assets only
- When copying files to production, always use `/Volumes/larryseyer/JTFNews`
- Check if volume is mounted first before copying

## Folder Structure
- `media/` - Background images organized by season (fall/, spring/, summer/, winter/, generator/)
- `docs/` - Documentation and implementation notes

## Tech Stack (planned)
- Python (~400 lines main script)
- HTML/CSS/JS overlay for OBS browser source
- Claude AI for fact extraction/rewriting
- TTS for audio generation
- OBS for streaming to YouTube
- X/Twitter for posting stories

## Constraints
- No APIs, no paywalls, respect robots.txt
- No ads, no tracking, no long-term raw data storage
- CC-BY-SA license on output
- Non-profit spirit
