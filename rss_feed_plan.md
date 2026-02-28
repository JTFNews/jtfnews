# JTF News Podcast Feed Implementation Plan

## Overview
Convert daily YouTube video digests into Apple Podcast-compatible feeds using Archive.org for free hosting.

## Architecture Summary

```
Daily Digest Video (MP4)
         │
         ├──► YouTube (existing)
         │
         └──► NEW: Podcast Pipeline
                    │
                    ├── Convert to 320kbps MP3
                    ├── Upload MP3 + MP4 to Archive.org
                    ├── Update podcast.xml (audio feed)
                    ├── Update podcast-video.xml (video feed)
                    └── Push feeds to GitHub Pages
```

## Key Decisions

- **Media format:** Both audio (MP3) and video (MP4), with audio as primary
- **Hosting:** Archive.org (free, unlimited bandwidth)
- **Feed hosting:** GitHub Pages at jtfnews.org
- **Implementation:** Integrated into main.py (not separate module)
- **Archive.org structure:** One item per episode (`jtf-news-YYYY-MM-DD`)
- **Timing:** Runs automatically after YouTube upload succeeds

## Files to Create/Modify

| File | Action | Purpose |
|------|--------|---------|
| `main.py` | Modify | Add podcast functions (~200-300 lines) |
| `docs/podcast.xml` | Create | Apple Podcast-compatible audio feed |
| `docs/podcast-video.xml` | Create | Video podcast feed |
| `.env` | Modify | Add Archive.org API keys |
| `docs/assets/podcast-artwork.png` | Create | 3000x3000 podcast cover (convert from icon-square.svg) |

## Implementation Steps

### Step 1: Archive.org Account Setup
1. Create account at https://archive.org/account/signup using jtfnews.org email
2. Get API keys from https://archive.org/account/s3.php
3. Install `internetarchive` Python library: `pip install internetarchive`
4. Add to `.env`:
   ```
   ARCHIVE_ORG_ACCESS_KEY=xxx
   ARCHIVE_ORG_SECRET_KEY=xxx
   ```
5. Test upload manually with `ia` CLI:
   ```bash
   ia configure  # Enter keys when prompted
   ia upload jtf-news-test test.mp3 --metadata="mediatype:movies" --metadata="collection:opensource_movies"
   ```

### Step 2: Create Podcast Artwork
Convert icon-square.svg to 3000x3000 PNG:
```bash
# Using Inkscape (if installed)
inkscape icon-square.svg --export-type=png --export-filename=docs/assets/podcast-artwork.png -w 3000 -h 3000

# Or using ImageMagick
convert -background none -density 1200 icon-square.svg -resize 3000x3000 docs/assets/podcast-artwork.png

# Or using rsvg-convert
rsvg-convert -w 3000 -h 3000 icon-square.svg > docs/assets/podcast-artwork.png
```

### Step 3: Add Podcast Functions to main.py

**Function 1: convert_video_to_podcast_audio()**
```python
def convert_video_to_podcast_audio(video_path: str, output_path: str) -> bool:
    """Convert MP4 to 320kbps MP3 using ffmpeg"""
    cmd = [
        'ffmpeg', '-i', video_path,
        '-vn',              # No video
        '-ab', '320k',      # 320kbps bitrate
        '-ar', '44100',     # 44.1kHz sample rate
        '-y',               # Overwrite output
        output_path
    ]
    result = subprocess.run(cmd, capture_output=True)
    return result.returncode == 0
```

**Function 2: upload_to_archive_org()**
```python
def upload_to_archive_org(date: str, mp3_path: str, mp4_path: str) -> dict:
    """Upload episode files to Archive.org

    Uses internetarchive library with credentials from environment variables:
    - ARCHIVE_ORG_ACCESS_KEY
    - ARCHIVE_ORG_SECRET_KEY

    Returns: {
        'item_id': 'jtf-news-2026-02-28',
        'audio_url': 'https://archive.org/download/jtf-news-2026-02-28/digest.mp3',
        'video_url': 'https://archive.org/download/jtf-news-2026-02-28/digest.mp4',
        'audio_size': 4521984,
        'video_size': 52428800
    }
    """
    import internetarchive as ia

    item_id = f"jtf-news-{date}"

    # Upload both files with metadata
    ia.upload(
        item_id,
        files=[mp3_path, mp4_path],
        metadata={
            'mediatype': 'movies',
            'collection': 'opensource_movies',
            'creator': 'JTF News',
            'date': date,
            'title': f'JTF News Daily Digest - {date}',
            'description': 'Daily digest of verified news facts. No opinions, no adjectives.',
            'licenseurl': 'https://creativecommons.org/licenses/by-sa/4.0/',
            'subject': ['news', 'daily digest', 'facts', 'journalism']
        },
        access_key=os.environ.get('ARCHIVE_ORG_ACCESS_KEY'),
        secret_key=os.environ.get('ARCHIVE_ORG_SECRET_KEY')
    )

    # Get file sizes for RSS enclosure tags
    audio_size = os.path.getsize(mp3_path)
    video_size = os.path.getsize(mp4_path)

    return {
        'item_id': item_id,
        'audio_url': f'https://archive.org/download/{item_id}/digest.mp3',
        'video_url': f'https://archive.org/download/{item_id}/digest.mp4',
        'audio_size': audio_size,
        'video_size': video_size
    }
```

