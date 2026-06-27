#!/usr/bin/env python3
"""
Fully automated YouTube Short pipeline.

Single-variant flow:
  Groq → narration + image prompts
  Edge TTS → audio (30-40s)
  DeAPI → images
  Captions → SRT
  FFmpeg → 9:16 vertical MP4
  YouTube upload (optional)

Bilingual flow (preset has `variants`):
  Groq → image_prompts + per-language {title, description, narration}
  DeAPI → images (once, shared)
  For each variant:
    Edge TTS → audio in that language with that voice
    Captions → SRT
    FFmpeg → MP4 with variant-specific font
    YouTube upload (optional, per-channel token)

Usage:
  .venv/bin/python scripts/run_short.py --channel ghost_stories
  .venv/bin/python scripts/run_short.py --channel facts --upload --privacy public
  .venv/bin/python scripts/run_short.py --channel hindi_myth
  # hindi_myth: topic = IST day theme (Ganesha→Shiva→…) + random unused line; --topic overrides
"""
from __future__ import annotations

import argparse
import json
import os

# Ensure local ffmpeg is in PATH
ffmpeg_bin = os.path.join(os.path.expanduser("~"), "ffmpeg", "bin")
if ffmpeg_bin not in os.environ.get("PATH", ""):
    os.environ["PATH"] = ffmpeg_bin + os.pathsep + os.environ.get("PATH", "")

import random
import sys

# Force UTF-8 for Windows consoles to avoid charmap encode errors
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8')

import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path


from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
load_dotenv(REPO_ROOT / ".env")
load_dotenv(REPO_ROOT / "scripts" / ".env")

from pipeline.captions import build_srt
from pipeline.channel_presets import get_preset, list_channel_ids
from pipeline.voice_gen import synthesize_full
from pipeline.groq_script import generate_short_pack
from pipeline.videos import fetch_scene_video
from pipeline.bgm import ensure_bgm_downloaded
from pipeline.render_short import render_vertical_short
from pipeline.story_history import save_title
from pipeline.youtube_analytics import get_authenticated_service, get_top_videos



def _render_and_upload(
    *,
    variant_label: str,
    narration: str,
    title: str,
    description: str,
    voice: str | None,
    font_file: str,
    font_name: str,
    image_paths: list,
    run_dir: Path,
    suffix: str,
    upload: bool,
    upload_ig: bool,
    privacy: str,
    yt_token_env: str = "YT_REFRESH_TOKEN",
) -> Path:

    """Render one video (audio + SRT + MP4) for a single variant. Optionally upload."""
    print(f"\n━━━ Variant: {variant_label} ━━━")

    audio_path = run_dir / f"voiceover{suffix}.mp3"
    print(f"② FishAudio TTS…")
    lang = suffix.strip("_") if suffix else None
    total_dur, sentence_timings = synthesize_full(narration, audio_path, voice=voice, lang=lang)
    print(f"   Audio: {total_dur:.1f}s ({len(sentence_timings)} sentences tracked)")
    if total_dur > 55:
        print(f"   ⚠ Audio is {total_dur:.0f}s — target is 30-45s")
    if total_dur < 25:
        print(f"   ⚠ Audio is {total_dur:.0f}s — might be too short")

    srt_path = run_dir / f"captions{suffix}.srt"
    print("④ Captions…")
    build_srt(sentence_timings, srt_path, total_dur)

    video_path = run_dir / f"short{suffix}.mp4"
    print(f"⑤ FFmpeg: rendering 1080×1920 (font={font_name})…")
    
    # Fetch BGM
    bgm_path = run_dir / "bgm.mp3"
    
    render_vertical_short(
        image_paths, total_dur, audio_path, srt_path, video_path,
        bgm_path=bgm_path,
        font_file=font_file, font_name=font_name,
    )
    print(f"   → {video_path}")

    if upload:
        try:
            from pipeline.youtube_upload import upload_short
            print(f"⑥ YouTube: uploading ({yt_token_env})…")
            vid = upload_short(
                video_path, title, description,
                privacy_status=privacy,
                refresh_token_env=yt_token_env,
            )
            print(f"   Uploaded! https://www.youtube.com/shorts/{vid}")
            
            try:
                from pipeline.notifications import send_whatsapp_message, send_telegram_message, send_email_notification
                msg = f"✅ YouTube Shorts Pipeline — Published!\n\n📽️ Title: {title}\n🔗 URL: https://www.youtube.com/shorts/{vid}"
                html_msg = f"✅ <b>YouTube Shorts Pipeline — Published!</b>\n\n📽️ <b>Title:</b> {title}\n🔗 <b>URL:</b> https://www.youtube.com/shorts/{vid}"
                
                send_whatsapp_message(msg)
                send_telegram_message(html_msg)
                send_email_notification(f"✅ Video Uploaded: {title}", msg)
            except Exception as notify_err:
                print(f"   ⚠ Failed to send notifications: {notify_err}")

        except Exception as e:
            print(f"   ❌ YouTube Upload Failed: {e}")
            print(f"   Video is saved locally at: {video_path}")
            
            try:
                from pipeline.notifications import send_whatsapp_message, send_telegram_message, send_email_notification
                msg = f"❌ YouTube Shorts Pipeline — FAILED!\n\n📽️ Title: {title}\n⚠ Error: {e}"
                html_msg = f"❌ <b>YouTube Shorts Pipeline — FAILED!</b>\n\n📽️ <b>Title:</b> {title}\n⚠ <b>Error:</b> {e}"
                
                send_whatsapp_message(msg)
                send_telegram_message(html_msg)
                send_email_notification(f"❌ Upload Failed: {title}", msg)
            except Exception:
                pass
                
            raise  # Re-raise so the thread/script actually fails
    else:
        print("   (skip YouTube upload — pass --upload)")

    if upload_ig:
        try:
            from pipeline.instagram_upload import upload_instagram_reel
            print(f"⑦ Instagram: uploading…")
            # Create a suitable caption for IG
            ig_caption = f"{title}\n\n{description}\n\n#reels #shorts"
            ig_id = upload_instagram_reel(video_path, ig_caption)
            print(f"   Uploaded to Instagram! Post ID: {ig_id}")
        except Exception as e:
            print(f"   ❌ Instagram Upload Failed: {e}")
            print(f"   Video is saved locally at: {video_path}")
    else:
        print("   (skip Instagram upload — pass --upload-ig)")

    return video_path



