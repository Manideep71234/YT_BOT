"""
voice_gen.py — Open-source TTS: Kokoro (primary) → Coqui TTS → edge-tts fallback
Kokoro: MIT-licensed, ElevenLabs-quality, no API key needed.
"""
import asyncio, json, os, sys
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

TTS_ENGINE = os.getenv("TTS_ENGINE", "fish")   # fish | kokoro | coqui | edge

def get_narration_text() -> str:
    with open("story.json") as f:
        story = json.load(f)
    return story["hook"] + " " + " ".join(story["script"])

# ── FishAudio TTS (custom voice clone) ───────────────────────────────────────
def synth_fish(text: str, out: str):
    try:
        from fishaudio import FishAudio
        from fishaudio.utils import save
        print("[voice] Using FishAudio TTS (custom voice clone)...")
        
        # Hardcoded from bot.py
        client = FishAudio(api_key="84e54f3d7bd2483f8f1866f7037c5f58")
        YOUR_VOICE_ID = "9c335d29248c49c9960e13b0b8b3ee6d"
        
        audio = client.tts.convert(
            text=text,
            reference_id=YOUR_VOICE_ID,
            model="s2.1-pro-free",
            speed=1.1
        )
        save(audio, out)
        print(f"[voice] FishAudio done -> {out}")
        return True
    except Exception as e:
        print(f"[voice] FishAudio failed: {e}")
        return False

# ── Kokoro TTS (best quality, MIT licence) ───────────────────────────────────
def synth_kokoro(text: str, out: str):
    try:
        # pyrefly: ignore [missing-import]
        from kokoro import KPipeline
        import soundfile as sf
        import numpy as np

        print("[voice] Using Kokoro TTS (af_heart voice)...")
        pipeline = KPipeline(lang_code="a")   # American English
        voice    = os.getenv("KOKORO_VOICE", "af_heart")  # warm female

        samples = []
        for _, _, audio in pipeline(text, voice=voice, speed=1.05, split_pattern=r'\n+'):
            samples.append(audio)

        full = np.concatenate(samples)
        sf.write(out.replace(".mp3", ".wav"), full, 24000)
        # Convert wav → mp3 with ffmpeg
        os.system(f"ffmpeg -y -i {out.replace('.mp3','.wav')} -b:a 128k {out} -loglevel quiet")
        Path(out.replace(".mp3",".wav")).unlink(missing_ok=True)
        print(f"[voice] Kokoro done -> {out}")
        return True
    except Exception as e:
        print(f"[voice] Kokoro failed: {e}")
        return False

# ── Coqui TTS (good quality, open-source) ───────────────────────────────────
def synth_coqui(text: str, out: str):
    try:
        # pyrefly: ignore [missing-import]
        from TTS.api import TTS
        print("[voice] Using Coqui TTS (jenny voice)...")
        tts = TTS("tts_models/en/jenny/jenny")
        tmp = out.replace(".mp3", ".wav")
        tts.tts_to_file(text=text, file_path=tmp)
        os.system(f"ffmpeg -y -i {tmp} -b:a 128k {out} -loglevel quiet")
        Path(tmp).unlink(missing_ok=True)
        print(f"[voice] Coqui done -> {out}")
        return True
    except Exception as e:
        print(f"[voice] Coqui failed: {e}")
        return False

# ── edge-tts fallback ────────────────────────────────────────────────────────
async def synth_edge(text: str, out: str):
    import edge_tts
    voice = os.getenv("TTS_VOICE", "en-US-AnaNeural")
    rate  = os.getenv("TTS_RATE",  "+5%")
    pitch = os.getenv("TTS_PITCH", "+10Hz")
    print(f"[voice] Using edge-tts fallback ({voice})...")
    for attempt in range(3):
        try:
            await edge_tts.Communicate(text, voice, rate=rate, pitch=pitch).save(out)
            print(f"[voice] edge-tts done -> {out}")
            return True
        except Exception as e:
            print(f"[voice] edge-tts attempt {attempt+1}: {e}")
            await asyncio.sleep(2)
    return False

# ── Main ─────────────────────────────────────────────────────────────────────
async def main():
    out  = "narration.mp3"
    
    text = get_narration_text()
    print(f"[voice] Text: {text[:80]}...")
    engine = TTS_ENGINE.lower()

    if engine == "fish":
        if not synth_fish(text, out):
            if not synth_kokoro(text, out):
                if not synth_coqui(text, out):
                    await synth_edge(text, out)
    elif engine == "kokoro":
        if not synth_kokoro(text, out):
            if not synth_coqui(text, out):
                await synth_edge(text, out)
    elif engine == "coqui":
        if not synth_coqui(text, out):
            await synth_edge(text, out)
    else:
        await synth_edge(text, out)

    if not Path(out).exists() or Path(out).stat().st_size < 1000:
        print("[voice] FATAL: narration.mp3 missing or empty."); sys.exit(1)

    # Copy to output dir
    out_dir = Path(os.getenv("OUTPUT_DIR","output"))
    out_dir.mkdir(parents=True, exist_ok=True)
    import shutil; shutil.copy(out, out_dir / "narration.mp3")

if __name__ == "__main__":
    asyncio.run(main())