**Function 3: update_podcast_feeds()**
```python
def update_podcast_feeds(date: str, archive_result: dict, story_count: int, duration_seconds: int) -> None:
    """Update both podcast.xml and podcast-video.xml

    Reads existing feed, prepends new episode, writes back.
    """
    # Parse existing feed
    # Create new <item> element with:
    #   - <title>JTF News - Month Day, Year</title>
    #   - <enclosure url="..." type="audio/mpeg" length="..."/>
    #   - <guid isPermaLink="false">jtf-news-YYYY-MM-DD</guid>
    #   - <pubDate>RFC 2822 format</pubDate>
    #   - <itunes:duration>MM:SS</itunes:duration>
    #   - <description>X verified facts from today's news.</description>
    # Insert as first item in channel
    # Write updated feed
```

**Function 4: push_podcast_feeds()**
```python
def push_podcast_feeds() -> None:
    """Commit and push podcast feeds to GitHub Pages

    Use existing GitHub API pattern from main.py (push_file_to_github)
    """
    push_file_to_github('docs/podcast.xml', 'Update podcast feed')
    push_file_to_github('docs/podcast-video.xml', 'Update video podcast feed')
```

### Step 4: Integrate into Digest Workflow

In `generate_and_upload_daily_summary()` (around line 4456), after YouTube upload:
```python
# After successful YouTube upload
if youtube_id:
    try:
        # Convert video to podcast audio
        mp3_path = video_path.replace('.mp4', '.mp3')
        if convert_video_to_podcast_audio(video_path, mp3_path):
            # Upload to Archive.org
            archive_result = upload_to_archive_org(date, mp3_path, video_path)

            # Update podcast feeds
            update_podcast_feeds(date, archive_result, story_count, duration_seconds)
            push_podcast_feeds()

            # Update status
            status['archive_org_id'] = archive_result['item_id']
            status['archive_audio_url'] = archive_result['audio_url']
            status['archive_video_url'] = archive_result['video_url']
            status['podcast_updated'] = True

            log(f"Podcast published: {archive_result['audio_url']}")
    except Exception as e:
        alert(f"Podcast upload failed: {e}")
        # Don't fail the overall digest - YouTube upload already succeeded
```

### Step 5: Create Initial Podcast RSS Feeds

**docs/podcast.xml** (audio feed):
```xml
<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"
     xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd"
     xmlns:atom="http://www.w3.org/2005/Atom"
     xmlns:content="http://purl.org/rss/1.0/modules/content/">
  <channel>
    <title>JTF News Daily Digest</title>
    <link>https://jtfnews.org</link>
    <language>en-us</language>
    <copyright>CC BY-SA 4.0</copyright>
    <itunes:author>JTF News</itunes:author>
    <itunes:owner>
      <itunes:name>JTF News</itunes:name>
      <itunes:email>podcast@jtfnews.org</itunes:email>
    </itunes:owner>
    <description>Verified facts without opinion. Daily news digest following the JTF methodology: two unrelated sources, no adjectives, just facts. What happened, where, when, and how many. Nothing more.</description>
    <itunes:image href="https://jtfnews.org/assets/podcast-artwork.png"/>
    <itunes:category text="News">
      <itunes:category text="Daily News"/>
    </itunes:category>
    <itunes:explicit>false</itunes:explicit>
    <itunes:type>episodic</itunes:type>
    <atom:link href="https://jtfnews.org/podcast.xml" rel="self" type="application/rss+xml"/>
    <!-- Episodes will be inserted here -->
  </channel>
</rss>
```

**docs/podcast-video.xml** (video feed):
```xml
<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"
     xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd"
     xmlns:atom="http://www.w3.org/2005/Atom"
     xmlns:content="http://purl.org/rss/1.0/modules/content/">
  <channel>
    <title>JTF News Daily Digest (Video)</title>
    <link>https://jtfnews.org</link>
    <language>en-us</language>
    <copyright>CC BY-SA 4.0</copyright>
    <itunes:author>JTF News</itunes:author>
    <itunes:owner>
      <itunes:name>JTF News</itunes:name>
      <itunes:email>podcast@jtfnews.org</itunes:email>
    </itunes:owner>
    <description>Verified facts without opinion. Daily video digest following the JTF methodology: two unrelated sources, no adjectives, just facts.</description>
    <itunes:image href="https://jtfnews.org/assets/podcast-artwork.png"/>
    <itunes:category text="News">
      <itunes:category text="Daily News"/>
    </itunes:category>
    <itunes:explicit>false</itunes:explicit>
    <itunes:type>episodic</itunes:type>
    <atom:link href="https://jtfnews.org/podcast-video.xml" rel="self" type="application/rss+xml"/>
    <!-- Episodes will be inserted here with type="video/mp4" -->
  </channel>
</rss>
```

