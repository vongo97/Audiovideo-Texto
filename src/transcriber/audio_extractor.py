# src/transcriber/audio_extractor.py
import os
import logging
import subprocess
import json
from typing import Dict, Any, Union

# Importaciones relativas corregidas previamente
from ..utils.gemini_processor import GeminiProcessor
from ..utils.text_processor import TextProcessor
from .speech_recognition_factory import SpeechRecognizer

logger = logging.getLogger(__name__)

OUTPUT_DIR = "output"
# Se cambió el nombre de audio extraído para que sea específico del archivo y evitar sobreescrituras
# AUDIO_FILENAME = "extracted_audio.wav" # Ya no se usa este nombre genérico
# No se usa directamente para el nombre final
TRANSCRIPTION_FILENAME = "transcription.txt"
# Sufijo para el archivo final
PROCESSED_TRANSCRIPTION_FILENAME = "processed_transcription.txt"

# Tiempo de espera para el proceso ffmpeg en segundos (ej. 10 minutos)
FFMPEG_TIMEOUT = 600


def extract_audio(video_path: str, output_path: str):
    """
    Extrae el audio de un archivo de video o audio usando ffmpeg.

    Args:
        video_path: Ruta al archivo de video o audio de entrada.
        output_path: Ruta donde se guardará el archivo de audio extraído (formato WAV).

    Raises:
        subprocess.CalledProcessError: Si el comando ffmpeg falla.
        FileNotFoundError: Si ffmpeg no se encuentra.
        subprocess.TimeoutExpired: Si ffmpeg excede el tiempo de espera.
    """
    logger.info(f"Iniciando extracción de audio desde: {video_path}")
    logger.info(f"El audio extraído se guardará en: {output_path}")

    try:
        logger.debug(
            f"Asegurando que el directorio de salida '{os.path.dirname(output_path)}' exista.")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        logger.debug(
            f"Directorio de salida '{os.path.dirname(output_path)}' listo.")
    except OSError as e:
        logger.error(
            f"No se pudo crear el directorio de salida '{os.path.dirname(output_path)}': {e}")
        raise  # Re-lanzar la excepción para que sea manejada por el llamador

    command = [
        "ffmpeg",
        "-i", video_path,
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", "44100",
        "-ac", "1",
        "-y",  # Sobrescribir archivo de salida si existe
        output_path
    ]

    logger.info(f"Ejecutando comando ffmpeg: {' '.join(command)}")

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True,  # Lanza CalledProcessError si ffmpeg retorna un código de error
            timeout=FFMPEG_TIMEOUT  # Añadir tiempo de espera
        )
        logger.info("Extracción de audio completada exitosamente.")
        logger.debug(f"FFmpeg stdout:\n{result.stdout}")
        if result.stderr:  # ffmpeg a menudo usa stderr para información, no solo errores
            logger.debug(f"FFmpeg stderr:\n{result.stderr}")

    except FileNotFoundError:
        logger.error(
            "Error Crítico: ffmpeg no encontrado. Asegúrate de que ffmpeg esté instalado y en el PATH del sistema.")
        raise
    except subprocess.CalledProcessError as e:
        logger.error(
            f"Error durante la ejecución de ffmpeg (código de retorno {e.returncode}): {e}")
        logger.error(f"FFmpeg stdout (si hubo):\n{e.stdout}")
        logger.error(f"FFmpeg stderr:\n{e.stderr}")  # stderr es crucial aquí
        raise
    except subprocess.TimeoutExpired as e:
        logger.error(
            f"ffmpeg tardó demasiado (más de {FFMPEG_TIMEOUT} segundos) y fue interrumpido.")
        logger.error(
            f"FFmpeg stdout (si hubo antes del timeout):\n{e.stdout.decode(errors='ignore') if e.stdout else 'N/A'}")
        logger.error(
            f"FFmpeg stderr (si hubo antes del timeout):\n{e.stderr.decode(errors='ignore') if e.stderr else 'N/A'}")
        raise
    except Exception as e:  # Captura cualquier otra excepción inesperada
        logger.error(f"Error inesperado durante la extracción de audio: {e}")
        raise


def transcribe_audio(audio_path: str, recognizer: SpeechRecognizer, language: str) -> str:
    logger.info(
        f"Transcribiendo audio: {audio_path} usando {type(recognizer).__name__} en idioma {language}")
    try:
        transcription_text = recognizer.recognize(audio_path, language)
        logger.info("Transcripción de audio completada.")
        return transcription_text
    except Exception as e:
        logger.error(f"Error durante la transcripción: {e}")
        raise  # Re-lanzar para que sea manejado por la UI


