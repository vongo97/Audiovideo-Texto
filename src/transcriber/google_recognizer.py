# src/transcriber/google_recognizer.py
import logging
import speech_recognition as sr
import os
import wave
import contextlib
import math
import time
import uuid
from typing import Optional, List
from .speech_recognition_factory import SpeechRecognizer

logger = logging.getLogger(__name__)


class GoogleRecognizer(SpeechRecognizer):
    """
    Implementación de SpeechRecognizer que utiliza Google Web Speech API.
    """

    def __init__(self):
        """Inicializa el reconocedor de Google."""
        self.recognizer = sr.Recognizer()
        self._is_cancelled = False
        logger.info("GoogleRecognizer inicializado.")

    def cancel(self):
        """Marca el proceso como cancelado."""
        self._is_cancelled = True
        logger.info("Proceso de reconocimiento marcado para cancelación.")

    def recognize(self, audio_path: str, language: str) -> str:
        """
        Reconoce el habla en un archivo de audio usando Google Web Speech API.
        Para archivos grandes, divide el audio en fragmentos más pequeños.

        Args:
            audio_path: Ruta al archivo de audio a transcribir.
            language: Código de idioma para el reconocimiento (ej. 'es-ES', 'en-US').

        Returns:
            str: El texto transcrito.

        Raises:
            Exception: Si ocurre un error durante el reconocimiento.
        """
        logger.info(
            f"Iniciando reconocimiento con Google para {audio_path} en idioma {language}...")

        self._is_cancelled = False  # Reiniciar el estado de cancelación

        try:
            # Verificar la duración del audio
            with contextlib.closing(wave.open(audio_path, 'r')) as f:
                frames = f.getnframes()
                rate = f.getframerate()
                duration = frames / float(rate)

            # Si el audio es mayor a 60 segundos, dividirlo en fragmentos
            if duration > 60:
                logger.info(
                    f"Audio demasiado largo ({duration:.2f} segundos). Dividiendo en fragmentos...")
                return self._process_long_audio(audio_path, language)
            else:
                # Procesar audio corto normalmente
                return self._process_short_audio(audio_path, language)

        except Exception as e:
            error_msg = f"Error inesperado durante el reconocimiento con Google: {e}"
            logger.error(error_msg)
            raise Exception(f"Error inesperado en GoogleRecognizer: {e}")

    def _process_short_audio(self, audio_path: str, language: str) -> str:
        """Procesa un archivo de audio corto."""
        if self._is_cancelled:
            logger.info("Proceso cancelado durante _process_short_audio")
            return ""

        try:
            # Cargar el archivo de audio
            with sr.AudioFile(audio_path) as source:
                # Grabar el audio completo
                audio_data = self.recognizer.record(source)

                # Realizar el reconocimiento con reintentos
                for attempt in range(3):  # 3 intentos
                    if self._is_cancelled:
                        logger.info("Proceso cancelado durante reconocimiento")
                        return ""

                    try:
                        text = self.recognizer.recognize_google(
                            audio_data, language=language)
                        logger.info("Reconocimiento con Google completado.")
                        return text
                    except sr.RequestError as e:
                        if attempt < 2:  # Si no es el último intento
                            logger.warning(
                                f"Intento {attempt+1} fallido: {e}. Reintentando...")
                            # Esperar un segundo antes de reintentar
                            time.sleep(1)
                        else:
                            raise  # Re-lanzar en el último intento

        except sr.UnknownValueError:
            logger.warning("Google Web Speech API no pudo entender el audio.")
            return ""  # Devolver cadena vacía si no se reconoció nada

        except sr.RequestError as e:
            error_msg = f"Error de solicitud a Google Web Speech API; {e}"
            logger.error(error_msg)
            raise sr.RequestError(f"Error de solicitud a Google API: {e}")

    def _process_long_audio(self, audio_path: str, language: str) -> str:
        """
        Procesa un archivo de audio largo dividiéndolo en fragmentos.
        """
        # Crear un directorio temporal único para esta instancia
        session_id = str(uuid.uuid4())[:8]
        temp_dir = f"temp_{session_id}"
        os.makedirs(temp_dir, exist_ok=True)

        try:
            # Obtener el nombre base del archivo
            base_name = os.path.splitext(os.path.basename(audio_path))[0]

            # Dividir el audio en fragmentos de 30 segundos
            chunk_size = 30  # segundos
            chunk_paths = self._split_audio(
                audio_path, temp_dir, base_name, chunk_size)

            # Procesar cada fragmento
            transcriptions = []
            for i, chunk_path in enumerate(chunk_paths):
                if self._is_cancelled:
                    logger.info(
                        f"Proceso cancelado en fragmento {i+1}/{len(chunk_paths)}")
                    break

                logger.info(
                    f"Procesando fragmento de audio {i+1}/{len(chunk_paths)}...")
                try:
                    chunk_text = self._process_short_audio(
                        chunk_path, language)
                    if chunk_text:
                        transcriptions.append(chunk_text)
                except Exception as e:
                    logger.error(f"Error al procesar fragmento {i+1}: {e}")
                    # Continuar con el siguiente fragmento
                finally:
                    # Intentar eliminar el archivo temporal
                    try:
                        if os.path.exists(chunk_path):
                            os.remove(chunk_path)
                    except Exception as e:
                        logger.warning(
                            f"No se pudo eliminar el archivo temporal {chunk_path}: {e}")

            # Combinar todas las transcripciones
            full_transcription = " ".join(transcriptions)
            if not self._is_cancelled:
                logger.info(
                    "Reconocimiento con Google completado para todos los fragmentos.")
            return full_transcription

        finally:
            # Limpiar todos los archivos temporales
            try:
                import shutil
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)
                    logger.info(f"Directorio temporal {temp_dir} eliminado")
            except Exception as e:
                logger.warning(
                    f"No se pudo eliminar el directorio temporal {temp_dir}: {e}")

    def _split_audio(self, audio_path: str, temp_dir: str, base_name: str, chunk_size: int) -> List[str]:
        """
        Divide un archivo de audio en fragmentos más pequeños.

        Args:
            audio_path: Ruta al archivo de audio.
            temp_dir: Directorio para guardar los fragmentos.
            base_name: Nombre base del archivo.
            chunk_size: Tamaño de cada fragmento en segundos.

        Returns:
            List[str]: Lista de rutas a los archivos de fragmentos.
        """
        if self._is_cancelled:
            return []

        # Obtener información del audio
        with contextlib.closing(wave.open(audio_path, 'r')) as f:
            frames = f.getnframes()
            rate = f.getframerate()
            duration = frames / float(rate)
            channels = f.getnchannels()
            sample_width = f.getsampwidth()

        # Calcular el número de fragmentos
        num_chunks = math.ceil(duration / chunk_size)
        # 500 fragmentos
        max_chunks = min(num_chunks, 500)
        logger.info(
            f"Dividiendo audio de {duration:.2f} segundos en {max_chunks} fragmentos (de {num_chunks} totales)")

        # Crear fragmentos directamente desde el archivo original
        chunk_paths = []

        for i in range(max_chunks):
            if self._is_cancelled:
                break

            start_time = i * chunk_size
            # Usar ffmpeg para extraer fragmentos
            chunk_path = os.path.join(temp_dir, f"chunk_{i}.wav")
            chunk_paths.append(chunk_path)

            # Comando ffmpeg para extraer el fragmento
            import subprocess
            cmd = [
                "ffmpeg",
                "-i", audio_path,
                "-ss", str(start_time),
                "-t", str(chunk_size),
                "-acodec", "pcm_s16le",
                "-ar", str(rate),
                "-ac", str(channels),
                "-y",  # Sobrescribir si existe
                chunk_path
            ]

            try:
                subprocess.run(cmd, check=True, capture_output=True)
            except subprocess.CalledProcessError as e:
                logger.error(f"Error al crear fragmento {i+1}: {e}")
                # Continuar con el siguiente fragmento

        return chunk_paths
