#!/usr/bin/env python3
"""
main.py - Video Storyboard Generator
Usage:
  python main.py <instagram_or_video_url> [options]

Generates an HTML storyboard and optionally a PNG grid image from any video URL.
"""

import argparse
import os
import sys
import tempfile
import shutil
from pathlib import Path

from downloader import download_video
from transcriber import transcribe
from frame_extractor import extract_frames_for_segments
from storyboard import build_storyboard_html, build_storyboard_image


def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate a storyboard from an Instagram (or other) video URL."
    )
    parser.add_argument("url", help="Instagram reel / TikTok / YouTube / direct video URL")
    parser.add_argument(
        "-o", "--output-dir",
        default="storyboard_output",
        help="Directory to save outputs (default: storyboard_output)",
    )
    parser.add_argument(
        "--model",
        default="base",
        choices=["tiny", "base", "small", "medium", "large"],
        help="Whisper model size (default: base). Larger = more accurate but slower.",
    )
    parser.add_argument(
        "--columns",
        type=int,
        default=2,
        help="Number of columns in the PNG grid (default: 2)",
    )
    parser.add_argument(
        "--png",
        action="store_true",
        help="Also save a PNG grid image (in addition to HTML)",
    )
    parser.add_argument(
        "--no-download",
        metavar="VIDEO_PATH",
        help="Skip download; use a local video file instead",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    work_dir = output_dir / "_work"
    frames_dir = output_dir / "frames"

    print("\n=== Video Storyboard Generator ===\n")

    # ── Step 1: Download (or use local file) ──────────────────────────────────
    if args.no_download:
        video_path = args.no_download
        if not os.path.exists(video_path):
            print(f"Error: file not found: {video_path}", file=sys.stderr)
            sys.exit(1)
        print(f"Using local video: {video_path}")
    else:
        print(f"[1/4] Downloading video from:\n  {args.url}\n")
        work_dir.mkdir(parents=True, exist_ok=True)
        try:
            video_path = download_video(args.url, str(work_dir))
            print(f"  Downloaded: {video_path}\n")
        except Exception as e:
            print(f"Error downloading video: {e}", file=sys.stderr)
            sys.exit(1)

    # ── Step 2: Transcribe ────────────────────────────────────────────────────
    print(f"[2/4] Transcribing audio (model: {args.model})...\n")
    try:
        segments = transcribe(video_path, model_size=args.model)
    except Exception as e:
        print(f"Error during transcription: {e}", file=sys.stderr)
        sys.exit(1)

    if not segments:
        print("Warning: no speech detected in video. Storyboard will have no text.")
        segments = [{"start": 0, "end": 1, "text": "(no speech detected)"}]
    else:
        print(f"  Found {len(segments)} segments.\n")

    # ── Step 3: Extract frames ────────────────────────────────────────────────
    print(f"[3/4] Extracting frames for {len(segments)} segments...\n")
    try:
        enriched = extract_frames_for_segments(video_path, segments, str(frames_dir))
    except Exception as e:
        print(f"Error extracting frames: {e}", file=sys.stderr)
        sys.exit(1)

    # ── Step 4: Build storyboard ──────────────────────────────────────────────
    print(f"[4/4] Building storyboard...\n")
    url = args.url if not args.no_download else ""

    html_path = str(output_dir / "storyboard.html")
    build_storyboard_html(enriched, html_path, video_url=url)

    if args.png:
        png_path = str(output_dir / "storyboard.png")
        build_storyboard_image(enriched, png_path, columns=args.columns)

    # ── Done ──────────────────────────────────────────────────────────────────
    print("\n✓ Storyboard complete!\n")
    print(f"  Output directory : {output_dir.resolve()}")
    print(f"  HTML storyboard  : {html_path}")
    if args.png:
        print(f"  PNG grid image   : {png_path}")
    print()


if __name__ == "__main__":
    main()
