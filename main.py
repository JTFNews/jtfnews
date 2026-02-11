#!/usr/bin/env python3
"""
JTF News - Just The Facts
=========================
Automated news stream that reports only verified facts.
No opinions. No adjectives. No interpretation.

This script runs continuously:
- Scrapes headlines from 20 news sources
- Uses Claude AI to extract pure facts
- Requires 2+ unrelated sources for verification
- Generates TTS audio via ElevenLabs
- Writes output files for OBS to display
- Archives daily to GitHub at midnight GMT
"""

import os
import sys
import json
import time
import gzip
import shutil
import hashlib
import logging
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import anthropic
from elevenlabs import ElevenLabs
from twilio.rest import Client as TwilioClient

# =============================================================================
# CONFIGURATION
# =============================================================================

# Load environment variables
load_dotenv()

# Paths
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
AUDIO_DIR = BASE_DIR / "audio"
ARCHIVE_DIR = BASE_DIR / "archive"
CONFIG_FILE = BASE_DIR / "config.json"

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)
AUDIO_DIR.mkdir(exist_ok=True)
ARCHIVE_DIR.mkdir(exist_ok=True)

# Load config
with open(CONFIG_FILE) as f:
    CONFIG = json.load(f)

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
log = logging.getLogger("jtf")

# Kill switch file
KILL_SWITCH = Path("/tmp/jtf-stop")

# =============================================================================
# CLAUDE AI - FACT EXTRACTION
# =============================================================================

FACT_EXTRACTION_PROMPT = """You are a fact extraction system for JTF News. Your ONLY job is to strip ALL editorialization, bias, and opinion from news headlines and return pure facts.

RULES:
1. Extract ONLY verifiable facts: what, where, when, how many
2. Remove ALL loaded language:
   - "brutal" → remove
   - "tragic" → remove
   - "shocking" → remove
   - "controversial" → remove
   - "failed" → remove unless objectively measurable
   - "active shooter" → "shooting reported"
   - "terrified" → remove
   - "slammed" → "criticized"
   - "historic" → remove unless objectively true
3. Remove ALL speculation and attribution of motive
4. Remove ALL adjectives that convey judgment
5. Keep numbers, locations, names, and actions
6. Use present tense for ongoing events
7. Maximum ONE sentence
8. If the headline contains NO verifiable facts, return "SKIP" for fact

NEWSWORTHINESS THRESHOLD:
A story is only newsworthy if it meets AT LEAST ONE of these criteria:
- Involves death or violent crime (shootings, murders, attacks, etc.)
- Affects 500 or more people directly
- Costs or invests at least $1 million USD (or equivalent)
- Changes a law or regulation
- Redraws a political border
- Major scientific or technological achievement (space launch, medical breakthrough, new discovery)
- Humanitarian milestone (aid delivered, rescue success, disaster relief)
If the story does NOT meet any threshold, set newsworthy to false.

OUTPUT FORMAT:
Return a JSON object with:
- "fact": The clean, factual sentence (or "SKIP" if no verifiable facts)
- "confidence": Your confidence percentage (0-100) that this is purely factual
- "newsworthy": true or false based on the threshold criteria above
- "threshold_met": Which threshold it meets (e.g., "death/violence", "500+ affected", "$1M+ cost/investment", "law change", "border change", "scientific achievement", "humanitarian milestone") or "none"

Headline to process:
"""


def extract_fact(headline: str) -> dict:
    """Send headline to Claude for fact extraction."""
    import re

    try:
        client = anthropic.Anthropic()

        response = client.messages.create(
            model=CONFIG["claude"]["model"],
            max_tokens=CONFIG["claude"]["max_tokens"],
            messages=[{
                "role": "user",
                "content": FACT_EXTRACTION_PROMPT + headline
            }]
        )

        text = response.content[0].text

        # Try standard JSON parsing first
        try:
            start = text.find('{')
            end = text.rfind('}') + 1
            if start >= 0 and end > start:
                return json.loads(text[start:end])
        except json.JSONDecodeError:
            pass

        # Fallback: Extract fields using regex (handles malformed JSON)
        fact_match = re.search(r'"fact"\s*:\s*"([^"]*(?:\\.[^"]*)*)"', text)
        conf_match = re.search(r'"confidence"\s*:\s*(\d+)', text)

        if fact_match:
            fact = fact_match.group(1).replace('\\"', '"')
            confidence = int(conf_match.group(1)) if conf_match else 85
            return {"fact": fact, "confidence": confidence, "removed": []}

        return {"fact": "SKIP", "confidence": 0, "removed": []}

    except Exception as e:
        log.error(f"Claude API error: {e}")
        return {"fact": "SKIP", "confidence": 0, "removed": [], "error": str(e)}