def main() -> None:
    ap = argparse.ArgumentParser(description="Generate & optionally upload a YouTube Short.")
    ap.add_argument("--channel", required=True, choices=list_channel_ids())
    ap.add_argument("--topic", default="", help="Optional topic hint for Groq.")
    ap.add_argument("--upload", action="store_true", help="Upload to YouTube after render.")
    ap.add_argument("--upload-ig", action="store_true", help="Upload to Instagram Reels after render.")
    ap.add_argument("--privacy", default="private", choices=["private", "unlisted", "public"])

    args = ap.parse_args()

    preset = get_preset(args.channel)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    run_dir = REPO_ROOT / "output" / "runs" / f"{args.channel}_{ts}"
    img_dir = run_dir / "images"
    img_dir.mkdir(parents=True, exist_ok=True)

    # Myth rotation: IST calendar picks theme (Ganesha → Shiva → …); random unused topic in that theme.
    myth_theme_for_commit: str | None = None
    myth_topic_for_commit: str | None = None

    # Pick a topic: CLI --topic wins; else performance-based; else myth rotation; else random from topic_pool.
    topic_hint = args.topic.strip() or None
    if not topic_hint:
        try:
            print("📊 Fetching channel analytics to find top-performing video...")
            yt_token_env = preset.get("yt_token_env") or "YT_REFRESH_TOKEN"
            if preset.get("variants"):
                yt_token_env = preset["variants"][0].get("yt_token_env", "YT_REFRESH_TOKEN")
            
            youtube = get_authenticated_service(yt_token_env)
            top_videos = get_top_videos(youtube, limit=3)
            if top_videos:
                # Pick a random video from the top 3 to avoid creating the EXACT same topic every time
                inspiration = random.choice(top_videos)
                print(f"📈 Found inspiration! Top video: '{inspiration['title']}' ({inspiration['views']} views)")
                topic_hint = f"Make a story similar to our top performing video: '{inspiration['title']}'. It was about: {inspiration['description']}"
            else:
                print("⚠️ No top videos found (or channel empty). Falling back to presets.")
        except Exception as e:
            print(f"⚠️ Failed to fetch channel analytics: {e}. Falling back to presets.")

    if not topic_hint:
        if preset.get("topic_rotation") == "myth":
            from pipeline.myth_topics import pick_myth_topic

            topic_hint, myth_theme_for_commit = pick_myth_topic(args.channel)
            myth_topic_for_commit = topic_hint
            print(f"📿 Myth theme today (IST): {myth_theme_for_commit} → {topic_hint!r}")
        else:
            pool = preset.get("topic_pool") or []
            if pool:
                topic_hint = random.choice(pool)
                print(f"🎲 Random topic from pool: {topic_hint!r}")

    variants = preset.get("variants") or []
    primary_video_path: Path | None = None

    # ── 1. Script via Groq ───────────────────────────────────────────
    print("① Groq: generating script…")
    pack = generate_short_pack(
        preset, topic_hint=topic_hint, channel_id=args.channel,
    )
    (run_dir / "script.json").write_text(json.dumps(pack, indent=2, ensure_ascii=False), encoding="utf-8")

    image_prompts = pack["image_prompts"]

    if variants:
        # Bilingual mode: each lang gets its own audio/SRT/video
        first_v = variants[0]
        first_node = pack["variants"][first_v["lang"]]
        print(f"   Title ({first_v['label']}): {first_node['youtube_title']}")
        for v in variants:
            node = pack["variants"][v["lang"]]
            wc = len(node["full_narration"].split())
            print(f"   {v['label']}: {wc} words")
        print(f"   {len(image_prompts)} image prompts (shared)")
        history_title = first_node["youtube_title"]
        history_narration = first_node["full_narration"]
    else:
        title = pack["youtube_title"]
        narration = pack["full_narration"]
        word_count = len(narration.split())
        print(f"   Title: {title}")
        print(f"   Narration: {word_count} words, {len(image_prompts)} image prompts")
        history_title = title
        history_narration = narration

    # ── 2. Images via DeAPI (generated ONCE, shared by all variants) ──
    w = int(os.environ.get("DEAPI_IMAGE_WIDTH", "768"))
    h = int(os.environ.get("DEAPI_IMAGE_HEIGHT", "768"))
    style_suffix = preset.get("image_style_suffix")

    # ── 2. Videos via Pexels (generated ONCE, shared by all variants) ──
    n_prompts = len(image_prompts)
    print(f"③ Videos: {n_prompts} scenes…")
    image_paths: list[Path] = []
    style = preset.get("image_style_suffix", "")

    for i, p in enumerate(image_prompts):
        v_path = img_dir / f"scene_{i + 1:02d}.mp4"
        print(f"   scene {i + 1}/{n_prompts}: video")
        
        # Combine prompt with style suffix for Pexels search query
        fetch_scene_video(p + style, v_path)
        image_paths.append(v_path)

    # ── 3.5 Fetch BGM (Shared across variants) ───────────────────────
    bgm_path = run_dir / "bgm.mp3"
    print("   [bgm] Fetching background music...")
    ensure_bgm_downloaded(bgm_path)

    # ── 4-6. Render (per variant) ────────────────────────────────────
    if variants:
        print("④-⑥ Rendering variants in parallel…")
        with ThreadPoolExecutor(max_workers=min(len(variants), 4)) as executor:
            futures = []
            for v in variants:
                node = pack["variants"][v["lang"]]
                futures.append(executor.submit(
                    _render_and_upload,
                    variant_label=v["label"],
                    narration=node["full_narration"],
                    title=node["youtube_title"],
                    description=node.get("youtube_description", ""),
                    voice=v.get("tts_voice"),
                    font_file=v.get("caption_font", "CreepsterCaps.ttf"),
                    font_name=v.get("caption_font_name", "Creepster"),
                    image_paths=image_paths,
                    run_dir=run_dir,
                    suffix=f"_{v['lang']}",
                    upload=args.upload,
                    upload_ig=args.upload_ig,
                    privacy=args.privacy,
                    yt_token_env=v.get("yt_token_env", "YT_REFRESH_TOKEN"),
                ))
            
            # Wait for all to complete
            for future in futures:
                try:
                    future.result()
                except Exception as e:
                    print(f"❌ Variant rendering failed: {e}")
                    import sys
                    sys.exit(1)
    else:

        primary_video_path = _render_and_upload(
            variant_label=preset.get("language", "en"),
            narration=narration,
            title=title,
            description=pack.get("youtube_description", ""),
            voice=preset.get("tts_voice") or os.environ.get("EDGE_TTS_VOICE"),
            font_file=preset.get("caption_font", "CreepsterCaps.ttf"),
            font_name=preset.get("caption_font_name", "Creepster"),
            image_paths=image_paths,
            run_dir=run_dir,
            suffix="",
            upload=args.upload,
            upload_ig=args.upload_ig,
            privacy=args.privacy,
            yt_token_env=preset.get("yt_token_env") or "YT_REFRESH_TOKEN",
        )


    # ── 7. History ───────────────────────────────────────────────────
    summary = " ".join(history_narration.split()[:25]) + "…"
    save_title(args.channel, history_title, summary)

    if myth_theme_for_commit and myth_topic_for_commit:
        from pipeline.myth_topics import commit_myth_topic

        commit_myth_topic(args.channel, myth_theme_for_commit, myth_topic_for_commit)

    # Optional second upload: same rendered MP4 to extra channels (e.g. second bhakti channel).
    # Uses env var names listed in preset["extra_yt_token_envs"].
    extra_envs = preset.get("extra_yt_token_envs") or []
    if args.upload and primary_video_path and extra_envs:
        from pipeline.youtube_upload import upload_short

        for env_name in extra_envs:
            print(f"⑦ Extra YouTube upload ({env_name})…")
            vid_extra = upload_short(
                primary_video_path,
                history_title,
                pack.get("youtube_description", ""),
                privacy_status=args.privacy,
                refresh_token_env=env_name,
            )
            print(f"   Extra channel video: https://www.youtube.com/shorts/{vid_extra}")

    print("\n✓ Done.")


if __name__ == "__main__":
    main()
