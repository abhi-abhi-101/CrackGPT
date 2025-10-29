# helpers/transcribe.py
def transcribe_file(tmp_file_path, hf_token):
    """
    Returns (transcription_string or None, error_message or None)
    """
    try:
        from faster_whisper import WhisperModel
    except Exception as e:
        return None, f"Import error: {e}"

    try:
        whisper_model = WhisperModel(
            model_size_or_path="tiny.en",
            device="cpu",
            use_auth_token=hf_token
        )
        segments, _ = whisper_model.transcribe(tmp_file_path)
        transcription = " ".join([seg.text for seg in segments])
        return transcription, None
    except Exception as e:
        return None, f"Transcription error: {e}"
