"""FFmpeg: videos + audio + captions + BGM → vertical Short MP4 (9:16).

Effects:
  - Fadeblack crossfade between scenes (horror vibe)
  - Creepster font captions at the bottom
  - Auto-loops and crops horizontal videos to fit perfectly
  - Mixes scary background music with the voiceover
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FONTS_DIR = REPO_ROOT / "assets" / "fonts"
DEFAULT_FONT_FILE = "CreepsterCaps.ttf"
DEFAULT_FONT_NAME = "Creepster"

FPS = 30
FADE_DUR = 0.5


def render_vertical_short(
    video_paths: list[Path],
    total_duration: float,
    audio_path: Path,
    srt_path: Path,
    out_video: Path,
    *,
    bgm_path: Path | None = None,
    width: int = 1080,
    height: int = 1920,
    font_file: str = DEFAULT_FONT_FILE,
    font_name: str = DEFAULT_FONT_NAME,
) -> None:
    if not video_paths:
        raise ValueError("No videos")
    if not shutil.which("ffmpeg"):
        raise RuntimeError("ffmpeg not found; install it (brew install ffmpeg)")

    out_video = Path(out_video)
    out_video.parent.mkdir(parents=True, exist_ok=True)
    tmp = out_video.parent / f"_tmp_render_{out_video.stem}"
    tmp.mkdir(parents=True, exist_ok=True)

    n = len(video_paths)
    clip_dur = (total_duration + (n - 1) * FADE_DUR) / n if n > 1 else total_duration

    # ── 1. Format and Loop Video Clips ───────────────────────────────
    for i, src in enumerate(video_paths):
        clip = tmp / f"clip_{i + 1:02d}.mp4"
        
        vf = (f"scale={width}:{height}:force_original_aspect_ratio=increase,"
              f"crop={width}:{height},setsar=1,fps={FPS}")
              
        subprocess.run(
            [
                "ffmpeg", "-y", "-hide_banner", "-loglevel", "warning",
                "-stream_loop", "-1", "-i", str(src),
                "-t", f"{clip_dur:.4f}",
                "-vf", vf,
                "-c:v", "libx264", "-preset", "ultrafast", "-crf", "15",
                "-an", # Remove original audio from stock video
                str(clip),
            ],
            check=True,
        )

    # ── 2. Prepare subtitles + font ──────────────────────────────────
    shutil.copyfile(srt_path, tmp / "captions.srt")

    font_path = FONTS_DIR / font_file
    rendered_font_name = "Arial"
    fontsdir_arg = ""
    if font_path.is_file():
        font_dir = tmp / "_fonts"
        font_dir.mkdir(exist_ok=True)
        shutil.copyfile(font_path, font_dir / font_path.name)
        rendered_font_name = font_name
        fontsdir_arg = ":fontsdir='_fonts'"
    else:
        print(f"   ⚠ Font {font_path} not found — using {rendered_font_name}")

    force_style = (
        f"FontName={rendered_font_name},"
        f"FontSize=18,"
        f"PrimaryColour=&H00FFFFFF,"
        f"OutlineColour=&H00000000,"
        f"BackColour=&H96000000,"
        f"BorderStyle=4,Outline=1,Bold=1,"
        f"Shadow=0,Alignment=2,"
        f"MarginV=15,MarginL=20,MarginR=20"
    )

    # ── 3. Build xfade chain + subtitles + audio mix ─────────────────
    inputs: list[str] = []
    for i in range(n):
        inputs += ["-i", f"clip_{i + 1:02d}.mp4"]
    
    inputs += ["-i", str(audio_path.resolve())]
    if bgm_path:
        # Re-loop the BGM in case it's shorter than the video
        inputs += ["-stream_loop", "-1", "-i", str(bgm_path.resolve())]

    filter_parts: list[str] = []

    # Visual filter chain
    if n == 1:
        filter_parts.append(
            f"[0:v]subtitles=captions.srt{fontsdir_arg}:"
            f"force_style='{force_style}'[v_final]"
        )
    else:
        prev = "[0:v]"
        for i in range(n - 1):
            offset = (i + 1) * (clip_dur - FADE_DUR)
            next_v = f"[{i + 1}:v]"
            out = f"[x{i}]"
            filter_parts.append(
                f"{prev}{next_v}xfade=transition=fadeblack:"
                f"duration={FADE_DUR:.4f}:offset={offset:.4f}{out}"
            )
            prev = out
        filter_parts.append(
            f"{prev}subtitles=captions.srt{fontsdir_arg}:"
            f"force_style='{force_style}'[v_final]"
        )
        
    # Audio filter chain
    voice_in = f"[{n}:a]"
    if bgm_path:
        bgm_in = f"[{n+1}:a]"
        filter_parts.append(f"{voice_in}volume=1.5[v1];{bgm_in}volume=0.15[v2];[v1][v2]amix=inputs=2:duration=first:dropout_transition=2[a_final]")
        audio_map = ["[a_final]"]
    else:
        audio_map = [voice_in]

    fc = ";\n".join(filter_parts)

    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "warning",
        *inputs,
        "-filter_complex", fc,
        "-map", "[v_final]", "-map", audio_map[0],
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest",
        "-movflags", "+faststart",
        str(out_video.resolve()),
    ]
    subprocess.run(cmd, check=True, cwd=str(tmp))

    # ── cleanup ──────────────────────────────────────────────────────
    shutil.rmtree(tmp, ignore_errors=True)
