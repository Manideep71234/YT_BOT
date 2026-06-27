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
BGM_YOUTUBE_URL = "https://www.youtube.com/watch?v=VsjSb9oFLZI" # Dark Ambient Background Music

def ensure_bgm_downloaded(out_path: Path) -> Path:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    
    if not out_path.exists():
        # First check if there's any local music in assets/music
        import shutil
        import random
        
        music_dir = Path("assets/music")
        if music_dir.exists() and music_dir.is_dir():
            local_tracks = list(music_dir.glob("*.mp3")) + list(music_dir.glob("*.wav"))
            if local_tracks:
                chosen_track = random.choice(local_tracks)
                print(f"   [bgm] Found local music track: {chosen_track.name}. Using it instead of downloading!")
                shutil.copy(chosen_track, out_path)
                return out_path
                
        print(f"   [bgm] Downloading real royalty-free horror BGM to {out_path}...")
        
        ffmpeg_bin = r"C:\ffmpeg\bin"
        if "ffmpeg" not in os.environ.get("PATH", "").lower():
            os.environ["PATH"] += os.pathsep + ffmpeg_bin
            
        cmd = [
            sys.executable, "-m", "yt_dlp",
            "-x", "--audio-format", "mp3",
            "-o", str(out_path.with_suffix('')),
            BGM_YOUTUBE_URL
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
