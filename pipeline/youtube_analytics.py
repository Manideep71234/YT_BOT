import os
from googleapiclient.discovery import build
from pipeline.youtube_upload import _get_creds

def get_authenticated_service(refresh_token_env="YT_REFRESH_TOKEN"):
    """Authenticates using the existing credentials logic and returns a youtube service object."""
    creds = _get_creds(refresh_token_env)
    return build('youtube', 'v3', credentials=creds)

def get_channel_stats(youtube):
    """Fetches stats for the authenticated channel."""
    # mine=True gets the authenticated user's channel
    response = youtube.channels().list(
        part="statistics,id",
        mine=True
    ).execute()
    
    if response.get("items"):
        return response["items"][0]["statistics"], response["items"][0]["id"]
    return {}, None

def get_top_videos(youtube, limit=5):
    """Fetches the top performing recent videos from the authenticated channel."""
    response = youtube.channels().list(part="contentDetails", mine=True).execute()
    
    if not response.get("items"):
        return []
        
    uploads_id = response["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]

    # Get recent videos (up to 50 to analyze)
    playlist_response = youtube.playlistItems().list(
        part="snippet",
        playlistId=uploads_id,
        maxResults=50
    ).execute()

    video_ids = [item["snippet"]["resourceId"]["videoId"] for item in playlist_response.get("items", [])]
    
    if not video_ids:
        return []

    # Get stats for those videos
    videos_response = youtube.videos().list(
        part="snippet,statistics",
        id=",".join(video_ids)
    ).execute()

    videos = []
    for item in videos_response.get("items", []):
        videos.append({
            "title": item["snippet"]["title"],
            "description": item["snippet"]["description"],
            "views": int(item["statistics"].get("viewCount", 0)),
            "likes": int(item["statistics"].get("likeCount", 0)),
            "comments": int(item["statistics"].get("commentCount", 0))
        })
        
    # Sort by views descending
    videos.sort(key=lambda x: x["views"], reverse=True)
    return videos[:limit]

