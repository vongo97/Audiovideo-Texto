# src/utils/deepseek_processor.py
import logging
import json
import requests
import time
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class DeepSeekProcessor:
    """
    Procesador de texto que utiliza la API de DeepSeek para analizar transcripciones.
    Realiza tareas como identificación de actores y segmentación de diálogos.
    """

    def __init__(self, api_key: str):
        """
        Inicializa el procesador de DeepSeek.

        Args:
            api_key: La API Key para autenticarse con el servicio de DeepSeek.
        """
        self.api_key = api_key
        self.api_url = "https://api.deepseek.com/v1/chat/completions"
        self.model = "deepseek-chat"  # Modelo por defecto

        logger.info(f"DeepSeekProcessor inicializado con modelo {self.model}.")

    def process_text(self, transcribed_text: str) -> Dict[str, Any]:
        """
        Envía el texto transcrito a la API de DeepSeek para su procesamiento
        y retorna la información estructurada (actores, diálogos).

        Args:
            transcribed_text: La cadena de texto obtenida de la transcripción.

        Returns:
            Dict[str, Any]: Un diccionario con la información procesada,
                            esperando al menos las claves 'actors' (lista) y 'dialogues' (lista).
                            Ejemplo: {'actors': ['Actor 1', 'Actor 2'], 'dialogues': [{'speaker': 'Actor 1', 'text': '...'}]}

        Raises:
            Exception: Si ocurre un error durante la interacción con la API de DeepSeek o el procesamiento.
        """
        logger.info("Enviando texto a DeepSeek para procesamiento...")

        # Manejar textos largos dividiéndolos en fragmentos
        MAX_CHUNK_SIZE = 10000  # Tamaño máximo de cada fragmento en caracteres
        MAX_RETRIES = 3  # Número máximo de reintentos

        # Si el texto es muy largo, dividirlo en fragmentos
        if len(transcribed_text) > MAX_CHUNK_SIZE:
            logger.info(
                f"Texto demasiado largo ({len(transcribed_text)} caracteres). Dividiendo en fragmentos...")

            # Dividir el texto en fragmentos de aproximadamente MAX_CHUNK_SIZE caracteres
            # Intentamos dividir en puntos o comas para mantener la coherencia
            chunks = []
            current_chunk = ""

            for sentence in transcribed_text.replace(".", ".|").replace("?", "?|").replace("!", "!|").split("|"):
                if len(current_chunk) + len(sentence) > MAX_CHUNK_SIZE:
                    if current_chunk:
                        chunks.append(current_chunk)
                    current_chunk = sentence
                else:
                    current_chunk += sentence

            if current_chunk:
                chunks.append(current_chunk)

            logger.info(f"Texto dividido en {len(chunks)} fragmentos")

            # Procesar cada fragmento y combinar los resultados
            all_actors = []
            all_dialogues = []

            for i, chunk in enumerate(chunks):
                logger.info(f"Procesando fragmento {i+1}/{len(chunks)}...")

                # Procesar el fragmento con reintentos
                for retry in range(MAX_RETRIES):
                    try:
                        chunk_result = self._process_text_chunk(chunk)

                        # Añadir actores y diálogos al resultado final
                        for actor in chunk_result.get("actors", []):
                            if actor not in all_actors:
                                all_actors.append(actor)

                        all_dialogues.extend(chunk_result.get("dialogues", []))
                        break  # Si tiene éxito, salir del bucle de reintentos

                    except Exception as e:
                        logger.warning(
                            f"Error en intento {retry+1}/{MAX_RETRIES} al procesar fragmento {i+1}: {e}")
                        if retry == MAX_RETRIES - 1:  # Si es el último intento
                            logger.error(
                                f"Todos los intentos fallaron para el fragmento {i+1}")
                            # Añadir el fragmento como diálogo de "Desconocido"
                            all_dialogues.append(
                                {"speaker": "Desconocido", "text": chunk})

            return {"actors": all_actors, "dialogues": all_dialogues}
        else:
            # Si el texto no es muy largo, procesarlo directamente con reintentos
            for retry in range(MAX_RETRIES):
                try:
                    return self._process_text_chunk(transcribed_text)
                except Exception as e:
                    logger.warning(
                        f"Error en intento {retry+1}/{MAX_RETRIES}: {e}")
                    if retry == MAX_RETRIES - 1:  # Si es el último intento
                        logger.error("Todos los intentos fallaron")
                        # Retornar un resultado básico como fallback
                        return {"actors": ["Desconocido"], "dialogues": [{"speaker": "Desconocido", "text": transcribed_text}]}

    def _process_text_chunk(self, text_chunk: str) -> Dict[str, Any]:
        """
        Procesa un fragmento de texto con la API de DeepSeek.
        Método interno utilizado por process_text.
        """
        prompt = f"""
Eres un analizador de transcripciones experto, especializado en el ámbito jurídico, y un especialista en la identificación de hablantes en grabaciones legales. Tu tarea es tomar el texto de una transcripción de audio (por ejemplo, una declaración, una audiencia, una consulta legal) y segmentarlo cuidadosamente en turnos de diálogo, identificando de manera precisa al hablante de cada turno.

Considera los siguientes puntos clave al procesar el texto en un contexto legal:
- **Identificación Precisa de Roles Legales**: Es crucial identificar a todos los participantes presentes. Presta especial atención a roles comunes en el ámbito legal como: "Abogado [Nombre]", "Juez", "Fiscal", "Testigo [Nombre]", "Declarante", "Perito", "Secretario Judicial", "Interprete", "Cliente". Si se identifica un nuevo hablante sin un rol claro, intenta inferir su rol legal basándote en el contexto del diálogo.
- **Atribución Rigurosa y Consistente**: Atribuye cada bloque de texto a un hablante identificado. Mantén la consistencia en los nombres y roles de los hablantes a lo largo de toda la transcripción.
- **Manejo de Hablantes No Identificables**: Si a pesar del contexto no puedes identificar al hablante de un bloque, atribúyelo a "Desconocido", pero intenta categorizarlo si hay alguna pista (ej. "Voz Masculina Desconocida", "Persona en Audiencia").
- **Ignorar Ruidos y Marcadores Contextuales**: El texto puede contener descripciones de ruidos, pausas o acciones entre corchetes [ruido], [pausa], [risas]. Ignora estos marcadores o manéjalos de forma que no afecten la identificación del hablante ni se incluyan como parte del nombre del hablante.
- **Terminología y Tono Legal**: Reconoce el lenguaje formal y la terminología específica utilizada en el ámbito legal. Esto puede ayudar a inferir el contexto y, en ocasiones, al hablante.
- **Formato de Nombres de Actores**: Utiliza nombres descriptivos y consistentes que reflejen el rol legal, por ejemplo: "Abogado Defensor", "Abogada Querellante", "Testigo Clara Gómez". Si un nombre completo es proporcionado, úsalo.
- **Estructura de Salida**: La salida debe ser una estructura de datos JSON con dos claves principales: 'actors' (una lista de todos los nombres de hablantes únicos identificados y sus roles si es posible) y 'dialogues' (una lista de objetos, donde cada objeto representa un turno de diálogo con las claves 'speaker' y 'text').

Ejemplo de formato de salida (JSON):
```json
{
            "actors": ["Abogado Defensor Juan Pérez", "Juez Ana López", "Testigo María Rodríguez", "Fiscal Carlos M.","Desconocido"],
  "dialogues": [
    {"speaker": "Juez Ana López", "text": "Se abre la sesión. Abogado Pérez, puede proceder con su interrogatorio."},
    {"speaker": "Abogado Defensor Juan Pérez", "text": "Gracias, su Señoría. Sra. Rodríguez, ¿podría indicarnos su ubicación el día de los hechos?"},
    {"speaker": "Testigo María Rodríguez", "text": "Estaba en mi domicilio, como de costumbre."},
    {"speaker": "Fiscal Carlos M.", "text": "Objeción, su Señoría, la pregunta es capciosa."},
    {"speaker": "Juez Ana López", "text": "La objeción es desestimada. Continúe, abogado."},
    {"speaker": "Desconocido", "text": "[Ruido de papeles]"}
  ]
}

Analiza el siguiente texto:
{text_chunk}

Proporciona la salida en formato JSON.
"""

        try:
            # Preparar la solicitud para la API de DeepSeek
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }

            data = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": "Eres un asistente experto en análisis de transcripciones."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.3,  # Temperatura baja para respuestas más deterministas
                "max_tokens": 4000   # Ajustar según sea necesario
            }

            # Realizar la solicitud a la API
            response = requests.post(self.api_url, headers=headers, json=data)
            response.raise_for_status()  # Lanzar excepción si hay error HTTP

            # Procesar la respuesta
            response_data = response.json()
            response_text = response_data.get("choices", [{}])[0].get(
                "message", {}).get("content", "")

            # Buscar bloques de código JSON en la respuesta
            if response_text.startswith("```json"):
                response_text = response_text[len("```json"):].strip()
                if response_text.endswith("```"):
                    response_text = response_text[:-len("```")].strip()

            # Intentar cargar el JSON
            processed_data = json.loads(response_text)

            # Validar la estructura básica esperada
            if not isinstance(processed_data, dict) or "actors" not in processed_data or "dialogues" not in processed_data:
                logger.warning(
                    "La respuesta de DeepSeek no tiene la estructura JSON esperada.")
                processed_data = {"actors": ["Desconocido"], "dialogues": [
                    {"speaker": "Desconocido", "text": text_chunk}]}

            return processed_data

        except json.JSONDecodeError as e:
            logger.error(
                f"Error al parsear la respuesta JSON de DeepSeek: {e}")
            logger.error(
                f"Respuesta recibida de DeepSeek (sin parsear):\n{response_text}")
            raise

        except requests.exceptions.RequestException as e:
            logger.error(f"Error en la solicitud a la API de DeepSeek: {e}")
            raise

        except Exception as e:
            logger.error(
                f"Error durante el procesamiento con DeepSeek API: {e}")
            raise

    def translate_to_spanish(self, text: str) -> str:
        """
        Traduce el texto al español usando la API de DeepSeek.

        Args:
            text: El texto a traducir.

        Returns:
            str: El texto traducido al español.
        """
        logger.info("Traduciendo texto al español con DeepSeek...")

        # Manejar textos largos dividiéndolos en fragmentos
        MAX_CHUNK_SIZE = 10000  # Tamaño máximo de cada fragmento en caracteres
        MAX_RETRIES = 3  # Número máximo de reintentos

        # Si el texto es muy largo, dividirlo en fragmentos
        if len(text) > MAX_CHUNK_SIZE:
            logger.info(
                f"Texto demasiado largo para traducción ({len(text)} caracteres). Dividiendo en fragmentos...")

            # Dividir el texto en fragmentos de aproximadamente MAX_CHUNK_SIZE caracteres
            chunks = []
            current_chunk = ""

            for sentence in text.replace(".", ".|").replace("?", "?|").replace("!", "!|").split("|"):
                if len(current_chunk) + len(sentence) > MAX_CHUNK_SIZE:
                    if current_chunk:
                        chunks.append(current_chunk)
                    current_chunk = sentence
                else:
                    current_chunk += sentence

            if current_chunk:
                chunks.append(current_chunk)

            logger.info(
                f"Texto dividido en {len(chunks)} fragmentos para traducción")

            # Traducir cada fragmento y combinar los resultados
            translated_chunks = []

            for i, chunk in enumerate(chunks):
                logger.info(f"Traduciendo fragmento {i+1}/{len(chunks)}...")

                # Traducir el fragmento con reintentos
                for retry in range(MAX_RETRIES):
                    try:
                        translated_chunk = self._translate_chunk(chunk)
                        translated_chunks.append(translated_chunk)
                        break  # Si tiene éxito, salir del bucle de reintentos

                    except Exception as e:
                        logger.warning(
                            f"Error en intento {retry+1}/{MAX_RETRIES} al traducir fragmento {i+1}: {e}")
                        time.sleep(1)  # Esperar un segundo antes de reintentar
                        if retry == MAX_RETRIES - 1:  # Si es el último intento
                            logger.error(
                                f"Todos los intentos fallaron para traducir el fragmento {i+1}")
                            # Usar el texto original para este fragmento
                            translated_chunks.append(chunk)

            return " ".join(translated_chunks)
        else:
            # Si el texto no es muy largo, traducirlo directamente con reintentos
            for retry in range(MAX_RETRIES):
                try:
                    return self._translate_chunk(text)
                except Exception as e:
                    logger.warning(
                        f"Error en intento {retry+1}/{MAX_RETRIES} al traducir: {e}")
                    time.sleep(1)  # Esperar un segundo antes de reintentar
                    if retry == MAX_RETRIES - 1:  # Si es el último intento
                        logger.error(
                            "Todos los intentos de traducción fallaron")
                        # Retornar el texto original como fallback
                        return text

    def _translate_chunk(self, text_chunk: str) -> str:
        """
        Traduce un fragmento de texto con la API de DeepSeek.
        Método interno utilizado por translate_to_spanish.
        """
        prompt = f"""
Traduce el siguiente texto al español, manteniendo el formato y estructura original:

{text_chunk}

Proporciona solo la traducción, sin comentarios adicionales.
"""

        try:
            # Preparar la solicitud para la API de DeepSeek
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }

            data = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": "Eres un traductor profesional."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.3,  # Temperatura baja para traducciones más precisas
                "max_tokens": 4000   # Ajustar según sea necesario
            }

            # Realizar la solicitud a la API
            response = requests.post(self.api_url, headers=headers, json=data)
            response.raise_for_status()  # Lanzar excepción si hay error HTTP

            # Procesar la respuesta
            response_data = response.json()
            translated_text = response_data.get("choices", [{}])[
                0].get("message", {}).get("content", "")

            logger.info("Traducción completada.")
            return translated_text

        except requests.exceptions.RequestException as e:
            logger.error(
                f"Error en la solicitud a la API de DeepSeek para traducción: {e}")
            raise

        except Exception as e:
            logger.error(f"Error durante la traducción con DeepSeek API: {e}")
            raise
