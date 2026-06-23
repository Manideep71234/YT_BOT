#!/usr/import/env python3
"""Weekly Report generation and notification script for Youtube_bot."""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
load_dotenv(REPO_ROOT / ".env")
load_dotenv(REPO_ROOT / "scripts" / ".env")

import google.generativeai as genai
from pipeline.youtube_analytics import get_authenticated_service, get_channel_stats, get_top_videos
from pipeline.notifications import send_email_notification, send_whatsapp_message, send_telegram_message

def generate_report(stats, top_videos):
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    videos_data = "\n".join([f"- {v['title']} (Views: {v['views']}, Likes: {v['likes']})" for v in top_videos])
    
    prompt = f"""
    You are an expert YouTube Channel Analyst. Analyze the performance of this channel.
    
    Channel Lifetime Stats:
    - Total Views: {stats.get('viewCount')}
    - Total Subscribers: {stats.get('subscriberCount')}
    - Total Videos: {stats.get('videoCount')}
    
    Top Recent Videos (by views):
    {videos_data}
    
    Write a weekly performance report email. Include:
    1. A brief summary of channel growth.
    2. An analysis of the most seen topics based on the top videos.
    3. Recommendations for next week's content based on what's working.
    
    Keep it professional, encouraging, and easy to read.
    """
    
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"Error generating report: {e}")
        return "Error generating the AI report."

def main():
    print("Generating Weekly Report...")
    # Defaulting to the primary refresh token if not specified
    youtube = get_authenticated_service("YT_REFRESH_TOKEN")
    
    stats, channel_id = get_channel_stats(youtube)
    top_videos = get_top_videos(youtube, limit=10)
    
    if not top_videos:
        print("No videos found to generate a report.")
        return

    report_text = generate_report(stats, top_videos)
    
    print("Sending notifications...")
    send_email_notification("📈 Your Weekly YouTube Performance Report", report_text)
    
    # Send a short WhatsApp and Telegram summary
    wa_summary = f"📈 Weekly YouTube Report is ready!\n\nTop Video: {top_videos[0]['title']} ({top_videos[0]['views']} views).\n\nCheck your email for the full analysis of topics and languages!"
    send_whatsapp_message(wa_summary)
    send_telegram_message(f"📈 <b>Weekly YouTube Report is ready!</b>\n\nTop Video: {top_videos[0]['title']} ({top_videos[0]['views']} views).\n\n<i>Check your email for the full analysis of topics!</i>")
    
    print("Done!")

if __name__ == "__main__":
    main()
