# src/utils/text_processor_factory.py
import logging
from typing import Dict, Any

# Importar las clases de procesador de texto
from .gemini_processor import GeminiProcessor
from .deepseek_processor import DeepSeekProcessor
# Puedes definir una interfaz base si quieres, como en SpeechRecognizer.

logger = logging.getLogger(__name__)

# Define una interfaz base informal o una clase abstracta si lo necesitas
# class TextProcessorInterface:
#     def process_text(self, transcribed_text: str) -> Dict[str, Any]:
#         pass


class TextProcessorFactory:
    """
    Fábrica para crear instancias de diferentes procesadores de texto (ej. Gemini, DeepSeek).
    """
    @staticmethod
    def create_processor(processor_type: str, api_key: str, text_processing_config: Dict[str, Any]):
        """
        Crea una instancia de un procesador de texto basado en el tipo especificado.

        Args:
            processor_type: El tipo de procesador de texto ('gemini', 'deepseek').
            api_key: La API Key principal (actualmente usada por Gemini y posiblemente DeepSeek).
                     Se pasa aquí, pero cada procesador decide si la usa y cómo.
            text_processing_config: El diccionario de configuración para el procesamiento de texto.
                                    Actualmente, esta configuración es más para el formateador,
                                    pero se pasa a la fábrica por si un procesador de IA la necesitara.

        Returns:
            Una instancia de GeminiProcessor, DeepSeekProcessor, o una clase compatible.

        Raises:
            ValueError: Si el tipo de procesador es desconocido.
            Exception: Si ocurre un error durante la inicialización del procesador.
        """
        logger.info(
            f"Creando instancia de procesador de texto: {processor_type}")
        # --- LOG DE DEBUG AQUÍ ---
        logger.debug(
            f"DEBUG TextProcessorFactory.create_processor - processor_type recibido: '{processor_type}'")

        try:
            if processor_type.lower() == "gemini":
                # GeminiProcessor necesita la API Key
                logger.debug(
                    "DEBUG TextProcessorFactory: Creando GeminiProcessor.")
                return GeminiProcessor(api_key=api_key)
            elif processor_type.lower() == "deepseek":
                # DeepSeekProcessor necesita la API Key
                # NOTA: Si DeepSeek requiere una API Key diferente o configuración específica,
                # necesitarás ajustar cómo se pasa aquí o cómo se obtiene en __init__.
                logger.debug(
                    "DEBUG TextProcessorFactory: Creando DeepSeekProcessor.")
                # Asumimos que usa la misma API key por ahora
                return DeepSeekProcessor(api_key=api_key)
            else:
                logger.error(
                    f"Tipo de procesador de texto desconocido: '{processor_type}'")
                raise ValueError(
                    f"Tipo de procesador de texto desconocido: {processor_type}")

        except Exception as e:
            logger.error(
                f"Error al inicializar el procesador de texto '{processor_type}': {e}")
            # Relanzar la excepción con un mensaje más específico si es útil
            raise Exception(
                f"Error al inicializar el procesador de texto '{processor_type}': {e}") from e
