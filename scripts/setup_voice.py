import os
from fishaudio import FishAudio

# 1. Initialize the client (You can get a free starting API key from fish.audio)
# For completely free local computing, you can also download their local weights from GitHub.
client = FishAudio(api_key="84e54f3d7bd2483f8f1866f7037c5f58")

print("Uploading and cloning your voice sample...")

# 2. Create the permanent voice clone
with open("my_voice.wav", "rb") as f:
    voice = client.voices.create(
        title="YouTube Shorts Voice",
        voices=[f.read()],
        description="My custom voice clone optimized for automated Reels",
        enhance_audio_quality=True # Automatically strips out tiny background hisses
    )

# 3. Print your unique ID
print(f"Success! Your reusable Voice ID is: {voice.id}")
print(f"Current State: {voice.state}")