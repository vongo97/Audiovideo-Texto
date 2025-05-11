# src/utils/gemini_processor.py
import logging
# Asegúrate de que google-generativeai esté instalado
import google.generativeai as genai
import json
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class GeminiProcessor:
    """
    Procesador de texto que utiliza la API de Google Gemini para analizar transcripciones.
    Realiza tareas como identificación de actores y segmentación de diálogos.
    """

    def __init__(self, api_key: str):
        """
        Inicializa el procesador de Gemini.

        Args:
            api_key: La API Key para autenticarse con el servicio de Google Gemini.
        """
        self.api_key = api_key
        # Configurar la API key de Gemini
        genai.configure(api_key=self.api_key)

        # TODO: Permitir configurar el modelo (ej. gemini-1.5-flash, gemini-1.0-pro)
        # Usamos gemini-1.5-flash por ser más rápido y económico para esta tarea.
        self.model = genai.GenerativeModel('gemini-1.5-flash')

        logger.info(
            f"GeminiProcessor inicializado con modelo {self.model.model_name}.")

    def process_text(self, transcribed_text: str) -> Dict[str, Any]:
        """
        Envía el texto transcrito a la API de Gemini para su procesamiento
        y retorna la información estructurada (actores, diálogos).

        Args:
            transcribed_text: La cadena de texto obtenida de la transcripción.

        Returns:
            Dict[str, Any]: Un diccionario con la información procesada,
                            esperando al menos las claves 'actors' (lista) y 'dialogues' (lista).
                            Ejemplo: {'actors': ['Actor 1', 'Actor 2'], 'dialogues': [{'speaker': 'Actor 1', 'text': '...'}]}

        Raises:
            Exception: Si ocurre un error durante la interacción con la API de Gemini o el procesamiento.
        """
        logger.info("Enviando texto a Gemini para procesamiento...")

        # TODO: Mejorar el prompt para que sea más robusto y especifique el formato de salida (JSON)
        # Un prompt más avanzado podría pedir un formato JSON específico.
        prompt = f"""
Eres un analizador de transcripciones experto. Tu tarea es tomar el texto de una transcripción y segmentarlo en turnos de diálogo, identificando al hablante de cada turno.

Considera los siguientes puntos al procesar el texto:
- Identifica a los hablantes incluso si solo se presentan una vez.
- Atribuye cada bloque de texto a un hablante identificado.
- Si no puedes identificar al hablante de un bloque, atribúyelo a "Desconocido".
- El texto puede contener ruidos o descripciones entre corchetes [ruido]. Ignora o maneja estos marcadores si es posible, pero no los incluyas como parte del nombre del hablante.
- El formato de salida debe ser una estructura de datos que contenga una lista de actores identificados y una lista de diálogos, donde cada diálogo es un objeto con las claves 'speaker' (el nombre del hablante) y 'text' (el texto del diálogo).

Ejemplo de formato de salida (idealmente JSON):
{{
  "actors": ["Nombre Actor 1", "Nombre Actor 2", "Desconocido"],
  "dialogues": [
    {{"speaker": "Nombre Actor 1", "text": "Hola, ¿cómo estás?"}},
    {{"speaker": "Nombre Actor 2", "text": "Estoy bien, gracias. ¿Y tú?"}},
    {{"speaker": "Nombre Actor 1", "text": "Todo bien por aquí."}},
    {{"speaker": "Desconocido", "text": "Se escucha un golpe."}}
  ]
}}

Analiza el siguiente texto:
{transcribed_text}

Proporciona la salida en formato JSON.
"""
        # TODO: Implementar manejo de fragmentos de texto si el texto es muy largo para la API.
        # En la versión anterior, probablemente enviábamos el texto completo.
        # La fragmentación se añadió después. Si el texto es largo, esto podría fallar.

        try:
            # Usar generate_content con response_mime_type="application/json" si el modelo lo soporta
            # y el prompt está diseñado para JSON.
            # Si el modelo no soporta JSON nativo, confiaremos en que el prompt guíe la salida a JSON.
            # Para compatibilidad con versiones anteriores o modelos que no soportan JSON nativo:
            response = self.model.generate_content(prompt)

            # Intentar parsear la respuesta como JSON
            # A veces la respuesta puede venir envuelta en texto o con formato markdown de código.
            # Necesitamos extraer la parte JSON.
            response_text = response.text.strip()

            # Buscar bloques de código JSON en la respuesta (si Gemini los envuelve)
            if response_text.startswith("```json"):
                response_text = response_text[len("```json"):].strip()
                if response_text.endswith("```"):
                    response_text = response_text[:-len("```")].strip()

            # Intentar cargar el JSON
            processed_data = json.loads(response_text)

            # Validar la estructura básica esperada
            if not isinstance(processed_data, dict) or "actors" not in processed_data or "dialogues" not in processed_data:
                logger.warning(
                    "La respuesta de Gemini no tiene la estructura JSON esperada.")
                # Intentar un parseo alternativo o retornar datos básicos
                # Como fallback, podemos asumir que todo es de un actor "Desconocido"
                processed_data = {"actors": ["Desconocido"], "dialogues": [
                    {"speaker": "Desconocido", "text": transcribed_text}]}

            logger.info("Procesamiento con Gemini completado exitosamente.")
            return processed_data

        except json.JSONDecodeError as e:
            logger.error(f"Error al parsear la respuesta JSON de Gemini: {e}")
            logger.error(
                f"Respuesta recibida de Gemini (sin parsear):\n{response.text}")
            # Como fallback en caso de error JSON, retornar todo el texto como de un actor "Desconocido"
            return {"actors": ["Desconocido"], "dialogues": [{"speaker": "Desconocido", "text": transcribed_text}]}

        except Exception as e:
            logger.error(f"Error durante el procesamiento con Gemini API: {e}")
            # Como fallback en caso de cualquier otro error, retornar todo el texto como de un actor "Desconocido"
            return {"actors": ["Desconocido"], "dialogues": [{"speaker": "Desconocido", "text": transcribed_text}]}
