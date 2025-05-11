# src/transcriber/google_recognizer.py
import speech_recognition as sr  # Asegúrate de que SpeechRecognition esté instalado
import logging
from .speech_recognition_factory import SpeechRecognizer  # Importar la interfaz base

logger = logging.getLogger(__name__)


class GoogleRecognizer(SpeechRecognizer):
    """
    Reconocedor de voz que utiliza la API de Google Web Speech.
    Requiere conexión a internet.
    """

    def __init__(self):
        """Inicializa el reconocedor de Google."""
        self.recognizer = sr.Recognizer()
        # Puedes ajustar parámetros del reconocedor aquí si es necesario
        # self.recognizer.energy_threshold = 4000
        # self.recognizer.dynamic_energy_threshold = True
        # self.recognizer.operation_timeout = 5 # segundos
        logger.info("GoogleRecognizer inicializado.")

    def recognize(self, audio_file_path: str, language: str = "es-ES") -> str:
        """
        Transcribe un archivo de audio usando la API de Google.

        Args:
            audio_file_path: Ruta al archivo de audio (preferiblemente WAV).
            language: Código de idioma (ej. "es-ES", "en-US").

        Returns:
            str: El texto transcrito. Retorna cadena vacía si no se detecta voz o hay error.

        Raises:
            sr.UnknownValueError: Si la API no puede entender el audio.
            sr.RequestError: Si hay un problema con la solicitud a la API.
            Exception: Para otros errores (ej. archivo no encontrado).
        """
        logger.info(
            f"Iniciando reconocimiento con Google para {audio_file_path} en idioma {language}...")
        try:
            with sr.AudioFile(audio_file_path) as source:
                # Ajustar para ruido ambiental y energía si es necesario
                # self.recognizer.adjust_for_ambient_noise(source, duration=5)
                # Leer el archivo de audio completo
                audio_data = self.recognizer.record(source)

            # Usar recognize_google para transcribir
            text = self.recognizer.recognize_google(
                audio_data, language=language)
            logger.info("Reconocimiento con Google completado.")
            return text

        except sr.UnknownValueError:
            logger.warning("Google Web Speech API no pudo entender el audio.")
            # No relanzamos, simplemente retornamos vacío para fragmentos sin voz
            return ""
        except sr.RequestError as e:
            logger.error(f"Error de solicitud a Google Web Speech API; {e}")
            # Relanzamos RequestError ya que es un problema con la API
            raise sr.RequestError(
                f"Error de solicitud a Google API: {e}") from e
        except FileNotFoundError:
            logger.error(f"Archivo de audio no encontrado: {audio_file_path}")
            raise FileNotFoundError(
                f"Archivo de audio no encontrado: {audio_file_path}")
        except Exception as e:
            logger.error(
                f"Error inesperado durante el reconocimiento con Google: {e}")
            # Relanzamos cualquier otro error inesperado
            raise Exception(
                f"Error inesperado en GoogleRecognizer: {e}") from e
