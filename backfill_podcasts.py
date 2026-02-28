#!/usr/bin/env python3
"""Backfill all existing daily digest videos to Archive.org and podcast feeds."""

import os
import sys
import gzip
import subprocess
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from main import (
    convert_video_to_podcast_audio,
    upload_to_archive_org,
    update_podcast_feeds,
    log,
)

VIDEO_DIR = Path("video")
ARCHIVE_DIR = Path("docs/archive/2026")


def get_video_duration(video_path: str) -> int:
    """Get video duration in seconds via ffprobe."""
    result = subprocess.run(
        ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
         '-of', 'csv=p=0', video_path],
        capture_output=True, text=True, timeout=30
    )
    return int(float(result.stdout.strip()))


def get_facts_from_archive(date: str) -> list:
    """Extract fact strings from archived daily log.

    Log format: timestamp|sources|ratings|urls|audio_file|fact text
    Lines starting with # are comments.
    """
    gz_path = ARCHIVE_DIR / f"{date}.txt.gz"
    if not gz_path.exists():
        return []
    try:
        facts = []
        with gzip.open(gz_path, 'rt') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                parts = line.split('|')
                if len(parts) >= 6:
                    facts.append(parts[5])
        return facts
    except Exception:
        return []


def main():
    # Find all videos sorted chronologically
    videos = sorted(VIDEO_DIR.glob("*-daily-digest.mp4"))
    print(f"Found {len(videos)} videos to backfill\n")

    # Reset podcast.xml to empty (so episode numbers are correct)
    feed_path = Path("docs/podcast.xml")
    if feed_path.exists():
        content = feed_path.read_text()
        while "<item>" in content:
            start = content.index("<item>") - 4  # include indent
            end = content.index("</item>") + len("</item>") + 1  # include newline
            content = content[:start] + content[end:]
        feed_path.write_text(content)
    print("Reset podcast.xml to empty\n")

    success = 0
    failed = 0

    for video_path in videos:
        # Extract date from filename: 2026-02-15-daily-digest.mp4
        date = video_path.stem.replace("-daily-digest", "")
        mp3_path = str(video_path).replace(".mp4", ".mp3")

        print(f"{'='*60}")
        print(f"Processing {date}")
        print(f"  Video: {video_path} ({video_path.stat().st_size / 1024 / 1024:.1f} MB)")

        try:
            # Get metadata
            duration = get_video_duration(str(video_path))
            facts = get_facts_from_archive(date)
            story_count = len(facts)
            print(f"  Duration: {duration}s, Stories: {story_count}")
            if facts:
                print(f"  First fact: {facts[0][:80]}...")

            # Convert to MP3
            print(f"  Converting to MP3...")
            if not convert_video_to_podcast_audio(str(video_path), mp3_path):
                print(f"  FAILED: MP3 conversion")
                failed += 1
                continue

            mp3_size = os.path.getsize(mp3_path) / (1024 * 1024)
            print(f"  MP3: {mp3_size:.2f} MB")

            # Upload to Archive.org (skips if already exists)
            print(f"  Uploading to Archive.org...")
            archive_result = upload_to_archive_org(date, mp3_path, str(video_path))
            print(f"  Uploaded: {archive_result['item_id']}")

            # Update feed with full facts
            update_podcast_feeds(date, archive_result, story_count, duration, facts=facts)
            print(f"  Feed updated with {story_count} facts")

            # Delete temporary MP3
            Path(mp3_path).unlink()
            print(f"  Cleaned up MP3")

            success += 1
            print(f"  DONE\n")

        except Exception as e:
            print(f"  FAILED: {e}\n")
            failed += 1
            # Clean up MP3 if it exists
            if Path(mp3_path).exists():
                Path(mp3_path).unlink()

    print(f"{'='*60}")
    print(f"Backfill complete: {success} succeeded, {failed} failed out of {len(videos)}")


if __name__ == "__main__":
    main()