**Episode item template:**
```xml
<item>
  <title>JTF News - February 28, 2026</title>
  <description>8 verified facts from today's news.</description>
  <enclosure url="https://archive.org/download/jtf-news-2026-02-28/digest.mp3"
             type="audio/mpeg"
             length="4521984"/>
  <guid isPermaLink="false">jtf-news-2026-02-28</guid>
  <pubDate>Sat, 28 Feb 2026 06:00:00 GMT</pubDate>
  <itunes:duration>02:34</itunes:duration>
  <itunes:episode>1</itunes:episode>
  <itunes:explicit>false</itunes:explicit>
</item>
```

### Step 6: Testing

1. **Test Archive.org upload manually:**
   ```bash
   ia upload jtf-news-test test.mp3 --metadata="mediatype:movies" --metadata="collection:opensource_movies" --metadata="creator:JTF News"
   ```

2. **Verify upload:**
   - Check https://archive.org/details/jtf-news-test
   - Confirm direct download URL works: https://archive.org/download/jtf-news-test/test.mp3

3. **Validate RSS feeds:**
   - Apple: https://podba.se/validate/
   - W3C: https://validator.w3.org/feed/
   - Cast Feed Validator: https://castfeedvalidator.com/

4. **Test episode playback:**
   - Add feed URL to a podcast app manually
   - Verify audio plays correctly

### Step 7: Submit to Podcast Directories

1. **Apple Podcasts:**
   - Go to https://podcastsconnect.apple.com/
   - Sign in with Apple ID
   - Submit RSS feed URL: `https://jtfnews.org/podcast.xml`
   - Wait for approval (usually 24-48 hours)

2. **Spotify:**
   - Go to https://podcasters.spotify.com/
   - Create account or sign in
   - Submit RSS feed URL
   - Verify ownership

3. **Other directories** (will auto-discover from Apple/Spotify, or submit manually):
   - Google Podcasts (auto from RSS)
   - Pocket Casts
   - Overcast
   - Castro
   - Podcast Index (https://podcastindex.org/)

## Archive.org Item Structure

```
Item ID: jtf-news-YYYY-MM-DD
├── digest.mp3 (320kbps audio, ~2.4MB per minute)
├── digest.mp4 (original video)
└── Metadata:
    ├── mediatype: movies (allows both audio and video)
    ├── collection: opensource_movies
    ├── creator: JTF News
    ├── date: YYYY-MM-DD
    ├── licenseurl: CC BY-SA 4.0
    ├── title: JTF News Daily Digest - YYYY-MM-DD
    ├── description: Daily digest of verified news facts
    └── subject: news, daily digest, facts, journalism
```

## RSS Feed URLs

| Feed | URL | Purpose |
|------|-----|---------|
| Audio (primary) | https://jtfnews.org/podcast.xml | Apple Podcasts, Spotify, all apps |
| Video | https://jtfnews.org/podcast-video.xml | Video podcast apps |

## Environment Variables

Add to `.env`:
```bash
ARCHIVE_ORG_ACCESS_KEY=your_access_key_here
ARCHIVE_ORG_SECRET_KEY=your_secret_key_here
```

## Error Handling

- **Archive.org upload fails:** Retry with exponential backoff using existing resilience system, alert via Twilio if persistent
- **RSS generation fails:** Alert, but don't break YouTube digest flow
- **YouTube and podcast uploads are independent:** One can fail without affecting the other
- **Archive.org item already exists:** Check first, skip upload if already present (idempotent)

## Dependencies

```bash
pip install internetarchive
```

The `ffmpeg` tool is already installed and used for video processing.

## Verification Checklist

- [ ] Archive.org account created with jtfnews.org email
- [ ] API keys obtained from https://archive.org/account/s3.php
- [ ] API keys added to .env file
- [ ] `internetarchive` Python library installed
- [ ] Manual test upload to Archive.org successful
- [ ] Podcast artwork created (3000x3000 PNG from icon-square.svg)
- [ ] Artwork uploaded to docs/assets/podcast-artwork.png
- [ ] Podcast functions added to main.py
- [ ] Initial podcast.xml created
- [ ] Initial podcast-video.xml created
- [ ] RSS feeds pushed to GitHub Pages
- [ ] RSS feeds validate (Apple, W3C validators)
- [ ] First automated episode uploads successfully
- [ ] Episode playback works in podcast app
- [ ] Submitted to Apple Podcasts
- [ ] Submitted to Spotify
- [ ] Apple Podcasts approved and live

## Notes

- Archive.org items are **permanent** - choose identifiers carefully
- The `jtf-news-YYYY-MM-DD` naming ensures uniqueness
- Use `mediatype:movies` to allow both audio and video in same item
- Apple Podcasts requires consistent feed URL - don't change it after submission
- Keep episode GUIDs stable (never change after publishing)
