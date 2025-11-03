# helpers/eleven.py
import requests

def fetch_elevenlabs_voices(api_key):
    try:
        url = "https://api.elevenlabs.io/v1/voices"
        headers = {"xi-api-key": api_key}
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, dict):
                return data.get("voices", []) or []
            return []
        else:
            return []
    except Exception:
        return []

def tts_audio_bytes(api_key, voice_id, text):
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "Accept": "audio/wav",
        "Content-Type": "application/json",
        "xi-api-key": api_key
    }
    payload = {"text": text, "model": "eleven_monolingual_v1"}
    resp = requests.post(url, json=payload, headers=headers, timeout=30)
    if resp.status_code == 200:
        return resp.content
    else:
        raise Exception(f"ElevenLabs TTS failed: {resp.status_code} {resp.text}")
