# src/utils/gemini_processor.py
import logging
# Asegúrate de que google-generativeai esté instalado
import google.generativeai as genai
import json
from typing import Dict, Any, List
from src.utils.diarization_helper import DiarizationHelper
from src.utils.name_normalizer import NameNormalizer

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
        try:
            self.model = genai.GenerativeModel('gemini-1.5-flash')
        except Exception as e:
            logger.warning(f"Error al inicializar modelo gemini-1.5-flash: {e}")
            logger.info("Intentando con modelo alternativo gemini-pro...")
            self.model = genai.GenerativeModel('gemini-pro')

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

        # Aplicar preprocesamiento para mejorar la diarización
        preprocessed_text = DiarizationHelper.preprocess_for_diarization(transcribed_text)
        
        # Manejar textos largos dividiéndolos en fragmentos
        MAX_CHUNK_SIZE = 10000  # Tamaño máximo de cada fragmento en caracteres
        MAX_RETRIES = 3  # Número máximo de reintentos

        # Si el texto es muy largo, dividirlo en fragmentos
        if len(preprocessed_text) > MAX_CHUNK_SIZE:
            logger.info(
                f"Texto demasiado largo ({len(preprocessed_text)} caracteres). Dividiendo en fragmentos...")

            # Dividir el texto en fragmentos de aproximadamente MAX_CHUNK_SIZE caracteres
            # Intentamos dividir en puntos o comas para mantener la coherencia
            chunks = []
            current_chunk = ""

            for sentence in preprocessed_text.replace(".", ".|").replace("?", "?|").replace("!", "!|").split("|"):
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
                        
                        # Aplicar post-procesamiento para mejorar la diarización
                        chunk_result = DiarizationHelper.postprocess_diarization(chunk_result, chunk)

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
                    result = self._process_text_chunk(preprocessed_text)
                    # Aplicar post-procesamiento para mejorar la diarización
                    return DiarizationHelper.postprocess_diarization(result, transcribed_text)
                except Exception as e:
                    logger.warning(
                        f"Error en intento {retry+1}/{MAX_RETRIES}: {e}")
                    if retry == MAX_RETRIES - 1:  # Si es el último intento
                        logger.error("Todos los intentos fallaron")
                        # Retornar un resultado básico como fallback
                        return {"actors": ["Desconocido"], "dialogues": [{"speaker": "Desconocido", "text": transcribed_text}]}

    def _process_text_chunk(self, text_chunk: str) -> Dict[str, Any]:
        """
        Procesa un fragmento de texto con la API de Gemini.
        Método interno utilizado por process_text.
        """
        prompt = f"""
Eres un analizador de transcripciones experto, especializado en el ámbito jurídico y reuniones empresariales, con habilidad avanzada para la identificación de hablantes. Tu tarea es tomar el texto de una transcripción de audio y segmentarlo cuidadosamente en turnos de diálogo, identificando de manera precisa al hablante de cada turno.

Considera los siguientes puntos clave al procesar el texto:

1. **Identificación Avanzada de Hablantes**:
   - Presta atención a cambios sutiles en el estilo de habla, vocabulario y temas tratados
   - Identifica cuando una persona menciona a otra por su nombre (ej. "Jennifer, por favor...")
   - Reconoce patrones de habla únicos de cada persona (muletillas, frases características)
   - Detecta cuando alguien responde a una pregunta o continúa un tema previo

2. **Indicadores de Cambio de Hablante**:
   - Cambios abruptos de tema o perspectiva
   - Frases como "como decía...", "en mi opinión...", "yo creo que..."
   - Preguntas directas seguidas de respuestas
   - Referencias a "yo", "tú", "él/ella" que indiquen cambio de perspectiva

3. **Nombres y Roles Específicos**:
   - Identifica nombres propios mencionados en la conversación (Jennifer, Julián, Valeria, etc.)
   - Asigna roles basados en el contexto (Coordinador, Cliente, Abogado, etc.)
   - Mantén consistencia en la identificación a lo largo del texto
   - IMPORTANTE: Distingue claramente entre personas que HABLAN y personas que solo son MENCIONADAS
   - Si alguien dice "hablé con Janer" pero Janer no habla directamente, márcalo como "Janer (Mencionado)"

4. **Análisis de Contexto Conversacional**:
   - Reconoce patrones de pregunta-respuesta
   - Identifica cuando alguien está explicando un proceso vs. cuando alguien está solicitando información
   - Detecta acuerdos, desacuerdos y negociaciones entre participantes

5. **Estructura de Salida Mejorada**:
   - Divide el texto en segmentos más pequeños por hablante
   - Evita asignar bloques muy largos a un solo hablante si hay indicios de múltiples voces
   - Usa "Participante 1", "Participante 2", etc. si no puedes identificar nombres específicos
   - Solo usa "Desconocido" como último recurso cuando no hay forma de distinguir al hablante

Ejemplo de formato de salida (JSON):
```json
{{
  "actors": ["Jennifer (Coordinadora)", "Julián (Abogado)", "Valeria (Consultora)", "Participante 1", "Carlos (Mencionado)"],
  "dialogues": [
    {{"speaker": "Jennifer (Coordinadora)", "text": "Por favor, comparte pantalla. Necesitamos revisar el proceso."}},
    {{"speaker": "Valeria (Consultora)", "text": "Me gustaría programar una reunión para el lunes y revisar la documentación pendiente."}},
    {{"speaker": "Julián (Abogado)", "text": "Tengo aquí el caso que mencionabas. Efectivamente hay un problema con la notificación."}},
    {{"speaker": "Participante 1", "text": "¿Podríamos avanzar con el tema de persona natural primero?"}}
  ]
}}
```

Analiza el siguiente texto, prestando especial atención a los cambios de hablante, referencias a nombres propios, y patrones de conversación:

{text_chunk}

Proporciona la salida en formato JSON con la identificación más precisa posible de los hablantes.
"""

        try:
            response = self.model.generate_content(prompt)
            response_text = response.text.strip()

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
                    "La respuesta de Gemini no tiene la estructura JSON esperada.")
                processed_data = {"actors": ["Desconocido"], "dialogues": [
                    {"speaker": "Desconocido", "text": text_chunk}]}
            
            # Normalizar nombres y consolidar hablantes
            normalized_actors, normalized_dialogues = NameNormalizer.normalize_names(
                processed_data["actors"], processed_data["dialogues"]
            )
            
            # Filtrar actores que solo son mencionados
            active_actors = NameNormalizer.filter_mentioned_names(normalized_actors)
            
            # Actualizar los datos procesados
            processed_data["actors"] = active_actors
            processed_data["dialogues"] = normalized_dialogues

            return processed_data

        except json.JSONDecodeError as e:
            logger.error(f"Error al parsear la respuesta JSON de Gemini: {e}")
            logger.error(
                f"Respuesta recibida de Gemini (sin parsear):\n{response.text}")
            raise

        except Exception as e:
            logger.error(f"Error durante el procesamiento con Gemini API: {e}")
            raise

    def translate_to_spanish(self, text: str) -> str:
        """
        Traduce el texto al español usando la API de Gemini.

        Args:
            text: El texto a traducir.

        Returns:
            str: El texto traducido al español.
        """
        logger.info("Traduciendo texto al español con Gemini...")

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
                    if retry == MAX_RETRIES - 1:  # Si es el último intento
                        logger.error(
                            "Todos los intentos de traducción fallaron")
                        # Retornar el texto original como fallback
                        return text

    def _translate_chunk(self, text_chunk: str) -> str:
        """
        Traduce un fragmento de texto con la API de Gemini.
        Método interno utilizado por translate_to_spanish.
        """
        prompt = f"""
Traduce el siguiente texto al español, siguiendo estas instrucciones específicas:

1. Mantén EXACTAMENTE el mismo formato y estructura del texto original.
2. NUNCA omitas ninguna palabra o frase, incluso si parece confusa o incompleta.
3. NUNCA sustituyas palabras o frases con puntos suspensivos (...).
4. Si encuentras una palabra o frase que no entiendes completamente, tradúcela literalmente.
5. Preserva todos los nombres propios, términos técnicos y jerga especializada tal como aparecen.
6. Mantén todas las repeticiones, vacilaciones y muletillas del hablante original.
7. Conserva la puntuación exacta del texto original.

Texto a traducir:
{text_chunk}

Proporciona ÚNICAMENTE la traducción completa, sin omisiones ni comentarios adicionales.
"""

        # Configurar parámetros de generación para maximizar la fidelidad
        generation_config = {
            "temperature": 0.2,  # Baja temperatura para respuestas más deterministas
            "top_p": 0.95,       # Alto valor de top_p para mantener la coherencia
            "top_k": 40,         # Valor moderado de top_k
            "max_output_tokens": len(text_chunk) * 2  # Asegurar suficiente espacio para la traducción
        }

        try:
            response = self.model.generate_content(
                prompt, 
                generation_config=generation_config
            )
            translated_text = response.text.strip()
            
            # Verificar si hay puntos suspensivos sospechosos en la traducción
            if "..." in translated_text and "..." not in text_chunk:
                logger.warning("Se detectaron puntos suspensivos en la traducción que no estaban en el original")
                # Intentar nuevamente con instrucciones más enfáticas
                return self._translate_chunk_strict(text_chunk)
                
            return translated_text
            
        except Exception as e:
            logger.error(f"Error en traducción estándar: {e}")
            # Intentar con el método estricto como fallback
            return self._translate_chunk_strict(text_chunk)
            
    def _translate_chunk_strict(self, text_chunk: str) -> str:
        """
        Método alternativo de traducción con instrucciones más estrictas para casos difíciles.
        """
        prompt = f"""
INSTRUCCIONES DE TRADUCCIÓN CRÍTICAS:

Tu tarea es traducir el siguiente texto del inglés al español con ABSOLUTA FIDELIDAD.

REGLAS ESTRICTAS:
- PROHIBIDO usar puntos suspensivos (...) a menos que existan en el texto original
- PROHIBIDO omitir cualquier palabra o frase, sin importar lo confusa que parezca
- PROHIBIDO resumir o parafrasear - debes traducir PALABRA POR PALABRA
- Si hay términos técnicos o nombres propios, mantenlos EXACTAMENTE igual
- Si hay repeticiones o frases incompletas, REPRODÚCELAS fielmente en la traducción
- Si hay palabras que no entiendes, tradúcelas LITERALMENTE

TEXTO A TRADUCIR:
{text_chunk}

IMPORTANTE: Tu traducción será evaluada por su COMPLETITUD. Cualquier omisión resultará en un fallo crítico.
"""

        try:
            # Usar configuración más restrictiva
            generation_config = {
                "temperature": 0.1,  # Temperatura muy baja para máxima precisión
                "top_p": 0.99,       # Valor muy alto de top_p
                "top_k": 50,         # Valor alto de top_k
                "max_output_tokens": len(text_chunk) * 3  # Espacio extra para asegurar completitud
            }
            
            response = self.model.generate_content(
                prompt, 
                generation_config=generation_config
            )
            return response.text.strip()
            
        except Exception as e:
            logger.error(f"Error en traducción estricta: {e}")
            # Si todo falla, devolver el texto original
            return text_chunk