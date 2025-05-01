import speech_recognition as sr
import os


class SpeechToText:
    class TranscriptionError(Exception):
        """Error personalizado para problemas de transcripción"""
        pass

    def __init__(self):
        self.recognizer = sr.Recognizer()  # Inicializar en el constructor

    def convert_to_text(self, audio_path: str, language: str = 'es-ES') -> str:
        """
        Convierte un archivo de audio a texto.

        Args:
            audio_path: Ruta al archivo de audio
            language: Código del idioma (default: 'es-ES')

        Returns:
            str: Texto transcrito

        Raises:
            TranscriptionError: Si hay un error en la transcripción
        """
        try:
            with sr.AudioFile(audio_path) as source:
                audio = self.recognizer.record(source)
                text = self.recognizer.recognize_google(
                    audio, language=language)
                if not text:
                    raise self.TranscriptionError(
                        "No se detectó texto en el audio")
                return text
        except sr.UnknownValueError:
            raise self.TranscriptionError("No se pudo entender el audio")
        except sr.RequestError as e:
            raise self.TranscriptionError(
                f"Error en el servicio de Google: {str(e)}")
        except Exception as e:
            raise self.TranscriptionError(f"Error inesperado: {str(e)}")
