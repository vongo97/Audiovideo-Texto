# src/transcriber/whisper_recognizer.py
import whisper  # Asegúrate de que openai-whisper esté instalado
import logging
from .speech_recognition_factory import SpeechRecognizer  # Importar la interfaz base
import os  # Necesario para verificar si el archivo existe

logger = logging.getLogger(__name__)


class WhisperRecognizer(SpeechRecognizer):
    """
    Reconocedor de voz que utiliza el modelo local Whisper de OpenAI.
    No requiere conexión a internet después de descargar el modelo.
    """

    def __init__(self, model_name: str = "base"):
        """
        Inicializa el reconocedor de Whisper.

        Args:
            model_name: Nombre del modelo Whisper a cargar (ej. "base", "small", "medium", "large").
        """
        self.model_name = model_name
        self.model = None  # El modelo se carga bajo demanda en recognize

        logger.info(
            f"WhisperRecognizer inicializado. Modelo configurado: '{self.model_name}'.")

    def _load_model(self):
        """Carga el modelo Whisper si aún no está cargado."""
        if self.model is None:
            logger.info(
                f"Cargando modelo Whisper '{self.model_name}'. Esto puede tardar un poco...")
            try:
                self.model = whisper.load_model(self.model_name)
                logger.info(f"Modelo Whisper '{self.model_name}' cargado.")
            except Exception as e:
                logger.error(
                    f"Error al cargar el modelo Whisper '{self.model_name}': {e}")
                raise Exception(
                    f"No se pudo cargar el modelo Whisper: {e}") from e

    def recognize(self, audio_file_path: str, language: str = None) -> str:
        """
        Transcribe un archivo de audio usando el modelo local Whisper.

        Args:
            audio_file_path: Ruta al archivo de audio.
            language: Código de idioma (ej. "es", "en", "es-ES", "en-US").
                      Si es None, Whisper intentará detectarlo.
                      El código se normalizará a dos letras si contiene un especificador regional.

        Returns:
            str: El texto transcrito. Retorna cadena vacía si no se detecta voz o hay error.

        Raises:
             FileNotFoundError: Si el archivo de audio no se encuentra.
             Exception: Para otros errores durante la transcripción.
        """
        if not os.path.exists(audio_file_path):
            logger.error(
                f"Archivo de audio no encontrado para Whisper: {audio_file_path}")
            raise FileNotFoundError(
                f"Archivo de audio no encontrado para Whisper: {audio_file_path}")

        self._load_model()

        whisper_language_code = None
        if language:
            original_lang_param = language  # Guardar el original para logging
            if "-" in language:
                whisper_language_code = language.split("-")[0].lower()
                # Log crucial para verificar la normalización
                logger.info(
                    f"Código de idioma original '{original_lang_param}' normalizado a '{whisper_language_code}' para Whisper.")
            else:
                whisper_language_code = language.lower()
                logger.info(
                    f"Código de idioma '{original_lang_param}' usado directamente (minúsculas): '{whisper_language_code}' para Whisper.")
        else:
            logger.info(
                "No se especificó idioma para Whisper, se usará detección automática.")

        # Log para ver qué se pasa a self.model.transcribe
        log_lang_for_transcribe = whisper_language_code if whisper_language_code else "detección automática"
        logger.info(
            f"Iniciando reconocimiento con Whisper para '{audio_file_path}' usando idioma: '{log_lang_for_transcribe}'.")

        try:
            result = self.model.transcribe(
                audio_file_path,
                # Pasar el código normalizado (o None)
                language=whisper_language_code,
                fp16=False  # Puedes probar con True si tienes GPU NVIDIA compatible
            )
            text = result["text"].strip()
            logger.info("Reconocimiento con Whisper completado.")
            return text

        except Exception as e:
            # Mejorar el mensaje de error si es por idioma no soportado
            if "Unsupported language" in str(e):
                logger.error(
                    f"Error durante el reconocimiento con Whisper: El código de idioma '{whisper_language_code}' (procesado desde '{language}') NO es soportado por el modelo Whisper. Detalle: {e}")
            else:
                logger.error(
                    f"Error durante el reconocimiento con Whisper: {e}")
            raise Exception(
                f"Error inesperado en WhisperRecognizer: {e}") from e
