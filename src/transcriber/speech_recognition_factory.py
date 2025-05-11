# src/transcriber/speech_recognition_factory.py
# Este archivo define la interfaz base para los reconocedores de voz.
# La fábrica para crearlos estaba en main.py en la versión anterior.

from abc import ABC, abstractmethod
from typing import Dict, Any


class SpeechRecognizer(ABC):
    """
    Interfaz base abstracta para los reconocedores de voz.
    Todos los reconocedores deben heredar de esta clase e implementar el método recognize.
    """
    @abstractmethod
    def recognize(self, audio_file_path: str, language: str) -> str:
        """
        Transcribe un archivo de audio.

        Args:
            audio_file_path: Ruta al archivo de audio.
            language: Código de idioma para la transcripción.

        Returns:
            str: El texto transcribido.

        Raises:
            Exception: Si ocurre un error durante el reconocimiento.
        """
        pass

    # Puedes añadir una clase de error base común si quieres
    class RecognitionError(Exception):
        """Excepción base para errores de reconocimiento."""
        pass

    # NOTA: En la versión anterior, la lógica para crear instancias
    # de reconocedores basándose en la configuración estaba directamente en main.py.
    # La TextProcessorFactory y SpeechRecognizerFactory se añadieron después.
