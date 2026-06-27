"""Fetch stock videos for backgrounds.

Uses Pexels API if PEXELS_API_KEY is provided.
Otherwise, falls back to downloading a random segment from a royalty-free creepy looping YouTube video.
"""
from __future__ import annotations

import os
import random
import subprocess
from pathlib import Path

import requests

FALLBACK_CREEPY_VIDEOS = [
    "https://www.youtube.com/watch?v=Fj-V7e3jAms", # royalty free scary fog looping
    "https://www.youtube.com/watch?v=kY31RzB227Q",
    "https://www.youtube.com/watch?v=0hYV_Xm7rXY",
]

def _fetch_pexels(query: str, out_path: Path, api_key: str) -> Path:
    # Clean up the query
    query = query.replace(" (Pexels video search query)", "").strip()
    # Pexels usually likes short keywords (e.g. "dark forest", "creepy house")
    words = [w for w in query.split() if w.lower() not in ("a", "the", "in", "of", "on", "at")]
    short_query = " ".join(words[:4])
    
    url = f"https://api.pexels.com/videos/search?query={short_query}&per_page=15&orientation=portrait"
    headers = {"Authorization": api_key}
    
    print(f"      [video] Searching Pexels for: '{short_query}'...")
    res = requests.get(url, headers=headers, timeout=15)
    res.raise_for_status()
    data = res.json()
    
    videos = data.get("videos", [])
    if not videos:
        print(f"      [video] No Pexels results for '{short_query}'. Using fallback.")
        return _fetch_fallback_youtube(out_path)
        
    # Pick a random video from top results
    video = random.choice(videos[:5])
    # Get highest quality HD video file
    files = video.get("video_files", [])
    files.sort(key=lambda x: (x.get("width", 0) * x.get("height", 0)), reverse=True)
    
    download_link = files[0]["link"]
    print(f"      [video] Downloading Pexels video (ID: {video['id']})...")
    
    video_data = requests.get(download_link, timeout=60).content
    with open(out_path, "wb") as f:
        f.write(video_data)
        
    return out_path


def _fetch_fallback_ffmpeg(out_path: Path) -> Path:
    """Generates a synthetic creepy film grain background using FFmpeg."""
    if not os.path.exists(out_path):
        print("      [video] Generating synthetic spooky background using FFmpeg...")
        
        # Ensure ffmpeg is in PATH
        if "ffmpeg" not in os.environ.get("PATH", "").lower():
            if os.name == 'nt':
                os.environ["PATH"] += os.pathsep + r"C:\ffmpeg\bin"
            
        cmd = [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "warning",
            "-f", "lavfi",
            "-i", "color=c=darkred:s=1080x1920:d=10",
            "-vf", "noise=alls=15:allf=t+u, vignette=PI/4",
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
            "-pix_fmt", "yuv420p",
            str(out_path)
        ]
        
        try:
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError as e:
            print(f"      [video] WARNING: FFmpeg fallback failed: {e}")
            
    return out_path


def fetch_scene_video(prompt: str, out_path: Path) -> Path:
    """Gets a video for the scene, returns the path to the saved .mp4."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    
    api_key = os.environ.get("PEXELS_API_KEY", "").strip()
    
    if api_key:
        try:
            return _fetch_pexels(prompt, out_path, api_key)
        except Exception as e:
            print(f"      [video] Pexels API failed: {e}")
            return _fetch_fallback_ffmpeg(out_path)
    else:
        return _fetch_fallback_ffmpeg(out_path)
