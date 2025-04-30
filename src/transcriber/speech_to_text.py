import speech_recognition as sr


class SpeechToText:
    def __init__(self):
        self.recognizer = sr.Recognizer()

    def convert_to_text(self, audio_path, language='es-ES'):
        try:
            with sr.AudioFile(audio_path) as source:
                audio = self.recognizer.record(source)
                text = self.recognizer.recognize_google(
                    audio, language=language)
                return text
        except sr.UnknownValueError:
            return "No se pudo entender el audio"
        except sr.RequestError as e:
            return f"Error en el servicio de reconocimiento: {str(e)}"
        except Exception as e:
            return f"Error: {str(e)}"
