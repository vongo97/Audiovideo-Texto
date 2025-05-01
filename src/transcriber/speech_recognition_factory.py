from abc import ABC, abstractmethod
import speech_recognition as sr
import whisper


class SpeechRecognizer(ABC):
    @abstractmethod
    def recognize(self, audio_path: str, language: str) -> str:
        pass


class GoogleRecognizer(SpeechRecognizer):
    def recognize(self, audio_path: str, language: str) -> str:
        recognizer = sr.Recognizer()
        with sr.AudioFile(audio_path) as source:
            audio = recognizer.record(source)
            return recognizer.recognize_google(audio, language=language)


class WhisperRecognizer(SpeechRecognizer):
    def recognize(self, audio_path: str, language: str) -> str:
        model = whisper.load_model("base")
        result = model.transcribe(audio_path)
        return result["text"]


class SpeechRecognizerFactory:
    @staticmethod
    def create_recognizer(recognizer_type: str) -> SpeechRecognizer:
        recognizers = {
            "google": GoogleRecognizer,
            "whisper": WhisperRecognizer
        }
        return recognizers.get(recognizer_type, GoogleRecognizer)()
