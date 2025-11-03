# helpers/google_tts.py
import requests
import os
import base64

def tts_audio_bytes(text, api_key=None, voice_name="en-US-Wavenet-D", ssml=False):
    """
    Generate high-quality speech audio using Google Cloud TTS (WaveNet).
    Adds natural pacing, tone, and device profile for smoother sound.
    """
    if api_key is None:
        api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("Google API key not found. Please set GOOGLE_API_KEY in .env")

    url = f"https://texttospeech.googleapis.com/v1/text:synthesize?key={api_key}"

    # --- Fine-tuning parameters for more natural sound ---
    data = {
        "input": {"ssml": text} if ssml else {"text": text},
        "voice": {
            "languageCode": "en-US",
            "name": voice_name  # Keep WaveNet voice
        },
        "audioConfig": {
            "audioEncoding": "MP3",
            "speakingRate": 0.92,            # Slightly slower (more natural)
            "pitch": -1.2,                   # Softer tone
            "effectsProfileId": ["headphone-class-device"],  # Fuller sound
            "volumeGainDb": 0.0              # Keep neutral gain
        }
    }

    response = requests.post(url, json=data)
    result = response.json()

    if "audioContent" in result:
        return base64.b64decode(result["audioContent"])
    else:
        raise Exception(result.get("error", "Unknown error"))