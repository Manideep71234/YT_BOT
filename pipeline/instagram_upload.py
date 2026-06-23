"""Upload MP4 to Instagram Reels via instagrapi."""
import os
from pathlib import Path

try:
    from instagrapi import Client
except ImportError:
    Client = None

def upload_instagram_reel(video_path: Path, caption: str) -> str:
    """Uploads a video to Instagram Reels.
    
    Requires IG_USERNAME and IG_PASSWORD to be set in environment.
    """
    if Client is None:
        raise ImportError("instagrapi is not installed. Please install it using 'pip install instagrapi'")

    username = os.environ.get("IG_USERNAME", "").strip()
    password = os.environ.get("IG_PASSWORD", "").strip()

    if not username or not password:
        raise ValueError("IG_USERNAME and IG_PASSWORD environment variables must be set.")

    cl = Client()
    
    # Optional: Delay logic or proxy setting could be added here to avoid bans
    print(f"Logging into Instagram as {username}...")
    try:
        cl.login(username, password)
    except Exception as e:
        raise RuntimeError(f"Instagram login failed: {e}")

    print(f"Uploading Reel to Instagram: {video_path}")
    try:
        media = cl.clip_upload(str(video_path), caption)
        return media.pk
    except Exception as e:
        raise RuntimeError(f"Instagram upload failed: {e}")
