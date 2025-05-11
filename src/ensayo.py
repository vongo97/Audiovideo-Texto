import whisper
try:
    model = whisper.load_model("base")
    print("Whisper model loaded successfully outside the app.")
except Exception as e:
    print(
        f"Error loading Whisper model outside the app: {type(e).__name__} - {e}")
