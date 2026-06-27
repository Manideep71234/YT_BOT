"""Voice generation using FishAudio and sync via faster-whisper.

Provides a drop-in replacement signature for synthesize_full().
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import TypedDict

class SentenceTiming(TypedDict):
    text: str
    offset_ms: int
    duration_ms: int


def _ffprobe_duration(path: Path) -> float:
    out = subprocess.check_output(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        text=True,
    ).strip()
    return float(out)


def synthesize_full(
    text: str, out_path: Path, voice: str | None = None, lang: str | None = None
) -> tuple[float, list[SentenceTiming]]:
    """TTS the full narration using FishAudio and align with faster-whisper."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    
    if lang == "te":
        print(f"   [voice] Generating via Edge TTS (native Telugu: {voice or 'te-IN-ShrutiNeural'})...")
        import subprocess
        subprocess.run([
            "edge-tts", 
            "--voice", voice or "te-IN-ShrutiNeural", 
            "--text", text, 
            "--write-media", str(out_path)
        ], check=True)
    else:
        # 1. Generate audio using FishAudio
        from fishaudio import FishAudio
        from fishaudio.utils import save
        
        # Fallback to defaults from bot.py
        FISH_API_KEY = os.environ.get("FISH_API_KEY", "84e54f3d7bd2483f8f1866f7037c5f58")
        FISH_VOICE_ID = os.environ.get("FISH_VOICE_ID", "9c335d29248c49c9960e13b0b8b3ee6d")
        
        print(f"   [voice] Generating via FishAudio (Voice ID: {FISH_VOICE_ID})...")
        client = FishAudio(api_key=FISH_API_KEY)
        
        audio = client.tts.convert(
            text=text,
            reference_id=FISH_VOICE_ID,
            model="s2.1-pro-free",
            speed=1.0
        )
        save(audio, str(out_path))
    
    dur = _ffprobe_duration(out_path)
    
    # 2. Extract word-level timestamps using faster-whisper
    print("   [voice] Aligning audio with faster-whisper...")
    from faster_whisper import WhisperModel
    model = WhisperModel("small", device="cpu", compute_type="int8")
    
    # Provide the text as initial_prompt to heavily bias the model towards outputting the actual script
    # pass language explicitly to avoid auto-detect issues with short clips
    transcribe_kwargs = {
        "beam_size": 1,
        "word_timestamps": True,
        "language": lang
    }
    
    if lang == "te":
        transcribe_kwargs["task"] = "translate"
    else:
        transcribe_kwargs["initial_prompt"] = text[:1000]

    segments, info = model.transcribe(str(out_path), **transcribe_kwargs)
    
    words = []
    for seg in segments:
        if seg.words:
            words.extend(seg.words)
            
    # 3. Group into short chunks (SentenceTiming) to match short-style subs
    sentences: list[SentenceTiming] = []
    chunk = []
    CHUNK_SIZE = 3
    
    for w in words:
        chunk.append(w)
        if len(chunk) == CHUNK_SIZE:
            start_ms = int(chunk[0].start * 1000)
            end_ms = int(chunk[-1].end * 1000)
            chunk_text = " ".join(x.word.strip() for x in chunk)
            
            sentences.append(
                SentenceTiming(
                    text=chunk_text,
                    offset_ms=start_ms,
                    duration_ms=end_ms - start_ms,
                )
            )
            chunk = []
            
    if chunk:
        start_ms = int(chunk[0].start * 1000)
        end_ms = int(chunk[-1].end * 1000)
        chunk_text = " ".join(x.word.strip() for x in chunk)
        sentences.append(
            SentenceTiming(
                text=chunk_text,
                offset_ms=start_ms,
                duration_ms=end_ms - start_ms,
            )
        )
        
    return dur, sentences
