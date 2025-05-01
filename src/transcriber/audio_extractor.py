from moviepy.video.io.VideoFileClip import VideoFileClip
from moviepy.audio.io.AudioFileClip import AudioFileClip
from pathlib import Path
from .speech_to_text import SpeechToText
import os
import math
import time
import logging
from pydub import AudioSegment

logger = logging.getLogger(__name__)


def is_video_file(file_path):
    video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv'}
    return Path(file_path).suffix.lower() in video_extensions


def is_audio_file(file_path):
    audio_extensions = {'.mp3', '.wav', '.m4a', '.aac', '.ogg', '.wma'}
    return Path(file_path).suffix.lower() in audio_extensions


# Reducido a 3 minutos por fragmento
def process_in_chunks(audio_file, chunk_duration=180):
    try:
        # Crear directorio temporal si no existe
        temp_dir = os.path.join(os.getcwd(), "temp")
        os.makedirs(temp_dir, exist_ok=True)

        # Obtener la duración total
        total_duration = audio_file.duration
        chunks = math.ceil(total_duration / chunk_duration)
        full_text = []

        logger.info(f"Duración total del audio: {total_duration} segundos")
        logger.info(f"Procesando en {chunks} fragmentos...")

        # Guardar el audio completo temporalmente
        temp_audio_path = os.path.join(temp_dir, "temp_audio.wav")
        audio_file.write_audiofile(temp_audio_path)

        # Cargar el audio con pydub
        audio_segment = AudioSegment.from_wav(temp_audio_path)

        for i in range(chunks):
            start_time = i * chunk_duration * 1000  # pydub usa milisegundos
            end_time = min((i + 1) * chunk_duration *
                           1000, total_duration * 1000)

            logger.info(
                f"\nProcesando fragmento {i+1} de {chunks} ({start_time/1000}s - {end_time/1000}s)...")

            try:
                # Extraer fragmento
                chunk = audio_segment[start_time:end_time]

                # Guardar fragmento
                chunk_path = os.path.join(temp_dir, f"chunk_{i}.wav")
                chunk.export(chunk_path, format="wav")

                # Procesar fragmento
                recognizer = SpeechToText()
                text = recognizer.convert_to_text(chunk_path)
                full_text.append(text)

                # Limpiar
                os.remove(chunk_path)

            except Exception as chunk_error:
                logger.error(f"❌ Error en fragmento {i+1}: {str(chunk_error)}")
                continue

        # Limpiar archivo temporal
        os.remove(temp_audio_path)

        return " ".join(full_text)

    except Exception as e:
        logger.error(f"Error procesando audio en fragmentos: {str(e)}")
        raise


def extract_and_transcribe(file_path):
    """
    Extrae audio de un archivo de video/audio y lo transcribe con procesamiento de texto avanzado.

    Args:
        file_path: Ruta al archivo de video o audio

    Returns:
        str: Ruta al archivo de transcripción generado
    """
    try:
        # Verificar si el archivo existe
        if not os.path.exists(file_path):
            raise FileNotFoundError("El archivo no existe")

        # Configurar directorios
        app_dir = Path(__file__).parent.parent.parent
        temp_dir = app_dir / "temp"
        trans_dir = app_dir / "transcripciones"

        # Crear directorios necesarios
        temp_dir.mkdir(exist_ok=True)
        trans_dir.mkdir(exist_ok=True)

        # Configurar rutas
        audio_path = temp_dir / "temp_audio.wav"
        text_path = trans_dir / f"{Path(file_path).stem}_transcripcion.txt"

        logger.info(f"Procesando archivo: {file_path}")
        logger.info(f"Archivo de salida: {text_path}")

        try:
            # Procesar según el tipo de archivo
            if is_video_file(file_path):
                logger.info("Procesando archivo de video...")
                with VideoFileClip(str(file_path)) as video:
                    if video.audio is None:
                        raise ValueError("El video no contiene audio")
                    text = process_in_chunks(video.audio)

            elif is_audio_file(file_path):
                logger.info("Procesando archivo de audio...")
                with AudioFileClip(str(file_path)) as audio:
                    text = process_in_chunks(audio)

            else:
                raise ValueError(
                    "Formato de archivo no soportado. Use archivos de video o audio.")

            # Procesar el texto transcrito
            logger.info("Procesando transcripción con análisis de texto...")
            from utils.text_processor import TextProcessor
            text_processor = TextProcessor()
            processed_result = text_processor.process_transcript(text)

            # Guardar transcripción estructurada
            logger.info("Guardando transcripción estructurada...")
            with open(text_path, 'w', encoding='utf-8') as f:
                # Encabezado
                f.write("TRANSCRIPCIÓN ESTRUCTURADA\n")
                f.write("=========================\n\n")

                # Metadatos
                f.write("INFORMACIÓN DEL ARCHIVO\n")
                f.write("---------------------\n")
                f.write(f"Archivo original: {Path(file_path).name}\n")
                f.write(
                    f"Fecha de procesamiento: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")

                # Actores identificados
                if processed_result["actors"]:
                    f.write("ACTORES IDENTIFICADOS\n")
                    f.write("--------------------\n")
                    for actor in processed_result["actors"]:
                        f.write(f"- {actor}\n")
                    f.write("\n")

                # Diálogos por actor
                f.write("DIÁLOGOS POR ACTOR\n")
                f.write("-----------------\n")
                for actor, dialogues in processed_result["dialogue_by_actor"].items():
                    if dialogues:
                        f.write(f"\n[{actor}]\n")
                        for dialogue in dialogues:
                            f.write(f"  • {dialogue}\n")
                f.write("\n")

                # Texto completo estructurado
                f.write("TEXTO COMPLETO ESTRUCTURADO\n")
                f.write("-------------------------\n")
                f.write(processed_result["structured_text"])

            logger.info(f"Transcripción guardada exitosamente en: {text_path}")
            return str(text_path)

        except Exception as e:
            logger.error(f"Error en el procesamiento: {str(e)}")
            raise

    except Exception as e:
        logger.error(f"Error general: {str(e)}")
        return str(e)

    finally:
        # Limpiar archivos temporales
        if audio_path.exists():
            audio_path.unlink()

        # Limpiar directorio temporal
        for temp_file in temp_dir.glob("chunk_*.wav"):
            temp_file.unlink()