# =============================================================================
# WEB SCRAPING
# =============================================================================

def fetch_rss_headlines(source: dict) -> list:
    """Fetch headlines from an RSS feed."""
    headlines = []
    rss_url = source.get("rss")

    if not rss_url:
        return []

    try:
        headers = {
            "User-Agent": "JTFNews/1.0 (Facts only, no opinions; RSS reader)"
        }

        response = requests.get(rss_url, headers=headers, timeout=15)
        response.raise_for_status()

        # Parse RSS XML
        root = ET.fromstring(response.content)

        # RSS feeds have items under channel, Atom feeds have entry elements
        items = root.findall('.//item') or root.findall('.//{http://www.w3.org/2005/Atom}entry')

        for item in items[:10]:  # Limit to first 10 headlines
            # Try RSS format first, then Atom format
            title = item.find('title')
            if title is None:
                title = item.find('{http://www.w3.org/2005/Atom}title')

            if title is not None and title.text:
                text = title.text.strip()
                if len(text) > 20:  # Skip very short items
                    headlines.append({
                        "text": text,
                        "source_id": source["id"],
                        "source_name": source["name"],
                        "source_rating": source["ratings"]["accuracy"],
                        "owner": source["owner"],
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })

        if headlines:
            log.info(f"Fetched {len(headlines)} headlines from {source['name']} (RSS)")

    except Exception as e:
        log.debug(f"RSS failed for {source['name']}: {e}")

    return headlines


def fetch_html_headlines(source: dict) -> list:
    """Fetch headlines by scraping HTML."""
    headlines = []

    try:
        headers = {
            "User-Agent": "JTFNews/1.0 (Facts only, no opinions; respects robots.txt)"
        }

        response = requests.get(source["url"], headers=headers, timeout=15)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        # Find headlines using configured selector
        elements = soup.select(source["scrape_selector"])

        for el in elements[:10]:  # Limit to first 10 headlines
            text = el.get_text(strip=True)
            if text and len(text) > 20:  # Skip very short items
                headlines.append({
                    "text": text,
                    "source_id": source["id"],
                    "source_name": source["name"],
                    "source_rating": source["ratings"]["accuracy"],
                    "owner": source["owner"],
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })

        if headlines:
            log.info(f"Fetched {len(headlines)} headlines from {source['name']} (HTML)")

    except Exception as e:
        log.warning(f"Failed to fetch from {source['name']}: {e}")

    return headlines


def fetch_headlines(source: dict) -> list:
    """Fetch headlines from a news source. Tries RSS first, falls back to HTML."""
    # Try RSS first (more reliable, designed for machine consumption)
    headlines = fetch_rss_headlines(source)

    # Fall back to HTML scraping if RSS didn't work
    if not headlines:
        headlines = fetch_html_headlines(source)

    return headlines


def scrape_all_sources() -> list:
    """Scrape headlines from all configured sources."""
    all_headlines = []

    for source in CONFIG["sources"]:
        headlines = fetch_headlines(source)
        all_headlines.extend(headlines)
        time.sleep(1)  # Be polite between requests

    return all_headlines


# =============================================================================
# VERIFICATION
# =============================================================================

def get_story_hash(text: str) -> str:
    """Generate hash of story text for deduplication."""
    return hashlib.md5(text.lower().encode()).hexdigest()[:12]