def extract_and_transcribe(file_path: str, ai_text_processor: Union[GeminiProcessor, Any], formatter: TextProcessor,
                           recognizer: SpeechRecognizer, language: str) -> str:
    logger.info(
        f"Iniciando proceso completo para: {file_path}")

    # Crear el directorio de salida general si no existe
    try:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
    except OSError as e:
        logger.error(
            f"No se pudo crear el directorio de salida principal '{OUTPUT_DIR}': {e}")
        raise

    base_filename = os.path.splitext(os.path.basename(file_path))[0]
    # Limpiar un poco el base_filename para rutas, aunque ffmpeg y Python deberían manejar Unicode.
    # Esto es una medida de precaución menor; el problema principal suele ser con la herramienta externa (ffmpeg).
    # safe_base_filename = "".join(c if c.isalnum() or c in (' ', '_', '-') else '_' for c in base_filename)
    # Por ahora, mantenemos el nombre original para ver si ffmpeg lo maneja con las rutas correctas.
    safe_base_filename = base_filename

    audio_output_path = os.path.join(
        OUTPUT_DIR, f"{safe_base_filename}_extracted_audio.wav")
    processed_transcription_output_path = os.path.join(
        OUTPUT_DIR, f"{safe_base_filename}_{PROCESSED_TRANSCRIPTION_FILENAME}")

    try:
        logger.info(f"Paso 1: Extracción de audio para '{file_path}'...")
        extract_audio(file_path, audio_output_path)
        logger.info(f"Audio extraído correctamente en: {audio_output_path}")

        logger.info(
            f"Paso 2: Transcripción de audio para '{audio_output_path}'...")
        raw_transcription = transcribe_audio(
            audio_output_path, recognizer, language)
        logger.info("Transcripción en bruto obtenida.")
        # Log de una parte
        logger.debug(f"Transcripción en bruto: {raw_transcription[:200]}...")

        logger.info("Paso 3: Procesamiento de la transcripción con IA...")
        if ai_text_processor:
            if hasattr(ai_text_processor, 'process_text'):
                processed_data = ai_text_processor.process_text(
                    raw_transcription)
            elif hasattr(ai_text_processor, 'process_transcription'):
                processed_data = ai_text_processor.process_transcription(
                    raw_transcription)
            else:
                logger.error(
                    "El procesador AI no tiene un método 'process_text' o 'process_transcription'.")
                processed_data = {"actors": ["Desconocido"], "dialogues": [
                    {"speaker": "Desconocido", "text": raw_transcription}]}
            logger.info("Procesamiento AI completado.")
        else:
            logger.warning(
                "No hay procesador AI configurado. Usando transcripción en bruto.")
            processed_data = {"actors": ["Desconocido"], "dialogues": [
                {"speaker": "Desconocido", "text": raw_transcription}]}

        logger.info("Paso 4: Formateo del resultado...")
        formatted_transcription = formatter.format_processed_result(
            processed_data, os.path.basename(file_path))
        logger.info("Formateo completado.")

        logger.info(
            f"Paso 5: Guardando transcripción procesada en '{processed_transcription_output_path}'...")
        with open(processed_transcription_output_path, "w", encoding="utf-8") as f:
            f.write(formatted_transcription)
        logger.info(
            "Transcripción procesada y formateada guardada exitosamente.")

        if os.path.exists(audio_output_path):
            try:
                logger.debug(
                    f"Intentando eliminar archivo de audio temporal: {audio_output_path}")
                os.remove(audio_output_path)
                logger.info(
                    f"Archivo de audio temporal eliminado: {audio_output_path}")
            except OSError as e_remove:
                logger.warning(
                    f"No se pudo eliminar el archivo de audio temporal '{audio_output_path}': {e_remove}")

        return processed_transcription_output_path

    except Exception as e:
        logger.error(
            f"Error en el flujo principal de extract_and_transcribe para '{file_path}': {type(e).__name__} - {e}")
        # Re-lanzar la excepción para que la UI la maneje
        # Es importante que la UI muestre estos errores.
        raise
    finally:
        # Asegurarse de que el archivo de audio temporal se elimine al final
        if os.path.exists(audio_output_path):
            try:
                logger.debug(
                    f"Intentando eliminar archivo de audio temporal: {audio_output_path}")
                os.remove(audio_output_path)
                logger.info(
                    f"Archivo de audio temporal eliminado: {audio_output_path}")
            except OSError as e_remove:
                logger.warning(
                    f"No se pudo eliminar el archivo de audio temporal '{audio_output_path}': {e_remove}")
