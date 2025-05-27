# src/utils/audio_diarization.py
import logging
import os
import subprocess
from typing import Dict, Any, List, Optional
import json
import tempfile

logger = logging.getLogger(__name__)

class AudioDiarization:
    """
    Clase para realizar diarización de audio (separación de hablantes) utilizando
    herramientas externas como PyAnnote o Whisper-diarize.
    """
    
    def __init__(self, model_path: Optional[str] = None):
        """
        Inicializa el sistema de diarización.
        
        Args:
            model_path: Ruta opcional al modelo pre-entrenado
        """
        self.model_path = model_path
        logger.info("AudioDiarization inicializado")
        
    def diarize_audio(self, audio_path: str) -> Dict[str, Any]:
        """
        Realiza la diarización del audio para identificar diferentes hablantes.
        
        Args:
            audio_path: Ruta al archivo de audio a procesar
            
        Returns:
            Diccionario con información de segmentos y hablantes
        """
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"El archivo de audio {audio_path} no existe")
            
        logger.info(f"Iniciando diarización del audio: {audio_path}")
        
        # Crear un archivo temporal para los resultados
        try:
            with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as tmp_file:
                output_path = tmp_file.name
        except Exception as e:
            logger.warning(f"No se pudo crear archivo temporal: {e}. Usando ruta predefinida.")
            output_path = os.path.join(os.path.dirname(audio_path), "diarization_result.json")
            
        try:
            # Ejecutar el comando de diarización (usando pyannote-audio si está instalado)
            # Este es un ejemplo simplificado, en una implementación real se usaría
            # la API de pyannote-audio directamente desde Python
            cmd = [
                "python", "-m", "pyannote.audio", "diarize",
                "--model", self.model_path or "pyannote/speaker-diarization-3.0",
                "--output", output_path,
                audio_path
            ]
            
            logger.info(f"Ejecutando comando: {' '.join(cmd)}")
            
            # En una implementación real, esto ejecutaría el comando
            # subprocess.run(cmd, check=True, capture_output=True)
            
            # Como es una simulación, devolvemos un resultado de ejemplo
            # En una implementación real, leeríamos el archivo output_path
            return {
                "segments": [
                    {"start": 0.0, "end": 15.5, "speaker": "SPEAKER_01"},
                    {"start": 15.8, "end": 25.2, "speaker": "SPEAKER_02"},
                    {"start": 25.5, "end": 40.0, "speaker": "SPEAKER_01"},
                    {"start": 40.3, "end": 55.7, "speaker": "SPEAKER_03"},
                    {"start": 56.0, "end": 70.2, "speaker": "SPEAKER_01"}
                ]
            }
            
        except Exception as e:
            logger.error(f"Error durante la diarización: {e}")
            # Devolver un resultado vacío en caso de error
            return {"segments": []}
            
        finally:
            # Limpiar archivos temporales
            if os.path.exists(output_path):
                os.unlink(output_path)
                
    def merge_diarization_with_transcript(self, diarization_result: Dict[str, Any], 
                                         transcript: str) -> Dict[str, Any]:
        """
        Combina los resultados de diarización con la transcripción para asignar
        texto a cada hablante identificado.
        
        Args:
            diarization_result: Resultado de la diarización con segmentos y hablantes
            transcript: Texto transcrito completo
            
        Returns:
            Diccionario con actores y diálogos estructurados
        """
        logger.info("Combinando resultados de diarización con transcripción")
        
        # Esta es una implementación simplificada
        # En un caso real, se alinearían los tiempos de la diarización con el texto
        
        # Extraer hablantes únicos
        speakers = set()
        for segment in diarization_result.get("segments", []):
            speakers.add(segment.get("speaker", "Desconocido"))
        
        # Mapear hablantes a nombres más amigables
        speaker_mapping = {}
        for i, speaker in enumerate(speakers):
            speaker_mapping[speaker] = f"Participante {i+1}"
            
        # Crear estructura de salida
        result = {
            "actors": list(speaker_mapping.values()),
            "dialogues": []
        }
        
        # En una implementación real, aquí se dividiría el texto según los tiempos
        # de los segmentos. Como es una simulación, dividimos el texto arbitrariamente.
        
        # Dividir el texto en párrafos como aproximación simple
        paragraphs = transcript.split("\n\n")
        
        # Asignar párrafos a hablantes
        segments = diarization_result.get("segments", [])
        for i, paragraph in enumerate(paragraphs):
            if paragraph.strip():
                # Asignar al hablante correspondiente o al último si nos quedamos sin segmentos
                segment_idx = min(i, len(segments) - 1) if segments else 0
                speaker = speaker_mapping.get(
                    segments[segment_idx].get("speaker", "Desconocido") if segments else "Desconocido", 
                    "Desconocido"
                )
                
                result["dialogues"].append({
                    "speaker": speaker,
                    "text": paragraph.strip()
                })
                
        return result