def are_sources_unrelated(source1_id: str, source2_id: str) -> bool:
    """Check if two sources are unrelated (different owners)."""
    sources = {s["id"]: s for s in CONFIG["sources"]}

    s1 = sources.get(source1_id)
    s2 = sources.get(source2_id)

    if not s1 or not s2:
        return False

    # Same owner = related
    if s1["owner"] == s2["owner"]:
        return False

    # Check institutional holder overlap
    holders1 = {h["name"] for h in s1.get("institutional_holders", [])}
    holders2 = {h["name"] for h in s2.get("institutional_holders", [])}

    shared = holders1 & holders2
    if len(shared) >= CONFIG["unrelated_rules"]["max_shared_top_holders"]:
        return False

    return True


def has_word_overlap(fact1: str, fact2: str, threshold: float = 0.15) -> bool:
    """Quick check if two facts share enough words to possibly be related.

    Returns True if at least threshold% of words overlap.
    This is a cheap pre-filter before calling Claude.
    """
    # Extract meaningful words (3+ chars, lowercase)
    words1 = set(w.lower() for w in fact1.split() if len(w) >= 3)
    words2 = set(w.lower() for w in fact2.split() if len(w) >= 3)

    if not words1 or not words2:
        return False

    shared = words1 & words2
    min_len = min(len(words1), len(words2))

    return len(shared) >= min_len * threshold


def find_matching_stories(fact: str, queue: list) -> list:
    """Find stories in queue that match this fact (same core event).

    Pre-filters with word overlap, then uses single Claude call for candidates.
    """
    if not queue:
        return []

    # Pre-filter: only check items with some word overlap (saves API calls)
    candidates = [item for item in queue if has_word_overlap(fact, item["fact"])]

    if not candidates:
        return []

    log.info(f"Word overlap pre-filter: {len(candidates)}/{len(queue)} candidates")

    try:
        client = anthropic.Anthropic()

        # Build numbered list of candidate facts
        queue_list = "\n".join([f"{i+1}. {item['fact']}" for i, item in enumerate(candidates)])

        prompt = f"""Compare this new fact against the numbered list below.
Return ONLY the numbers of facts that describe the SAME EVENT as the new fact.
Same event means: same incident, same person doing same action, same announcement.
Details like death counts or exact wording may differ.

New fact: {fact}

Existing facts:
{queue_list}

Reply with ONLY comma-separated numbers (e.g., "1,3,5") or "NONE" if no matches."""

        response = client.messages.create(
            model=CONFIG["claude"]["model"],
            max_tokens=50,
            messages=[{"role": "user", "content": prompt}]
        )

        answer = response.content[0].text.strip().upper()

        if answer == "NONE" or not answer:
            return []

        # Parse the numbers (referencing candidates list)
        matches = []
        for num_str in answer.replace(" ", "").split(","):
            try:
                idx = int(num_str) - 1  # Convert to 0-indexed
                if 0 <= idx < len(candidates):
                    matches.append(candidates[idx])
            except ValueError:
                continue

        return matches

    except Exception as e:
        log.error(f"Claude batch matching error: {e}")
        return []


def is_duplicate_batch(fact: str, published: list) -> bool:
    """Check if fact matches any published story using a single Claude call."""
    if not published:
        return False

    # Pre-filter: only check stories with word overlap
    candidates = [p for p in published if has_word_overlap(fact, p)]

    if not candidates:
        return False  # No overlap = definitely not a duplicate

    try:
        client = anthropic.Anthropic()

        # Build numbered list of candidate published facts
        pub_list = "\n".join([f"{i+1}. {p}" for i, p in enumerate(candidates)])

        prompt = f"""Does this new fact describe the SAME EVENT as any fact in the list below?
Same event means: same incident, same person doing same action, same announcement.
Details like death counts or exact wording may differ.

New fact: {fact}

Published facts:
{pub_list}

Reply with ONLY "YES" or "NO"."""

        response = client.messages.create(
            model=CONFIG["claude"]["model"],
            max_tokens=10,
            messages=[{"role": "user", "content": prompt}]
        )

        answer = response.content[0].text.strip().upper()
        if answer == "YES":
            log.info(f"Duplicate (Claude batch): '{fact[:40]}...'")
            return True
        return False

    except Exception as e:
        log.error(f"Claude duplicate check error: {e}")
        return False


# =============================================================================
# QUEUE MANAGEMENT
# =============================================================================

