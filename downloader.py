"""
downloader.py - Downloads Instagram (and other) videos using yt-dlp
"""
import os
import subprocess
import tempfile
from pathlib import Path


def download_video(url: str, output_dir: str) -> str:
    """
    Download a video from Instagram (or any yt-dlp supported URL).
    Returns the path to the downloaded video file.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    output_template = str(output_dir / "video.%(ext)s")

    cmd = [
        "yt-dlp",
        "--no-playlist",
        "--format", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "--merge-output-format", "mp4",
        "--output", output_template,
        "--no-warnings",
        url,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"yt-dlp failed:\n{result.stderr}")

    # Find the downloaded file
    for f in output_dir.iterdir():
        if f.name.startswith("video") and f.suffix in (".mp4", ".mkv", ".webm", ".mov"):
            return str(f)

    raise FileNotFoundError("Downloaded video file not found in output directory.")
