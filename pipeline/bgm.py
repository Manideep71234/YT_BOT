"""Fetch background music.

Downloads a royalty-free creepy background track from YouTube.
"""
from __future__ import annotations

import os
import sys
import subprocess
from pathlib import Path

# A royalty-free creepy ambient track
# Kevin MacLeod - "Come Play with Me" or similar spooky ambient
BGM_YOUTUBE_URL = "https://www.youtube.com/watch?v=1F2cOetVfM4" # Dark Ambient Background Music

def ensure_bgm_downloaded(out_path: Path) -> Path:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    
    if not out_path.exists():
        print(f"   [bgm] Downloading real royalty-free horror BGM to {out_path}...")
        
        ffmpeg_bin = r"C:\ffmpeg\bin"
        if "ffmpeg" not in os.environ.get("PATH", "").lower():
            os.environ["PATH"] += os.pathsep + ffmpeg_bin
            
        cmd = [
            sys.executable, "-m", "yt_dlp",
            "-x", "--audio-format", "mp3",
            "-o", str(out_path.with_suffix('')),
            "https://www.youtube.com/watch?v=xAO3x-Uhfoo"
        ]
        
        if os.name == 'nt':
            cmd[3:3] = ["--ffmpeg-location", r"C:\ffmpeg\bin"]
        
        try:
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError as e:
            print(f"   [bgm] WARNING: yt-dlp failed: {e}. Generating fallback drone instead.")
            subprocess.run([
                "ffmpeg", "-y", "-hide_banner", "-loglevel", "warning",
                "-f", "lavfi",
                "-i", "sine=frequency=55:duration=60",
                "-af", "tremolo=f=5.0:d=0.8, aecho=0.8:0.8:100|200:0.3|0.2",
                "-c:a", "libmp3lame",
                str(out_path)
            ], check=True)
            
    return out_path
