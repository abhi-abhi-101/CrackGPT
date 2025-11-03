# helpers/transcribe.py

# A list of common English filler words. You can add more if you like.
FILLER_WORDS = [
    "um", "umm", "ah", "ahh", "uh", "uhh",
    "like", "you know", "i mean", "so", "right",
    "basically", "actually", "literally", "i think"
]
# We'll check for variations, e.g., "um,"
FILLER_CHECK = tuple([f.lower() for f in FILLER_WORDS])

def transcribe_file(tmp_file_path):
    """
    Transcribes the audio file and counts filler words.
    Returns (transcription_string, filler_word_count, error_message)
    """
    try:
        from faster_whisper import WhisperModel
    except Exception as e:
        return None, 0, f"Import error: {e}"

    try:
        whisper_model = WhisperModel(
            model_size_or_path="tiny.en",
            device="cpu",
            local_files_only=False
        )
        
        # --- MODIFICATION: Enable word_timestamps ---
        segments, _ = whisper_model.transcribe(
            tmp_file_path, 
            word_timestamps=True
        )

        full_transcription = ""
        filler_count = 0
        
        for segment in segments:
            # Add segment text to the full transcription
            full_transcription += segment.text + " "
            
            # Iterate through each word in the segment
            for word in segment.words:
                # Clean the word (lowercase, remove punctuation)
                cleaned_word = word.word.lower().strip(" ,.?!")
                
                # Check if it's a filler word
                if cleaned_word in FILLER_CHECK:
                    filler_count += 1
        
        return full_transcription.strip(), filler_count, None

    except Exception as e:
        return None, 0, f"Transcription error: {e}"
