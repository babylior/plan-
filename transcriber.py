"""
transcriber.py - Transcribes video audio using OpenAI Whisper with word-level timestamps
"""
import whisper
import subprocess
import os
from pathlib import Path
from typing import List, Dict


def extract_audio(video_path: str, audio_path: str) -> str:
    """Extract audio from video as WAV for Whisper."""
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-vn",                    # no video
        "-acodec", "pcm_s16le",   # PCM 16-bit
        "-ar", "16000",            # 16kHz (Whisper's preferred rate)
        "-ac", "1",               # mono
        audio_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg audio extraction failed:\n{result.stderr}")
    return audio_path


def transcribe(video_path: str, model_size: str = "base") -> List[Dict]:
    """
    Transcribe the audio of a video file.
    Returns a list of segments, each with:
      - start: float (seconds)
      - end: float (seconds)
      - text: str
    """
    audio_path = video_path.replace(Path(video_path).suffix, "_audio.wav")

    print(f"  Extracting audio from video...")
    extract_audio(video_path, audio_path)

    print(f"  Loading Whisper model '{model_size}'...")
    model = whisper.load_model(model_size)

    print(f"  Transcribing...")
    result = model.transcribe(audio_path, word_timestamps=True, verbose=False)

    # Clean up temporary audio file
    try:
        os.remove(audio_path)
    except OSError:
        pass

    segments = []
    for seg in result.get("segments", []):
        segments.append({
            "start": seg["start"],
            "end": seg["end"],
            "text": seg["text"].strip(),
        })

    return segments
