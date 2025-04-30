from moviepy.editor import VideoFileClip, AudioFileClip
from pathlib import Path
from .speech_to_text import SpeechToText
import os
import math
import time


def is_video_file(file_path):
    video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv'}
    return Path(file_path).suffix.lower() in video_extensions


def is_audio_file(file_path):
    audio_extensions = {'.mp3', '.wav', '.m4a', '.aac', '.ogg', '.wma'}
    return Path(file_path).suffix.lower() in audio_extensions


# Reducido a 3 minutos por fragmento
def process_in_chunks(audio_file, chunk_duration=180):
    try:
        # Guardar el archivo de audio original en una variable
        audio_path = audio_file.filename
        audio_file.close()  # Cerrar el archivo original

        recognizer = SpeechToText()
        total_duration = audio_file.duration
        chunks = math.ceil(total_duration / chunk_duration)
        full_text = []
        temp_dir = os.path.join(os.getcwd(), "temp")

        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)

        print(f"Duración total del audio: {total_duration} segundos")
        print(f"Procesando en {chunks} fragmentos...")

        for i in range(chunks):
            start_time = i * chunk_duration
            end_time = min((i + 1) * chunk_duration, total_duration)

            print(
                f"\nProcesando fragmento {i+1} de {chunks} ({start_time}s - {end_time}s)...")

            try:
                # Crear una nueva instancia de AudioFileClip para cada fragmento
                current_audio = AudioFileClip(audio_path)
                temp_chunk_path = os.path.join(
                    temp_dir,
                    f"chunk_{i}_{int(time.time())}_{os.getpid()}.wav"
                )

                # Extraer y procesar el fragmento
                chunk = current_audio.subclip(start_time, end_time)
                chunk.write_audiofile(
                    temp_chunk_path,
                    codec='pcm_s16le',
                    verbose=False,
                    logger=None,
                    fps=16000,
                    nbytes=2,
                    buffersize=2048,  # Buffer más pequeño
                    ffmpeg_params=["-ac", "1", "-ar", "16000"]
                )

                # Cerrar recursos inmediatamente
                chunk.close()
                current_audio.close()
                del chunk
                del current_audio

                # Verificar y transcribir
                if os.path.exists(temp_chunk_path) and os.path.getsize(temp_chunk_path) > 0:
                    text = recognizer.convert_to_text(temp_chunk_path)
                    if text:
                        full_text.append(text)
                        print(f"✓ Fragmento {i+1} transcrito exitosamente")
                    else:
                        print(f"⚠ No se pudo transcribir el fragmento {i+1}")

            except Exception as chunk_error:
                print(f"❌ Error en fragmento {i+1}: {str(chunk_error)}")
                continue

            finally:
                # Limpiar archivos temporales
                if os.path.exists(temp_chunk_path):
                    try:
                        os.remove(temp_chunk_path)
                    except:
                        pass

                # Forzar liberación de memoria
                import gc
                gc.collect()
                time.sleep(1)  # Pausa breve entre fragmentos

        return " ".join(full_text)

    except Exception as e:
        print(f"❌ Error en process_in_chunks: {str(e)}")
        raise e


def extract_and_transcribe(file_path):
    try:
        # Verificar si el archivo existe
        if not os.path.exists(file_path):
            raise Exception("El archivo no existe")

        # Obtener el directorio donde está el script actual
        app_dir = Path(__file__).parent.parent.parent

        # Crear directorio temporal si no existe
        temp_dir = app_dir / "temp"
        temp_dir.mkdir(exist_ok=True)

        # Crear directorio de transcripciones si no existe
        trans_dir = app_dir / "transcripciones"
        trans_dir.mkdir(exist_ok=True)

        # Rutas de archivos
        audio_path = temp_dir / "temp_audio.wav"
        text_path = trans_dir / \
            Path(file_path).name.replace(Path(file_path).suffix, '.txt')

        print(f"Procesando archivo: {file_path}")  # Debug
        print(f"Creando archivo en: {text_path}")  # Debug

        try:
            # Procesar según el tipo de archivo
            if is_video_file(file_path):
                print(f"Iniciando procesamiento del video: {file_path}")
                try:
                    video = VideoFileClip(str(file_path))
                    print("Video cargado correctamente")

                    if video.audio is None:
                        raise Exception("El video no contiene audio")

                    print("Extrayendo audio del video...")
                    # Usar process_in_chunks directamente con el audio del video
                    text = process_in_chunks(video.audio)
                    print("Extracción de audio completada")
                    video.close()

                except Exception as video_error:
                    print(f"Error al procesar el video: {str(video_error)}")
                    raise video_error

            elif is_audio_file(file_path):
                print(f"Iniciando procesamiento del audio: {file_path}")
                try:
                    audio = AudioFileClip(str(file_path))
                    print("Audio cargado correctamente")

                    # Usar process_in_chunks directamente con el archivo de audio
                    text = process_in_chunks(audio)
                    print("Procesamiento de audio completado")
                    audio.close()

                except Exception as audio_error:
                    print(f"Error al procesar el audio: {str(audio_error)}")
                    raise audio_error
            else:
                raise Exception(
                    "Formato de archivo no soportado. Use archivos de video o audio.")

            # Guardar transcripción
            print("Guardando transcripción...")
            with open(text_path, 'w', encoding='utf-8') as f:
                f.write(text)

            print(f"Archivo guardado exitosamente en: {text_path}")
            return str(text_path)

        except Exception as ve:
            raise Exception(f"Error en el procesamiento: {str(ve)}")

    except Exception as e:
        print(f"Error general: {str(e)}")
        return str(e)
    finally:
        # Asegurarse de que los archivos temporales se eliminen
        if 'video' in locals():
            video.close()
        if 'audio' in locals():
            audio.close()
        if os.path.exists(audio_path):
            os.remove(audio_path)
