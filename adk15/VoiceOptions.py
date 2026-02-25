"""
VoiceOptions.py
Single-Speaker TTS Demo
Speaks each voice individually and saves as WAV files
"""

import os
import wave
from google import genai
from google.genai import types
from config import config

# -----------------------------
# Configuration
# -----------------------------
os.environ["GOOGLE_API_KEY"] = config.GOOGLE_API_KEY.strip()
TTS_MODEL = "gemini-2.5-flash-preview-tts"

# List of 30 available voices
voice_names = [
    "Zephyr", "Puck", "Charon", "Kore", "Fenrir", "Leda",
    "Orus", "Aoede", "Callirrhoe", "Autonoe", "Enceladus", "Iapetus",
    "Umbriel", "Algieba", "Despina", "Erinome", "Algenib", "Rasalgethi",
    "Laomedeia", "Achernar", "Alnilam", "Schedar", "Gacrux", "Pulcherrima",
    "Achird", "Zubenelgenubi", "Vindemiatrix", "Sadachbia", "Sadaltager", "Sulafat"
]

# -----------------------------
# Create folder
# -----------------------------
folder_name = "Voice Options"
os.makedirs(folder_name, exist_ok=True)

# -----------------------------
# Save WAV file
# -----------------------------
def save_wave(filename, pcm, channels=1, rate=24000, sample_width=2):
    with wave.open(filename, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(rate)
        wf.writeframes(pcm)

# -----------------------------
# Generate single-speaker TTS
# -----------------------------
def generate_tts(voice_name, client):
    print(f"🎤 Speaking with voice: {voice_name}")
    text = f"Hello, I am {voice_name}."

    response = client.models.generate_content(
        model=TTS_MODEL,
        contents=text,
        config=types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=voice_name
                    )
                )
            )
        )
    )

    # Correct path to audio bytes
    audio_data = response.candidates[0].content.parts[0].inline_data.data

    # Save file inside "Voice Options" folder
    filename = os.path.join(folder_name, f"{voice_name}.wav")
    save_wave(filename, audio_data)
    print(f"✅ Saved as: {filename}\n")

# -----------------------------
# Main function
# -----------------------------
def main():
    client = genai.Client()
    for voice in voice_names:
        generate_tts(voice, client)

if __name__ == "__main__":
    main()