def load_queue() -> list:
    """Load the story queue from file."""
    queue_file = DATA_DIR / "queue.json"
    if queue_file.exists():
        with open(queue_file) as f:
            return json.load(f)
    return []


def save_queue(queue: list):
    """Save the story queue to file."""
    queue_file = DATA_DIR / "queue.json"
    with open(queue_file, 'w') as f:
        json.dump(queue, f, indent=2)


def clean_expired_queue(queue: list) -> list:
    """Remove stories older than 3 hours from queue."""
    timeout_hours = CONFIG["thresholds"]["queue_timeout_hours"]
    cutoff = datetime.now(timezone.utc).timestamp() - (timeout_hours * 3600)

    cleaned = []
    for item in queue:
        item_time = datetime.fromisoformat(item["timestamp"]).timestamp()
        if item_time > cutoff:
            cleaned.append(item)
        else:
            log.info(f"Expired from queue: {item['fact'][:50]}...")

    return cleaned


# =============================================================================
# DUPLICATE DETECTION
# =============================================================================

def load_shown_hashes() -> set:
    """Load hashes of stories shown today."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    hash_file = DATA_DIR / f"shown_{today}.txt"

    if hash_file.exists():
        with open(hash_file) as f:
            return set(line.strip() for line in f if line.strip())
    return set()


def add_shown_hash(story_hash: str):
    """Add a hash to today's shown list."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    hash_file = DATA_DIR / f"shown_{today}.txt"

    with open(hash_file, 'a') as f:
        f.write(story_hash + '\n')


def load_published_stories() -> list:
    """Load today's published stories from stories.json."""
    stories_file = DATA_DIR / "stories.json"
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    if stories_file.exists():
        try:
            with open(stories_file) as f:
                data = json.load(f)
            if data.get("date") == today:
                return [s["fact"] for s in data.get("stories", [])]
        except:
            pass
    return []


def is_duplicate(fact: str) -> bool:
    """Check if this fact matches any story already published today.

    Uses fast hash check first, then single Claude call for semantic matching.
    """
    # Fast path: exact text match via hash
    story_hash = get_story_hash(fact)
    shown = load_shown_hashes()
    if story_hash in shown:
        return True

    # Semantic check: single Claude call to check against all published stories
    published = load_published_stories()
    return is_duplicate_batch(fact, published)


# =============================================================================
# HEADLINE CACHE (Skip already-processed headlines to save API costs)
# =============================================================================

def load_processed_headlines() -> set:
    """Load hashes of headlines already sent to Claude today."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    cache_file = DATA_DIR / f"processed_{today}.txt"

    if cache_file.exists():
        with open(cache_file) as f:
            return set(line.strip() for line in f if line.strip())
    return set()


def add_processed_headline(headline_hash: str):
    """Mark a headline as processed."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    cache_file = DATA_DIR / f"processed_{today}.txt"

    with open(cache_file, 'a') as f:
        f.write(headline_hash + '\n')


def is_headline_processed(headline_text: str, processed_cache: set) -> bool:
    """Check if we've already sent this headline to Claude."""
    headline_hash = get_story_hash(headline_text)
    return headline_hash in processed_cache


# =============================================================================
# TEXT-TO-SPEECH
# =============================================================================

def get_next_audio_index() -> int:
    """Get the next audio file index based on today's stories."""
    stories_file = DATA_DIR / "stories.json"
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    if stories_file.exists():
        try:
            with open(stories_file) as f:
                stories = json.load(f)
            if stories.get("date") == today:
                return len(stories.get("stories", []))
        except:
            pass
    return 0


def generate_tts(text: str, audio_index: int = None) -> str:
    """Generate TTS audio using ElevenLabs. Returns audio filename."""
    try:
        client = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))

        # Generate audio using the new client API
        audio_generator = client.text_to_speech.convert(
            voice_id=os.getenv("ELEVENLABS_VOICE_ID"),
            text=text,
            model_id="eleven_multilingual_v2",
            voice_settings={
                "stability": 0.7,
                "similarity_boost": 0.8,
                "style": 0.3,
                "use_speaker_boost": True
            }
        )

        # Collect audio data
        audio_data = b''.join(chunk for chunk in audio_generator)

        # Save to indexed file for loop playback
        if audio_index is not None:
            indexed_path = AUDIO_DIR / f"audio_{audio_index}.mp3"
            with open(indexed_path, 'wb') as f:
                f.write(audio_data)

        # Also save to current.mp3 for immediate playback
        current_path = AUDIO_DIR / "current.mp3"
        with open(current_path, 'wb') as f:
            f.write(audio_data)

        log.info(f"Generated TTS: {text[:50]}...")
        return f"audio_{audio_index}.mp3" if audio_index is not None else "current.mp3"

    except Exception as e:
        log.error(f"TTS error: {e}")
        return False


