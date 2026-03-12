"""
frame_extractor.py - Extracts the best representative frame for each transcript segment
"""
import subprocess
import os
from pathlib import Path
from typing import List, Dict


def get_video_duration(video_path: str) -> float:
    """Get video duration in seconds using ffprobe."""
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        video_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {result.stderr}")
    return float(result.stdout.strip())


def extract_frame_at(video_path: str, timestamp: float, output_path: str) -> str:
    """Extract a single frame at a given timestamp (seconds)."""
    cmd = [
        "ffmpeg", "-y",
        "-ss", str(timestamp),
        "-i", video_path,
        "-frames:v", "1",
        "-q:v", "2",           # high quality JPEG
        output_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg frame extraction failed:\n{result.stderr}")
    return output_path


def extract_frames_for_segments(
    video_path: str,
    segments: List[Dict],
    frames_dir: str,
) -> List[Dict]:
    """
    For each transcript segment, extract the frame at the midpoint of the segment.
    Returns the segments list enriched with a 'frame_path' key.
    """
    frames_dir = Path(frames_dir)
    frames_dir.mkdir(parents=True, exist_ok=True)

    duration = get_video_duration(video_path)
    enriched = []

    for i, seg in enumerate(segments):
        # Pick midpoint of the segment, clamped to video duration
        midpoint = (seg["start"] + seg["end"]) / 2
        midpoint = min(midpoint, duration - 0.1)
        midpoint = max(midpoint, 0)

        frame_path = str(frames_dir / f"frame_{i:04d}.jpg")
        try:
            extract_frame_at(video_path, midpoint, frame_path)
            enriched.append({**seg, "frame_path": frame_path, "frame_time": midpoint})
        except Exception as e:
            print(f"  Warning: could not extract frame for segment {i}: {e}")
            enriched.append({**seg, "frame_path": None, "frame_time": midpoint})

    return enriched
