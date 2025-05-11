# src/utils/text_processor.py
import logging
import re
import spacy  # Asegúrate de que spacy esté instalado (pip install spacy)
# Descarga el modelo de español si lo necesitas: python -m spacy download es_core_news_sm
# O el modelo de inglés si lo necesitas: python -m spacy download en_core_web_sm
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

# Cargar modelo de spaCy (puedes configurar el idioma si es necesario)
# Considera cargar esto una vez al inicio de la aplicación o pasarlo
try:
    # Intenta cargar un modelo pequeño de español por defecto
    nlp = spacy.load("es_core_news_sm")
    logger.info("Modelo de spaCy 'es_core_news_sm' cargado.")
except OSError:
    logger.warning(
        "Modelo de spaCy 'es_core_news_sm' no encontrado. Intentando descargar...")
    try:
        # Si no se encuentra, intenta descargarlo
        spacy.cli.download("es_core_news_sm")
        nlp = spacy.load("es_core_news_sm")
        logger.info("Modelo de spaCy 'es_core_news_sm' descargado y cargado.")
    except Exception as e:
        logger.error(
            f"Error al descargar o cargar modelo de spaCy 'es_core_news_sm': {e}")
        logger.warning(
            "spaCy no estará disponible para procesamiento de texto avanzado.")
        nlp = None  # spaCy no está disponible


class TextProcessor:
    """
    Procesador de texto para limpiar, analizar (básico) y formatear transcripciones.
    En la versión anterior, este podría haber tenido más lógica de análisis
    antes de que Gemini tomara ese rol principal. Ahora se enfoca en formateo.
    """

    def __init__(self, text_processing_config: Dict[str, Any]):
        """
        Inicializa el procesador de texto con reglas de configuración.

        Args:
            text_processing_config: Diccionario con reglas para formateo,
                                    identificación básica (si aplica), etc.
        """
        self.config = text_processing_config
        # En la versión anterior, podrías haber usado self.config para reglas de análisis aquí.
        logger.info("TextProcessor (Formateador) inicializado.")

    def _clean_text_pre_api(self, text: str) -> str:
        """
        Realiza una limpieza básica del texto antes de enviarlo a una API externa (como Gemini).
        Elimina marcadores de tiempo, ruidos comunes, etc.

        Args:
            text: El texto bruto de la transcripción.

        Returns:
            str: El texto limpio.
        """
        # Eliminar marcadores de tiempo como [00:01:23]
        cleaned_text = re.sub(r'\[\d{2}:\d{2}:\d{2}\]', '', text)
        # Eliminar ruidos comunes entre corchetes [ruido]
        cleaned_text = re.sub(r'\[.*?\]', '', cleaned_text)
        # Eliminar espacios en blanco extra
        cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()
        # Puedes añadir más reglas de limpieza aquí según sea necesario
        return cleaned_text

    # En la versión anterior, podrías haber tenido métodos aquí para:
    # - Identificar actores basándose en patrones (usando spaCy o regex)
    # - Segmentar texto en diálogos basándose en indicadores
    # - Analizar metadatos

    def format_processed_result(self, processed_data: Dict[str, Any], filename: str = "transcripcion") -> str:
        """
        Formatea el resultado procesado (obtenido de Gemini) en un string de texto estructurado.

        Args:
            processed_data: Diccionario con 'actors' y 'dialogues' obtenido del procesador IA.
            filename: Nombre original del archivo para incluir en el encabezado.

        Returns:
            str: El texto formateado listo para guardar en un archivo.
        """
        actors = processed_data.get("actors", ["Desconocido"])
        dialogues = processed_data.get("dialogues", [])
        format_config = self.config.get("format_config", {})

        line_spacing = format_config.get("line_spacing", 2)
        indent_size = format_config.get("indent_size", 4)
        max_line_length = format_config.get("max_line_length", 80)
        capitalize_names = format_config.get(
            "capitalize_names", True)  # Opción para capitalizar nombres

        formatted_output = []

        # Encabezado
        formatted_output.append("TRANSCRIPCIÓN ESTRUCTURADA")
        formatted_output.append("=" * len("TRANSCRIPCIÓN ESTRUCTURADA"))
        formatted_output.append("")
        formatted_output.append("INFORMACIÓN DEL ARCHIVO")
        formatted_output.append("-" * len("INFORMACIÓN DEL ARCHIVO"))
        formatted_output.append(f"Archivo original: {filename}")
        import datetime
        formatted_output.append(
            f"Fecha de procesamiento: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        formatted_output.append("")

        # Lista de Actores
        formatted_output.append("ACTORES IDENTIFICADOS")
        formatted_output.append("-" * len("ACTORES IDENTIFICADOS"))
        if actors:
            for actor in actors:
                formatted_output.append(f"- {actor}")
        else:
            formatted_output.append("No se identificaron actores.")
        formatted_output.append("")

        # Diálogos
        formatted_output.append("DIÁLOGOS")
        formatted_output.append("-" * len("DIÁLOGOS"))
        formatted_output.append("")

        for entry in dialogues:
            speaker = entry.get("speaker", "Desconocido")
            text = entry.get("text", "").strip()

            if not text:  # Ignorar entradas de diálogo vacías
                continue

            # Formatear el nombre del hablante (opcionalmente capitalizar)
            formatted_speaker = speaker
            if capitalize_names and speaker != "Desconocido":
                # Capitalizar cada palabra del nombre del hablante
                formatted_speaker = " ".join(
                    word.capitalize() for word in speaker.split())

            # Formatear el texto del diálogo con sangría y ajuste de línea
            indent = " " * indent_size
            speaker_line = f"{formatted_speaker}:"  # Línea del hablante
            formatted_output.append(speaker_line)

            # Ajustar el texto para que no exceda max_line_length (considerando la sangría)
            # nltk.word_wrap podría ser útil aquí si lo tuvieras instalado
            # Una implementación simple:
            current_line = indent
            words = text.split()
            for word in words:
                # Si añadir la palabra actual excede el límite (menos la sangría)
                if len(current_line) + len(word) + 1 > max_line_length:
                    # Añadir la línea actual (sin espacios al final)
                    formatted_output.append(current_line.rstrip())
                    current_line = indent + word + " "  # Empezar nueva línea con sangría y la palabra
                else:
                    current_line += word + " "  # Añadir la palabra a la línea actual

            # Añadir la última línea si no está vacía
            if current_line.strip() != indent.strip():
                # Añadir la última línea
                formatted_output.append(current_line.rstrip())

            # Añadir espaciado entre diálogos
            for _ in range(line_spacing):
                formatted_output.append("")

        return "\n".join(formatted_output)

# NOTA: La lógica de análisis más avanzada (identificación de entidades, etc.)
# que podría haber estado aquí en una versión muy temprana, fue movida a GeminiProcessor
# cuando se integró la API. Este archivo ahora se enfoca principalmente en el formateo.