# =============================================================================
# OUTPUT FILES
# =============================================================================

def write_current_story(fact: str, sources: list):
    """Write the current story to output files."""
    # Format source attribution
    source_text = " | ".join([
        f"{s['source_name']} - {s['source_rating']}"
        for s in sources[:2]
    ])

    # Write current story
    with open(DATA_DIR / "current.txt", 'w') as f:
        f.write(fact)

    # Write source attribution
    with open(DATA_DIR / "source.txt", 'w') as f:
        f.write(source_text)

    log.info(f"Published: {fact[:50]}...")


def append_daily_log(fact: str, sources: list, audio_file: str = None):
    """Append story to daily log."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    log_file = DATA_DIR / f"{today}.txt"

    timestamp = datetime.now(timezone.utc).isoformat()
    source_names = ",".join([s["source_name"] for s in sources[:2]])
    source_scores = ",".join([str(s["source_rating"]) for s in sources[:2]])

    line = f"{timestamp}|{source_names}|{source_scores}|{fact}\n"

    # Create header if new file
    if not log_file.exists():
        with open(log_file, 'w') as f:
            f.write(f"# JTF News Daily Log\n")
            f.write(f"# Date: {today}\n")
            f.write(f"# Generated: UTC\n\n")

    with open(log_file, 'a') as f:
        f.write(line)

    # Also update stories.json for JS loop
    update_stories_json(fact, sources, audio_file)


def update_stories_json(fact: str, sources: list, audio_file: str = None):
    """Update stories.json for the JS loop display."""
    stories_file = DATA_DIR / "stories.json"
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Load existing stories
    stories = {"date": today, "stories": []}
    if stories_file.exists():
        try:
            with open(stories_file) as f:
                stories = json.load(f)
            # Reset if it's a new day
            if stories.get("date") != today:
                stories = {"date": today, "stories": []}
        except:
            pass

    # Format source info
    source_text = " | ".join([
        f"{s['source_name']} - {s['source_rating']}"
        for s in sources[:2]
    ])

    # Add new story with cached audio file
    stories["stories"].append({
        "fact": fact,
        "source": source_text,
        "audio": f"../audio/{audio_file}" if audio_file else "../audio/current.mp3"
    })

    # Write back
    with open(stories_file, 'w') as f:
        json.dump(stories, f, indent=2)

    # Update RSS feed
    update_rss_feed(fact, sources)


def update_rss_feed(fact: str, sources: list):
    """Update RSS feed with new story and push to gh-pages."""
    import subprocess

    gh_pages_dir = BASE_DIR / "gh-pages-dist"
    feed_file = gh_pages_dir / "feed.xml"
    max_items = 50  # Keep last 50 stories in feed

    # Check if gh-pages worktree exists
    if not gh_pages_dir.exists():
        log.warning("gh-pages-dist worktree not found, skipping RSS update")
        return

    # Format source attribution
    source_text = ", ".join([s['source_name'] for s in sources[:2]])

    # Create new item
    pub_date = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")
    guid = hashlib.md5(f"{fact}{pub_date}".encode()).hexdigest()[:12]

    # Truncate fact for title (first 80 chars)
    title = fact[:80] + "..." if len(fact) > 80 else fact

    new_item = {
        "title": title,
        "description": fact,
        "source": source_text,
        "pubDate": pub_date,
        "guid": guid
    }

    # Load existing items or create new
    items = []
    if feed_file.exists():
        try:
            tree = ET.parse(feed_file)
            root = tree.getroot()
            channel = root.find("channel")
            for item in channel.findall("item"):
                items.append({
                    "title": item.find("title").text or "",
                    "description": item.find("description").text or "",
                    "source": item.find("source").text if item.find("source") is not None else "",
                    "pubDate": item.find("pubDate").text or "",
                    "guid": item.find("guid").text or ""
                })
        except:
            pass

    # Add new item at beginning
    items.insert(0, new_item)

    # Trim to max items
    items = items[:max_items]

    # Build RSS XML
    rss = ET.Element("rss", version="2.0")
    channel = ET.SubElement(rss, "channel")

    ET.SubElement(channel, "title").text = "JTF News - Just The Facts"
    ET.SubElement(channel, "link").text = "https://larryseyer.github.io/jtfnews/"
    ET.SubElement(channel, "description").text = "Verified facts from multiple sources. No opinions. No adjectives. No interpretation."
    ET.SubElement(channel, "language").text = "en-us"
    ET.SubElement(channel, "lastBuildDate").text = pub_date

    for item_data in items:
        item = ET.SubElement(channel, "item")
        ET.SubElement(item, "title").text = item_data["title"]
        ET.SubElement(item, "description").text = item_data["description"]
        ET.SubElement(item, "source").text = item_data["source"]
        ET.SubElement(item, "pubDate").text = item_data["pubDate"]
        ET.SubElement(item, "guid", isPermaLink="false").text = item_data["guid"]

    # Write with XML declaration
    tree = ET.ElementTree(rss)
    ET.indent(tree, space="  ")
    with open(feed_file, 'wb') as f:
        tree.write(f, encoding="utf-8", xml_declaration=True)

    log.info(f"RSS feed updated: {len(items)} items")

    # Commit and push to gh-pages
    try:
        subprocess.run(
            ["git", "add", "feed.xml"],
            cwd=gh_pages_dir,
            check=True,
            capture_output=True
        )
        subprocess.run(
            ["git", "commit", "-m", f"Update feed: {title[:50]}"],
            cwd=gh_pages_dir,
            check=True,
            capture_output=True
        )
        subprocess.run(
            ["git", "push"],
            cwd=gh_pages_dir,
            check=True,
            capture_output=True
        )
        log.info("RSS feed pushed to gh-pages")
    except subprocess.CalledProcessError as e:
        log.warning(f"Failed to push RSS feed: {e}")


# =============================================================================
# ALERTS
# =============================================================================

def send_alert(message: str):
    """Send SMS alert via Twilio."""
    try:
        client = TwilioClient(
            os.getenv("TWILIO_ACCOUNT_SID"),
            os.getenv("TWILIO_AUTH_TOKEN")
        )

        client.messages.create(
            body=f"JTF: {message}",
            from_=os.getenv("TWILIO_PHONE_NUMBER"),
            to=os.getenv("ALERT_PHONE_NUMBER")
        )

        log.warning(f"Alert sent: {message}")

    except Exception as e:
        log.error(f"Failed to send alert: {e}")


# =============================================================================
# ARCHIVE
# =============================================================================

def archive_daily_log():
    """Archive yesterday's log to GitHub."""
    yesterday = (datetime.now(timezone.utc).date() -
                 __import__('datetime').timedelta(days=1))
    yesterday_str = yesterday.strftime("%Y-%m-%d")
    year = yesterday.strftime("%Y")

    log_file = DATA_DIR / f"{yesterday_str}.txt"
    hash_file = DATA_DIR / f"shown_{yesterday_str}.txt"

    if not log_file.exists():
        log.info("No log to archive")
        return

    # Create year folder in archive
    year_dir = ARCHIVE_DIR / year
    year_dir.mkdir(exist_ok=True)

    # Gzip the log
    archive_file = year_dir / f"{yesterday_str}.txt.gz"
    with open(log_file, 'rb') as f_in:
        with gzip.open(archive_file, 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)

    log.info(f"Archived: {archive_file}")

    # Clean up old files
    log_file.unlink(missing_ok=True)
    hash_file.unlink(missing_ok=True)

    # Clean up processed headlines cache
    processed_file = DATA_DIR / f"processed_{yesterday_str}.txt"
    processed_file.unlink(missing_ok=True)

    # Git commit and push (if configured)
    # This would use GitHub API or subprocess for git commands
    # Simplified for now
    log.info("Archive complete - manual git push needed")


# =============================================================================
# MAIN LOOP
# =============================================================================

def process_cycle():
    """Run one processing cycle."""
    log.info("=" * 60)
    log.info("Starting cycle")

    # Check kill switch
    if KILL_SWITCH.exists():
        log.warning("KILL SWITCH ACTIVE - Stopping")
        sys.exit(0)

    # Load queue
    queue = load_queue()
    queue = clean_expired_queue(queue)

    # Scrape headlines
    headlines = scrape_all_sources()
    log.info(f"Total headlines: {len(headlines)}")

    # Load processed headlines cache
    processed_cache = load_processed_headlines()
    skipped_count = 0
    published_count = 0

    for headline in headlines:
        # Skip if already processed (saves API costs)
        if is_headline_processed(headline["text"], processed_cache):
            skipped_count += 1
            continue

        # Mark as processed before calling API
        add_processed_headline(get_story_hash(headline["text"]))

        # Extract fact
        result = extract_fact(headline["text"])

        # Skip if not a fact
        if result["fact"] == "SKIP":
            continue

        fact = result["fact"]
        confidence = result["confidence"]

        # Check confidence threshold
        if confidence < CONFIG["thresholds"]["min_confidence"]:
            log.info(f"Low confidence ({confidence}%): {fact[:40]}...")
            continue

        # Check newsworthiness threshold
        newsworthy = result.get("newsworthy", True)  # Default to True for backwards compatibility
        threshold_met = result.get("threshold_met", "unknown")
        if not newsworthy:
            log.info(f"Not newsworthy ({threshold_met}): {fact[:40]}...")
            continue

        # Check for duplicates
        if is_duplicate(fact):
            log.info(f"Duplicate: {fact[:40]}...")
            continue

        # Look for matching stories in queue
        matches = find_matching_stories(fact, queue)

        if matches:
            # Check if any match has unrelated source
            for match in matches:
                if are_sources_unrelated(headline["source_id"], match["source_id"]):
                    # VERIFIED! Two unrelated sources
                    sources = [headline, match]

                    # Get audio index for caching
                    audio_index = get_next_audio_index()

                    # Generate TTS first (before JS sees the new story)
                    audio_file = generate_tts(fact, audio_index)

                    # Now write output (JS will detect and play)
                    write_current_story(fact, sources)
                    append_daily_log(fact, sources, audio_file)
                    add_shown_hash(get_story_hash(fact))

                    # Remove from queue
                    queue = [q for q in queue if q["fact"] != match["fact"]]

                    published_count += 1
                    log.info(f"VERIFIED: {fact[:50]}...")
                    break
        else:
            # No match - add to queue
            queue.append({
                "fact": fact,
                "source_id": headline["source_id"],
                "source_name": headline["source_name"],
                "source_rating": headline["source_rating"],
                "timestamp": headline["timestamp"],
                "confidence": confidence
            })
            log.info(f"Queued: {fact[:40]}...")

    # Save queue
    save_queue(queue)

    log.info(f"Cycle complete. Published: {published_count}, Queue: {len(queue)}, Skipped (cached): {skipped_count}")


def check_midnight_archive():
    """Check if it's time to archive (midnight GMT)."""
    now = datetime.now(timezone.utc)
    if now.hour == 0 and now.minute < 5:
        archive_daily_log()


def main():
    """Main entry point."""
    log.info("JTF News starting...")
    log.info("Facts only. No opinions.")
    log.info("-" * 40)

    interval_minutes = CONFIG["timing"]["scrape_interval_minutes"]
    interval_seconds = interval_minutes * 60

    while True:
        try:
            # Check for midnight archive
            check_midnight_archive()

            # Run cycle
            process_cycle()

            # Sleep until next cycle
            log.info(f"Sleeping {interval_minutes} minutes...")
            time.sleep(interval_seconds)

        except KeyboardInterrupt:
            log.info("Shutting down...")
            break
        except Exception as e:
            log.error(f"Cycle error: {e}")
            send_alert(f"Error: {str(e)[:50]}")
            time.sleep(60)  # Wait 1 minute on error


if __name__ == "__main__":
    main()
